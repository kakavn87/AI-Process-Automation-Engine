from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.dependencies.auth import TenantContext, get_tenant_context, require_roles
from app.models.tenant import Tenant, TenantInvitation, TenantMembership, User
from app.models.workflow_session import WorkflowSession
from app.schemas.auth import InvitationAcceptRequest, InvitationCreateRequest, LoginRequest
from app.services.ai_usage_service import AIUsageService
from app.services.auth_service import AuthService, password_hash
from app.services.execution_service import ExecutionService
from app.services.workflow_session_service import WorkflowSessionService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        yield db
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def add_tenant(db: Session, name: str) -> Tenant:
    tenant = Tenant(
        id=str(uuid4()),
        name=name,
        slug=f"{name.lower().replace(' ', '-')}-{uuid4().hex[:8]}",
        is_active=True,
    )
    db.add(tenant)
    db.flush()
    return tenant


def add_user(db: Session, tenant: Tenant, email: str, role: str = "owner") -> User:
    user = User(
        id=str(uuid4()),
        email=email,
        full_name="Workspace User",
        password_hash=password_hash.hash("Correct-Horse-Battery-12!"),
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(TenantMembership(
        id=str(uuid4()),
        tenant_id=tenant.id,
        user_id=user.id,
        role=role,
        is_active=True,
    ))
    db.flush()
    return user


def simple_workflow() -> dict:
    return {
        "name": "Tenant-scoped workflow",
        "trigger": "Manual",
        "steps": [
            {
                "id": "step-1",
                "type": "trigger",
                "name": "Start",
                "description": "Start manually.",
                "config": {},
            },
            {
                "id": "step-2",
                "type": "generate",
                "name": "Prepare output",
                "description": "Prepare a draft.",
                "config": {},
            },
        ],
    }


def test_login_issues_jwt_bound_to_one_tenant(db_session, monkeypatch):
    tenant = add_tenant(db_session, "Finance workspace")
    user = add_user(db_session, tenant, "owner@example.com")
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "test-secret-that-is-at-least-32-characters-long")

    response = AuthService(db_session).login(LoginRequest(
        email="OWNER@example.com",
        password="Correct-Horse-Battery-12!",
    ))
    payload = jwt.decode(
        response["access_token"],
        settings.JWT_SECRET_KEY,
        algorithms=["HS256"],
    )

    assert response["token_type"] == "bearer"
    assert response["user"]["email"] == user.email
    assert response["user"]["tenant"]["id"] == tenant.id
    assert payload["sub"] == user.id
    assert payload["tid"] == tenant.id

    context = get_tenant_context(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=response["access_token"]),
        db_session,
    )
    assert context.authenticated is True
    assert context.tenant_id == tenant.id
    assert context.role == "owner"


def test_login_does_not_allow_wrong_password(db_session):
    tenant = add_tenant(db_session, "Operations workspace")
    add_user(db_session, tenant, "member@example.com", role="member")

    with pytest.raises(ValueError, match="incorrect"):
        AuthService(db_session).login(LoginRequest(
            email="member@example.com",
            password="wrong-password",
        ))


def test_one_time_invitation_creates_member_and_cannot_be_reused(db_session):
    tenant = add_tenant(db_session, "Customer workspace")
    owner = add_user(db_session, tenant, "owner@example.com")
    service = AuthService(db_session)
    invitation = service.create_invitation(
        InvitationCreateRequest(email="new.member@example.com", role="member"),
        tenant_id=tenant.id,
        created_by_user_id=owner.id,
    )

    accepted = service.accept_invitation(InvitationAcceptRequest(
        token=invitation["invitation_token"],
        password="A-New-Secure-Password-12!",
        full_name="New Member",
    ))
    assert accepted["accepted"] is True
    member = db_session.query(User).filter(User.email == "new.member@example.com").one()
    membership = (
        db_session.query(TenantMembership)
        .filter(TenantMembership.user_id == member.id, TenantMembership.tenant_id == tenant.id)
        .one()
    )
    assert membership.role == "member"
    assert password_hash.verify("A-New-Secure-Password-12!", member.password_hash)

    with pytest.raises(ValueError, match="invalid, expired or has already been used"):
        service.accept_invitation(InvitationAcceptRequest(
            token=invitation["invitation_token"],
            password="A-New-Secure-Password-12!",
            full_name="New Member",
        ))


