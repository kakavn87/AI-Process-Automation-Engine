from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.workflow_session import SubmitWorkflowAnswersRequest
from app.services.workflow_session_service import WorkflowSessionService
from app.services.ai_usage_service import AIUsageService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.models.workflow_session import WorkflowSession

router = APIRouter(prefix="/processes/sessions", tags=["workflow-sessions"])


@router.get("/{session_id}")
def get_workflow_session(session_id: str, db: Session = Depends(get_db)):
    result = WorkflowSessionService(db).get(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Workflow session was not found.")
    return result


@router.delete("/{session_id}", status_code=204)
def delete_workflow_session(session_id: str, db: Session = Depends(get_db)):
    session = db.get(WorkflowSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Workflow session was not found.")

    indexed_chunks = int(((session.analysis or {}).get("knowledgeBase") or {}).get("indexedChunks", 0))
    vectors_deleted = indexed_chunks == 0
    if indexed_chunks > 0:
        try:
            vectors_deleted = KnowledgeBaseService().delete_session(session_id)
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail="The session knowledge store could not delete its data. The workflow session was not deleted.",
            ) from error

    if indexed_chunks > 0 and not vectors_deleted:
        raise HTTPException(
            status_code=503,
            detail="Vector storage is not configured. Restore Qdrant access before deleting this session's indexed knowledge.",
        )

    db.delete(session)
    db.commit()
    return None


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
        for telemetry in knowledge.telemetry_events:
            AIUsageService(db).record(session_id, telemetry)
        raise HTTPException(
            status_code=503,
            detail="The session knowledge store could not complete the search.",
        ) from error

    for telemetry in knowledge.telemetry_events:
        AIUsageService(db).record(session_id, telemetry)

    return {
        "sessionId": session_id,
        "query": request.query,
        "matches": matches,
    }
