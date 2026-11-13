from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from typing import Literal
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.schemas.process import ProcessAnalyzeRequest
from app.services.ai_usage_service import AIUsageService
from app.services.process_service import ProcessService
from app.services.workflow_session_service import WorkflowSessionService
from app.services.document_service import DocumentProcessingService, MAX_FILE_BYTES, MAX_TOTAL_BYTES

router = APIRouter(prefix="/processes", tags=["processes"])



@router.post("/analyze-with-documents")
async def analyze_process_with_documents(
    description: str = Form(default="", max_length=8_000),
    analysis_strategy: Literal["auto", "rules", "llm"] = Form(default="auto"),
    analysis_language: Literal["de", "en"] = Form(default="de"),
    business_domain: str = Form(default="general", max_length=80),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    processor = DocumentProcessingService()
    uploaded: list[tuple[str, bytes]] = []
    total_size = 0
    try:
        if not files:
            raise HTTPException(status_code=422, detail="Upload at least one document or image.")
        if len(files) > 8:
            raise HTTPException(status_code=422, detail="Upload no more than 8 files at once.")
        for file in files:
            filename = file.filename or "uploaded-file"
            content = await file.read(MAX_FILE_BYTES + 1)
            total_size += len(content)
            if len(content) > MAX_FILE_BYTES:
                raise HTTPException(status_code=413, detail=f"{filename}: each file must be 10 MB or smaller.")
            if total_size > MAX_TOTAL_BYTES:
                raise HTTPException(status_code=413, detail="The combined upload size exceeds 25 MB.")
            uploaded.append((filename, content))
        try:
            extracted = processor.process(uploaded)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        for file in files:
            await file.close()

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
            f"{analysis_description}\\n\\nReference document evidence:\\n{extracted['text_context']}"
            if analysis_description else extracted["text_context"]
        )
    analysis_description = analysis_description[:45_000]

    analysis = ProcessService(db).analyze(
        analysis_description,
        strategy=analysis_strategy,
        language=analysis_language,
        business_domain=business_domain,
        image_data_urls=extracted["image_data_urls"],
    )
    usage_telemetry = analysis.pop("_aiUsageTelemetry", None)
    session = WorkflowSessionService(db).create(
        description=analysis_description,
        analysis=analysis,
        strategy=analysis_strategy,
        language=analysis_language,
        business_domain=business_domain,
    )
    if usage_telemetry:
        AIUsageService(db).record(session["id"], usage_telemetry)

    if extracted["image_data_urls"] and not analysis.get("llmUsed"):
        extracted["warnings"].append(
            "Visual content was not interpreted by a vision model. The fallback analysis used extracted text only."
        )
    analysis["description"] = description.strip() or "Uploaded process documents"
    analysis["sourceDocuments"] = extracted["documents"]
    analysis["documentWarnings"] = extracted["warnings"]
    return {
        **analysis,
        "processSessionId": session["id"],
        "workflowStatus": session["status"],
        "openQuestions": session["openQuestions"],
    }


@router.post("/analyze")
def analyze_process(request: ProcessAnalyzeRequest, db: Session = Depends(get_db)):
    analysis = ProcessService(db).analyze(
        request.description,
        strategy=request.analysis_strategy,
        language=request.analysis_language,
        business_domain=request.business_domain,
    )
    usage_telemetry = analysis.pop("_aiUsageTelemetry", None)

    session = WorkflowSessionService(db).create(
        description=request.description,
        analysis=analysis,
        strategy=request.analysis_strategy,
        language=request.analysis_language,
        business_domain=request.business_domain,
    )
    if usage_telemetry:
        AIUsageService(db).record(session["id"], usage_telemetry)

    return {
        **analysis,
        "processSessionId": session["id"],
        "workflowStatus": session["status"],
        "openQuestions": session["openQuestions"],
    }