def test_expired_invitation_is_rejected_with_sqlite_naive_datetime(db_session):
    tenant = add_tenant(db_session, "Invitation workspace")
    owner = add_user(db_session, tenant, "owner@example.com")
    service = AuthService(db_session)
    invitation = service.create_invitation(
        InvitationCreateRequest(email="expired@example.com", role="member"),
        tenant_id=tenant.id,
        created_by_user_id=owner.id,
    )
    record = db_session.query(TenantInvitation).one()
    record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()
    db_session.expire_all()

    with pytest.raises(ValueError, match="invalid, expired or has already been used"):
        service.accept_invitation(InvitationAcceptRequest(
            token=invitation["invitation_token"],
            password="A-New-Secure-Password-12!",
            full_name="Expired User",
        ))


def test_user_from_another_tenant_cannot_read_or_approve_execution(db_session):
    tenant_a = add_tenant(db_session, "Tenant A")
    tenant_b = add_tenant(db_session, "Tenant B")
    add_user(db_session, tenant_a, "a@example.com")
    add_user(db_session, tenant_b, "b@example.com")

    service_a = ExecutionService(db_session, tenant_id=tenant_a.id)
    service_b = ExecutionService(db_session, tenant_id=tenant_b.id)
    created = service_a.create(simple_workflow())

    assert service_a.get(created["id"]) is not None
    assert service_b.get(created["id"]) is None
    assert service_b.list() == []
    with pytest.raises(KeyError, match="not found"):
        service_b.approve(created["id"])
    with pytest.raises(KeyError, match="not found"):
        service_b.reject(created["id"])


def test_user_from_another_tenant_cannot_read_or_answer_workflow_session(db_session):
    tenant_a = add_tenant(db_session, "Tenant A")
    tenant_b = add_tenant(db_session, "Tenant B")
    service_a = WorkflowSessionService(db_session, tenant_id=tenant_a.id)
    service_b = WorkflowSessionService(db_session, tenant_id=tenant_b.id)
    created = service_a.create(
        description="Prepare a customer support report.",
        analysis={"questions": ["Which mailbox should receive the report?"]},
        strategy="rules",
        language="en",
        business_domain="customer_support",
    )
    question_id = created["openQuestions"][0]["id"]

    assert service_a.get(created["id"]) is not None
    assert service_b.get(created["id"]) is None
    with pytest.raises(KeyError, match="not found"):
        service_b.submit_answers(created["id"], {question_id: "private@example.com"})


def test_ai_usage_summary_is_tenant_scoped(db_session):
    tenant_a = add_tenant(db_session, "Tenant A")
    tenant_b = add_tenant(db_session, "Tenant B")
    telemetry = {
        "provider": "openai",
        "model": "test-model",
        "task": "process_analysis",
        "status": "success",
        "inputTokens": 10,
        "outputTokens": 5,
        "totalTokens": 15,
        "durationMs": 100,
    }
    AIUsageService(db_session, tenant_id=tenant_a.id).record(None, telemetry)
    AIUsageService(db_session, tenant_id=tenant_b.id).record(None, telemetry)

    assert AIUsageService(db_session, tenant_id=tenant_a.id).summary()["totalCalls"] == 1
    assert AIUsageService(db_session, tenant_id=tenant_b.id).summary()["totalCalls"] == 1


def test_workspace_role_protects_approval_and_live_actions_but_demo_remains_open(monkeypatch):
    context = TenantContext(
        tenant_id=str(uuid4()),
        role="member",
        authenticated=True,
    )
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    with pytest.raises(HTTPException) as error:
        require_roles("owner", "admin", "approver")(context)
    assert error.value.status_code == 403

    monkeypatch.setattr(settings, "AUTH_ENABLED", False)
    demo_context = TenantContext(
        tenant_id=str(uuid4()),
        role="demo",
        authenticated=False,
    )
    assert require_roles("owner", "admin")(demo_context) == demo_context


