import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.services.knowledge_service import DocumentIngestionService, MAX_DOCUMENT_BYTES, RAGService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["knowledge-documents"])


class DocumentSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    document_ids: list[str] = Field(default_factory=list, max_length=30)
    top_k: int = Field(default=8, ge=1, le=20)


def require_private_knowledge() -> None:
    if not settings.KNOWLEDGE_PERSISTENCE_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Persistent knowledge is disabled on this instance. Enable it only on a private, authenticated deployment.",
        )


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    if not settings.KNOWLEDGE_PERSISTENCE_ENABLED:
        return {"enabled": False, "documents": []}
    return {"enabled": True, "documents": RAGService(db).list_documents()}


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    require_private_knowledge()
    filename = file.filename or ""
    if not filename:
        raise HTTPException(status_code=400, detail="Please select a document.")
    content = await file.read(MAX_DOCUMENT_BYTES + 1)
    await file.close()
    if len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="The document exceeds the 25 MB upload limit.")
    try:
        return DocumentIngestionService(db).ingest(filename, content, file.content_type)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        logger.exception("Knowledge document ingestion failed.")
        raise HTTPException(
            status_code=500,
            detail="The document could not be indexed. Check backend logs and AI/embedding configuration.",
        ) from exc


@router.post("/search")
def search_documents(request: DocumentSearchRequest, db: Session = Depends(get_db)):
    require_private_knowledge()
    return {"results": RAGService(db).search(request.query, request.document_ids, request.top_k)}
