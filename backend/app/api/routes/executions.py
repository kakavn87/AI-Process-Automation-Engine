from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.execution import ApprovalDecisionRequest, CreateExecutionRequest
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("/")
def list_executions(db: Session = Depends(get_db)):
    return {"items": ExecutionService(db).list()}


@router.post("/", status_code=201)
def create_execution(request: CreateExecutionRequest, db: Session = Depends(get_db)):
    try:
        return ExecutionService(db).create(request.workflow)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{execution_id}")
def get_execution(execution_id: int, db: Session = Depends(get_db)):
    result = ExecutionService(db).get(execution_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Execution not found.")
    return result


@router.post("/{execution_id}/approve")
def approve_execution(
    execution_id: int,
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
):
    try:
        return ExecutionService(db).approve(execution_id, request.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{execution_id}/reject")
def reject_execution(
    execution_id: int,
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
):
    if not request.note.strip():
        raise HTTPException(status_code=422, detail="A rejection reason is required.")
    try:
        return ExecutionService(db).reject(execution_id, request.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
