from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.process import ProcessAnalyzeRequest
from app.services.process_service import ProcessService

router = APIRouter(prefix="/processes", tags=["processes"])

@router.post("/analyze")
def analyze_process(request: ProcessAnalyzeRequest, db: Session = Depends(get_db)):
    return ProcessService(db).analyze(request.description)
