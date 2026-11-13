from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.process import ProcessAnalyzeRequest
from app.services.ai_usage_service import AIUsageService
from app.services.process_service import ProcessService
from app.services.workflow_session_service import WorkflowSessionService

router = APIRouter(prefix="/processes", tags=["processes"])


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
