from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import TenantContext, get_tenant_context, require_roles
from app.schemas.execution import (
    CreateExecutionRequest,
    ExecutionDecisionRequest,
    LiveExecutionRequest,
)
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("/live-readiness")
def get_live_execution_readiness():
    return ExecutionService.live_execution_readiness()


@router.get("/")
def list_executions(
    db: Session = Depends(get_db),
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    return {"items": ExecutionService(db, tenant_id=tenant_context.tenant_id).list()}


@router.post("/", status_code=201)
def create_execution(
    request: CreateExecutionRequest,
    db: Session = Depends(get_db),
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    try:
        return ExecutionService(db, tenant_id=tenant_context.tenant_id).create(request.workflow)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{execution_id}")
def get_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    result = ExecutionService(db, tenant_id=tenant_context.tenant_id).get(execution_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Execution was not found.")
    return result


@router.post("/{execution_id}/approve")
def approve_execution(
    execution_id: str,
    request: ExecutionDecisionRequest,
    db: Session = Depends(get_db),
    tenant_context: TenantContext = Depends(require_roles("owner", "admin", "approver")),
):
    try:
        return ExecutionService(db, tenant_id=tenant_context.tenant_id).approve(execution_id, request.note)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{execution_id}/reject")
def reject_execution(
    execution_id: str,
    request: ExecutionDecisionRequest,
    db: Session = Depends(get_db),
    tenant_context: TenantContext = Depends(require_roles("owner", "admin", "approver")),
):
    try:
        return ExecutionService(db, tenant_id=tenant_context.tenant_id).reject(execution_id, request.note)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{execution_id}/live")
def run_live_execution(
    execution_id: str,
    request: LiveExecutionRequest,
    db: Session = Depends(get_db),
    tenant_context: TenantContext = Depends(require_roles("owner", "admin")),
):
    try:
        return ExecutionService(db, tenant_id=tenant_context.tenant_id).run_live(
            execution_id,
            request.confirm_live_execution,
            request.confirmation_token,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
