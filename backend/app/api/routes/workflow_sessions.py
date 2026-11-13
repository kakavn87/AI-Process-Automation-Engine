from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.workflow_session import SubmitWorkflowAnswersRequest
from app.services.workflow_session_service import WorkflowSessionService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.models.workflow_session import WorkflowSession

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


class SessionKnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1_000)
    top_k: int = Field(default=8, ge=1, le=20)


@router.post("/{session_id}/knowledge/search")
def search_session_knowledge(
    session_id: str,
    request: SessionKnowledgeSearchRequest,
    db: Session = Depends(get_db),
):
    if db.get(WorkflowSession, session_id) is None:
        raise HTTPException(status_code=404, detail="Workflow session was not found.")

    knowledge = KnowledgeBaseService()
    readiness = knowledge.readiness()
    if readiness["status"] != "ready":
        raise HTTPException(
            status_code=503,
            detail="Session knowledge search is not available. Check the RAG integration readiness.",
        )

    try:
        matches = knowledge.search(session_id, request.query, request.top_k)
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="The session knowledge store could not complete the search.",
        ) from error

    return {
        "sessionId": session_id,
        "query": request.query,
        "matches": matches,
    }
