from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import TenantContext, get_tenant_context, require_roles
from app.schemas.auth import InvitationAcceptRequest, InvitationCreateRequest, LoginRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/config")
def get_auth_config():
    """Public bootstrap information; never returns secrets or account details."""
    return {"authenticationRequired": settings.AUTH_ENABLED}


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    if not settings.AUTH_ENABLED:
        raise HTTPException(status_code=409, detail="Workspace authentication is disabled.")
    try:
        return AuthService(db).login(request)
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@router.get("/me")
def get_current_account(context: TenantContext = Depends(get_tenant_context)):
    if not context.authenticated:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user": {
            "id": context.user_id,
            "email": context.email,
            "full_name": context.full_name,
        },
        "tenant": {"id": context.tenant_id, "name": context.tenant_name},
        "role": context.role,
    }


@router.post("/invitations")
def create_invitation(
    request: InvitationCreateRequest,
    context: TenantContext = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    try:
        return AuthService(db).create_invitation(
            request,
            tenant_id=context.tenant_id,
            created_by_user_id=context.user_id or "",
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/invitations/accept")
def accept_invitation(request: InvitationAcceptRequest, db: Session = Depends(get_db)):
    if not settings.AUTH_ENABLED:
        raise HTTPException(status_code=409, detail="Workspace authentication is disabled.")
    try:
        return AuthService(db).accept_invitation(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
