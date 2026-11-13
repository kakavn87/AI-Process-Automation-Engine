from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets
from uuid import uuid4

import jwt
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tenancy import DEFAULT_TENANT_ID
from app.models.tenant import Tenant, TenantInvitation, TenantMembership, User
from app.schemas.auth import InvitationAcceptRequest, InvitationCreateRequest, LoginRequest

password_hash = PasswordHash.recommended()
ALLOWED_INVITE_ROLES = {"admin", "member", "approver"}


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def bootstrap(self) -> None:
        if not settings.AUTH_ENABLED:
            return
        if len(settings.JWT_SECRET_KEY.strip()) < 32:
            raise RuntimeError("AUTH_ENABLED requires a JWT_SECRET_KEY with at least 32 characters.")

        tenant = self.db.get(Tenant, DEFAULT_TENANT_ID)
        if tenant is None:
            tenant = Tenant(
                id=DEFAULT_TENANT_ID,
                name=settings.BOOTSTRAP_TENANT_NAME.strip() or "FlowPilot Workspace",
                slug="flowpilot-demo",
                is_active=True,
            )
            self.db.add(tenant)
            self.db.flush()

        email = settings.BOOTSTRAP_ADMIN_EMAIL.strip().lower()
        raw_password = settings.BOOTSTRAP_ADMIN_PASSWORD
        if bool(email) != bool(raw_password):
            raise RuntimeError("Set both BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD, or neither.")

        if email and raw_password:
            if len(raw_password) < 12:
                raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD must contain at least 12 characters.")
            user = self.db.query(User).filter(User.email == email).one_or_none()
            if user is None:
                user = User(
                    id=str(uuid4()),
                    email=email,
                    full_name="Workspace Owner",
                    password_hash=password_hash.hash(raw_password),
                    is_active=True,
                )
                self.db.add(user)
                self.db.flush()

            membership = (
                self.db.query(TenantMembership)
                .filter(
                    TenantMembership.user_id == user.id,
                    TenantMembership.tenant_id == tenant.id,
                )
                .one_or_none()
            )
            if membership is None:
                self.db.add(TenantMembership(
                    id=str(uuid4()),
                    user_id=user.id,
                    tenant_id=tenant.id,
                    role="owner",
                    is_active=True,
                ))
            elif membership.role != "owner":
                membership.role = "owner"

        active_memberships = (
            self.db.query(TenantMembership)
            .filter(TenantMembership.tenant_id == tenant.id, TenantMembership.is_active.is_(True))
            .count()
        )
        if active_memberships == 0:
            raise RuntimeError(
                "Authentication is enabled but no workspace owner exists. "
                "Configure BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD for the first startup."
            )
        self.db.commit()

    def login(self, request: LoginRequest) -> dict:
        user = self.db.query(User).filter(User.email == request.email).one_or_none()
        if user is None or not user.is_active or not password_hash.verify(request.password, user.password_hash):
            raise ValueError("Email address or password is incorrect.")

        query = (
            self.db.query(TenantMembership, Tenant)
            .join(Tenant, Tenant.id == TenantMembership.tenant_id)
            .filter(
                TenantMembership.user_id == user.id,
                TenantMembership.is_active.is_(True),
                Tenant.is_active.is_(True),
            )
        )
        if request.tenant_id:
            query = query.filter(TenantMembership.tenant_id == request.tenant_id)
        memberships = query.order_by(Tenant.name.asc()).all()

        if not memberships:
            if request.tenant_id:
                raise ValueError("The selected workspace is not available to this account.")
            raise ValueError("This account has no active workspace membership.")
        if len(memberships) > 1 and not request.tenant_id:
            return {
                "requires_workspace_selection": True,
                "workspaces": [
                    {"id": tenant.id, "name": tenant.name, "role": membership.role}
                    for membership, tenant in memberships
                ],
            }

        membership, tenant = memberships[0]
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.AUTH_ACCESS_TOKEN_MINUTES)
        token = jwt.encode(
            {
                "sub": user.id,
                "tid": tenant.id,
                "iat": now,
                "exp": expires_at,
                "jti": str(uuid4()),
            },
            settings.JWT_SECRET_KEY,
            algorithm="HS256",
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": int((expires_at - now).total_seconds()),
            "user": self._user_payload(user, tenant, membership.role),
        }

    def create_invitation(
        self,
        request: InvitationCreateRequest,
        tenant_id: str,
        created_by_user_id: str,
    ) -> dict:
        if request.role not in ALLOWED_INVITE_ROLES:
            raise ValueError("The requested workspace role cannot be assigned.")
        existing_user = self.db.query(User).filter(User.email == request.email).one_or_none()
        if existing_user:
            existing_membership = (
                self.db.query(TenantMembership)
                .filter(
                    TenantMembership.user_id == existing_user.id,
                    TenantMembership.tenant_id == tenant_id,
                    TenantMembership.is_active.is_(True),
                )
                .one_or_none()
            )
            if existing_membership:
                raise ValueError("This user is already a member of the workspace.")

        now = datetime.now(timezone.utc)
        pending_invitations = (
            self.db.query(TenantInvitation)
            .filter(
                TenantInvitation.tenant_id == tenant_id,
                TenantInvitation.email == request.email,
                TenantInvitation.accepted_at.is_(None),
            )
            .all()
        )
        for pending in pending_invitations:
            pending_expiry = pending.expires_at
            if pending_expiry.tzinfo is None:
                pending_expiry = pending_expiry.replace(tzinfo=timezone.utc)
            if pending_expiry > now:
                raise ValueError("A pending invitation already exists for this email address.")

        raw_token = secrets.token_urlsafe(36)
        expires_at = datetime.now(timezone.utc) + timedelta(days=3)
        invitation = TenantInvitation(
            id=str(uuid4()),
            tenant_id=tenant_id,
            email=request.email,
            role=request.role,
            token_hash=sha256(raw_token.encode("utf-8")).hexdigest(),
            expires_at=expires_at,
            created_by_user_id=created_by_user_id,
        )
        self.db.add(invitation)
        self.db.commit()
        return {
            "email": invitation.email,
            "role": invitation.role,
            "invitation_token": raw_token,
            "expires_at": expires_at.isoformat(),
        }

    def accept_invitation(self, request: InvitationAcceptRequest) -> dict:
        token_hash = sha256(request.token.encode("utf-8")).hexdigest()
        invitation = (
            self.db.query(TenantInvitation)
            .filter(TenantInvitation.token_hash == token_hash)
            .with_for_update()
            .one_or_none()
        )
        now = datetime.now(timezone.utc)
        expires_at = invitation.expires_at if invitation is not None else None
        # SQLite may return a naive datetime even when the mapped column is timezone-aware.
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if invitation is None or invitation.accepted_at is not None or expires_at <= now:
            raise ValueError("This invitation is invalid, expired or has already been used.")

        tenant = self.db.get(Tenant, invitation.tenant_id)
        if tenant is None or not tenant.is_active:
            raise ValueError("The invited workspace is no longer active.")

        user = self.db.query(User).filter(User.email == invitation.email).one_or_none()
        if user is None:
            user = User(
                id=str(uuid4()),
                email=invitation.email,
                full_name=request.full_name.strip(),
                password_hash=password_hash.hash(request.password),
                is_active=True,
            )
            self.db.add(user)
            self.db.flush()
        else:
            if not user.is_active or not password_hash.verify(request.password, user.password_hash):
                raise ValueError("This email already has an account. Sign in with its existing password to accept the invitation.")

        membership = (
            self.db.query(TenantMembership)
            .filter(
                TenantMembership.user_id == user.id,
                TenantMembership.tenant_id == tenant.id,
            )
            .one_or_none()
        )
        if membership is None:
            self.db.add(TenantMembership(
                id=str(uuid4()),
                user_id=user.id,
                tenant_id=tenant.id,
                role=invitation.role,
                is_active=True,
            ))
        elif membership.is_active:
            raise ValueError("This user is already a member of the workspace.")
        else:
            membership.is_active = True
            membership.role = invitation.role

        invitation.accepted_at = now
        self.db.commit()
        return {"accepted": True, "tenant": {"id": tenant.id, "name": tenant.name}}

    @staticmethod
    def _user_payload(user: User, tenant: Tenant, role: str) -> dict:
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "tenant": {"id": tenant.id, "name": tenant.name},
            "role": role,
        }