def test_user_with_multiple_workspaces_must_choose_one(db_session, monkeypatch):
    tenant_a = add_tenant(db_session, "First workspace")
    user = add_user(db_session, tenant_a, "multi@example.com")
    tenant_b = add_tenant(db_session, "Second workspace")
    db_session.add(TenantMembership(
        id=str(uuid4()),
        tenant_id=tenant_b.id,
        user_id=user.id,
        role="approver",
        is_active=True,
    ))
    db_session.commit()
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "test-secret-that-is-at-least-32-characters-long")

    service = AuthService(db_session)
    selection = service.login(LoginRequest(
        email="multi@example.com",
        password="Correct-Horse-Battery-12!",
    ))
    assert selection["requires_workspace_selection"] is True
    assert {item["id"] for item in selection["workspaces"]} == {tenant_a.id, tenant_b.id}
    assert "access_token" not in selection

    selected = service.login(LoginRequest(
        email="multi@example.com",
        password="Correct-Horse-Battery-12!",
        tenant_id=tenant_b.id,
    ))
    payload = jwt.decode(selected["access_token"], settings.JWT_SECRET_KEY, algorithms=["HS256"])
    assert payload["tid"] == tenant_b.id
    assert selected["user"]["role"] == "approver"


def test_jwt_cannot_switch_to_a_workspace_without_membership(db_session, monkeypatch):
    tenant_a = add_tenant(db_session, "Private A")
    tenant_b = add_tenant(db_session, "Private B")
    user = add_user(db_session, tenant_a, "private-a@example.com")
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    secret = "test-secret-that-is-at-least-32-characters-long"
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", secret)
    now = datetime.now(timezone.utc)
    forged_scope_token = jwt.encode(
        {
            "sub": user.id,
            "tid": tenant_b.id,
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as error:
        get_tenant_context(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=forged_scope_token),
            db_session,
        )
    assert error.value.status_code == 401


def test_live_webhook_is_disabled_when_shared_auth_mode_is_enabled(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "WEBHOOK_EXECUTION_ENABLED", True)
    monkeypatch.setattr(settings, "WORKFLOW_WEBHOOK_URL", "https://hooks.example.com/process")
    monkeypatch.setattr(settings, "WORKFLOW_LIVE_EXECUTION_TOKEN", "operator-token")

    readiness = ExecutionService.live_execution_readiness()

    assert readiness["ready"] is False
    assert readiness["enabled"] is False
    assert readiness["status"] == "workspace_configuration_required"


def test_live_webhook_session_sync_is_scoped_to_the_active_tenant(db_session):
    tenant_a = add_tenant(db_session, "Tenant Live A")
    tenant_b = add_tenant(db_session, "Tenant Live B")
    execution_id = str(uuid4())

    session_a = WorkflowSessionService(db_session, tenant_id=tenant_a.id).create(
        description="Tenant A workflow",
        analysis={"questions": []},
        strategy="rules",
        language="en",
    )
    session_b = WorkflowSession(
        id=str(uuid4()),
        tenant_id=tenant_b.id,
        description="Tenant B workflow",
        analysis_strategy="rules",
        language="en",
        business_domain="general",
        analysis={},
        questions=[],
        answers={},
        status="completed",
        events=[],
        related_execution_id=execution_id,
    )
    db_session.add(session_b)
    db_session.flush()

    # Attach the same reference deliberately to simulate an inconsistent or
    # legacy relation. Tenant A must never append events to Tenant B's row.
    session_a_row = db_session.get(WorkflowSession, session_a["id"])
    session_a_row.related_execution_id = execution_id
    db_session.commit()

    ExecutionService(db_session, tenant_id=tenant_a.id)._sync_live_workflow_session(
        execution_id,
        "succeeded",
        "Webhook receipt confirmed.",
    )
    db_session.commit()
    db_session.refresh(session_a_row)
    db_session.refresh(session_b)

    assert any(event["event"] == "live_execution_succeeded" for event in session_a_row.events)
    assert session_b.events == []
