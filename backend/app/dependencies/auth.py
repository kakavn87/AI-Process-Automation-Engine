from dataclasses import dataclass
from typing import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.tenancy import DEFAULT_TENANT_ID
from app.models.tenant import Tenant, TenantMembership, User

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    role: str
    authenticated: bool
    user_id: str | None = None
    email: str | None = None
    full_name: str | None = None
    tenant_name: str | None = None


def get_tenant_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> TenantContext:
    # Backward-compatible demo mode: all anonymous demo data belongs to one
    # isolated demo tenant. Production multi-user mode must set AUTH_ENABLED.
    if not settings.AUTH_ENABLED:
        return TenantContext(
            tenant_id=DEFAULT_TENANT_ID,
            role="demo",
            authenticated=False,
            tenant_name="FlowPilot Demo",
        )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "sub", "tid"]},
        )
        user_id = str(payload["sub"])
        tenant_id = str(payload["tid"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The access token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)
    tenant = db.get(Tenant, tenant_id)
    membership = (
        db.query(TenantMembership)
        .filter(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.is_active.is_(True),
        )
        .one_or_none()
    )
    if (
        user is None or not user.is_active
        or tenant is None or not tenant.is_active
        or membership is None
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account no longer has access to the selected workspace.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TenantContext(
        tenant_id=tenant_id,
        role=membership.role,
        authenticated=True,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_name=tenant.name,
    )


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(context: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if not context.authenticated or context.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your workspace role does not allow this action.",
            )
        return context

    return dependency
