import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.execution import ApprovalExecution
from app.services.execution_service import ExecutionService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    ApprovalExecution.__table__.create(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def valid_workflow():
    return {
        "name": "Weekly report",
        "trigger": "Every Monday",
        "steps": [
            {"id": "s1", "type": "trigger", "name": "Start", "description": "Start weekly run.", "config": {}},
            {"id": "s2", "type": "generate", "name": "Create report", "description": "Prepare report.", "config": {}},
            {"id": "s3", "type": "approval", "name": "Manager approval", "description": "Wait for approval.", "config": {}},
            {"id": "s4", "type": "notify", "name": "Notify Teams", "description": "Send report.", "config": {"requiresApproval": True}},
        ],
    }


def test_execution_waits_for_approval_and_runs_after_approval(db_session):
    service = ExecutionService(db_session)
    created = service.create(valid_workflow())

    assert created["status"] == "awaiting_approval"
    assert created["events"][0]["event"] == "execution_created"

    approved = service.approve(created["id"], "Reviewed the draft.")
    assert approved["status"] == "completed"
    assert approved["decisionNote"] == "Reviewed the draft."
    assert any(event["event"] == "approval_granted" for event in approved["events"])
    assert any(event["status"] == "simulated" for event in approved["events"])
    assert service.get(created["id"])["status"] == "completed"

    with pytest.raises(ValueError, match="Cannot reject"):
        service.reject(created["id"], "Too late")


def test_execution_can_be_rejected_without_running_steps(db_session):
    service = ExecutionService(db_session)
    created = service.create(valid_workflow())

    rejected = service.reject(created["id"], "The validation rules are incomplete.")
    assert rejected["status"] == "rejected"
    assert rejected["decisionNote"] == "The validation rules are incomplete."
    assert len(rejected["events"]) == 2
    assert "No workflow steps were executed" in rejected["events"][-1]["message"]


def test_execution_rejects_outbound_workflow_without_approval_gate(db_session):
    invalid_workflow = {
        "name": "Unsafe workflow",
        "steps": [
            {"id": "s1", "type": "trigger", "config": {}},
            {"id": "s2", "type": "notify", "config": {"requiresApproval": True}},
        ],
    }
    with pytest.raises(ValueError, match="approval step must come before"):
        ExecutionService(db_session).create(invalid_workflow)
