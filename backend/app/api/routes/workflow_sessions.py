from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.workflow_session import SubmitWorkflowAnswersRequest
from app.services.workflow_session_service import WorkflowSessionService

router = APIRouter(prefix="/processes/sessions", tags=["workflow-sessions"])


@router.get("/{session_id}")
def get_workflow_session(session_id: str, db: Session = Depends(get_db)):
    result = WorkflowSessionService(db).get(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Workflow session was not found.")
    return result


@router.post("/{session_id}/answers")
def submit_workflow_answers(
    session_id: str,
    request: SubmitWorkflowAnswersRequest,
    db: Session = Depends(get_db),
):
    try:
        return WorkflowSessionService(db).submit_answers(session_id, request.answers)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/{session_id}/execute", status_code=201)
def create_session_execution(session_id: str, db: Session = Depends(get_db)):
    try:
        return WorkflowSessionService(db).create_execution(session_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
