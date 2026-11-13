import json
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.process import ProcessAnalyzeRequest
from app.services.ai_usage_service import AIUsageService
from app.services.document_service import DocumentProcessingService, MAX_FILES, MAX_FILE_BYTES, MAX_TOTAL_BYTES
from app.services.knowledge_service import DocumentIngestionService, RAGService
from app.services.process_service import ProcessService
from app.services.workflow_session_service import WorkflowSessionService

router = APIRouter(prefix="/processes", tags=["processes"])


def _create_session_response(
    db: Session, description: str, analysis_strategy: str,
    analysis_language: str, business_domain: str, analysis: dict,
) -> dict:
    usage_telemetry = analysis.pop("_aiUsageTelemetry", None)
    session = WorkflowSessionService(db).create(
        description=description, analysis=analysis, strategy=analysis_strategy,
        language=analysis_language, business_domain=business_domain,
    )
    if usage_telemetry:
        AIUsageService(db).record(session["id"], usage_telemetry)
    return {
        **analysis,
        "processSessionId": session["id"],
        "workflowStatus": session["status"],
        "openQuestions": session["openQuestions"],
    }


@router.post("/analyze-with-documents")
async def analyze_process_with_documents(
    description: str = Form(default="", max_length=8_000),
    analysis_strategy: Literal["auto", "rules", "llm"] = Form(default="auto"),
    analysis_language: Literal["de", "en"] = Form(default="de"),
    business_domain: str = Form(default="general", max_length=80),
    document_ids: str = Form(default="[]"),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    uploaded: list[tuple[str, bytes, str | None]] = []
    total_size = 0
    try:
        if not files and not document_ids.strip():
            raise HTTPException(status_code=422, detail="Upload at least one document or select a saved knowledge source.")
        if len(files) > MAX_FILES:
            raise HTTPException(status_code=422, detail=f"Upload no more than {MAX_FILES} files at once.")
        for file in files:
            filename = file.filename or "uploaded-file"
            content = await file.read(MAX_FILE_BYTES + 1)
            total_size += len(content)
            if len(content) > MAX_FILE_BYTES:
                raise HTTPException(status_code=413, detail=f"{filename}: each file must be 10 MB or smaller.")
            if total_size > MAX_TOTAL_BYTES:
                raise HTTPException(status_code=413, detail="The combined upload size exceeds 25 MB.")
            uploaded.append((filename, content, file.content_type))
    finally:
        for file in files:
            await file.close()

    try:
        selected_ids = json.loads(document_ids or "[]")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="document_ids must be a JSON array.") from exc
    if not isinstance(selected_ids, list) or any(not isinstance(value, str) for value in selected_ids):
        raise HTTPException(status_code=422, detail="document_ids must be a JSON array of document IDs.")
    selected_ids = list(dict.fromkeys(selected_ids))[:30]
    if selected_ids and not settings.KNOWLEDGE_PERSISTENCE_ENABLED:
        raise HTTPException(status_code=403, detail="Saved knowledge is disabled on this instance.")

    # Public previews remain memory-only because they have no authenticated workspace.
    # Enable persistence only on a private/self-hosted instance with access control.
    if settings.KNOWLEDGE_PERSISTENCE_ENABLED:
        try:
            ingestion = DocumentIngestionService(db)
            persisted = [ingestion.ingest(name, content, mime) for name, content, mime in uploaded]
            all_ids = list(dict.fromkeys(selected_ids + [item["id"] for item in persisted]))
            evidence_query = description.strip() or (
                "business process workflow activities process steps actors inputs outputs "
                "decisions approvals responsibilities systems exceptions"
            )
            knowledge = RAGService(db).build_context(evidence_query, all_ids, top_k=10)
            if not knowledge["context"]:
                raise HTTPException(
                    status_code=422,
                    detail="No retrievable business-process content was found. Add a short description or select readable documents.",
                )
            effective_description = description.strip() or "Analyze the selected business-process documents and identify the process."
            analysis = ProcessService(db).analyze(
                effective_description,
                strategy=analysis_strategy,
                language=analysis_language,
                business_domain=business_domain,
                knowledge_context=knowledge["context"],
            )
            analysis["description"] = description.strip() or "Selected business-process documents"
            analysis["knowledgeSources"] = knowledge["sources"]
            analysis["knowledgeDocumentIds"] = all_ids
            analysis["sourceDocuments"] = [
                {
                    "filename": item["fileName"],
                    "fileType": item["fileType"].upper(),
                    "extractedCharacters": item.get("sourceMetadata", {}).get("characterCount", 0),
                    "pages": None,
                    "visualAssets": 1 if item.get("sourceMetadata", {}).get("visionUsed") else 0,
                }
                for item in persisted
            ]
            analysis["documentWarnings"] = [
                f"{item['fileName']}: review the extracted content and cited source locations."
                for item in persisted
                if item.get("sourceMetadata", {}).get("ocrUsed") or item.get("sourceMetadata", {}).get("visionUsed")
            ]
            return _create_session_response(
                db, description.strip() or "Selected business-process documents",
                analysis_strategy, analysis_language, business_domain, analysis,
            )
        except HTTPException:
            db.rollback()
            raise
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="The documents could not be indexed or analyzed. Check backend logs and AI gateway configuration.",
            ) from exc

    if selected_ids:
        raise HTTPException(
            status_code=403,
            detail="Saved knowledge sources are disabled on this public preview. Use the current-session upload instead.",
        )
    processor = DocumentProcessingService()
    try:
        extracted = processor.process([(name, content) for name, content, _ in uploaded])
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not description.strip() and not extracted["text_context"] and not extracted["image_data_urls"]:
        raise HTTPException(status_code=422, detail="Add a short process description or upload readable files.")
    if extracted["image_data_urls"] and not extracted["text_context"] and (
        not settings.OPENAI_API_KEY.strip() or analysis_strategy == "rules"
    ):
        raise HTTPException(
            status_code=503,
            detail="Image-only process analysis needs a configured vision-capable AI model. Select automatic or AI analysis, or add a text description.",
        )
    analysis_description = description.strip()
    if extracted["text_context"]:
        analysis_description = (
            f"{analysis_description}\n\nReference document evidence:\n{extracted['text_context']}"
            if analysis_description else extracted["text_context"]
        )
    analysis_description = analysis_description[:45_000]
    analysis = ProcessService(db).analyze(
        analysis_description, strategy=analysis_strategy, language=analysis_language,
        business_domain=business_domain, image_data_urls=extracted["image_data_urls"],
    )
    analysis["description"] = description.strip() or "Uploaded process documents"
    if extracted["image_data_urls"] and not analysis.get("llmUsed"):
        extracted["warnings"].append(
            "Visual content was not interpreted by a vision model. The fallback analysis used extracted text only."
        )
    analysis["sourceDocuments"] = extracted["documents"]
    analysis["documentWarnings"] = extracted["warnings"]
    return _create_session_response(
        db, description.strip() or "Uploaded process documents",
        analysis_strategy, analysis_language, business_domain, analysis,
    )


@router.post("/analyze")
def analyze_process(request: ProcessAnalyzeRequest, db: Session = Depends(get_db)):
    if request.document_ids and not settings.KNOWLEDGE_PERSISTENCE_ENABLED:
        raise HTTPException(status_code=403, detail="Saved knowledge is disabled on this instance.")
    knowledge = RAGService(db).build_context(request.description, request.document_ids, top_k=10)
    analysis = ProcessService(db).analyze(
        request.description, strategy=request.analysis_strategy,
        language=request.analysis_language, business_domain=request.business_domain,
        knowledge_context=knowledge["context"],
    )
    analysis["knowledgeSources"] = knowledge["sources"]
    analysis["knowledgeDocumentIds"] = request.document_ids
    return _create_session_response(
        db, request.description, request.analysis_strategy,
        request.analysis_language, request.business_domain, analysis,
    )
