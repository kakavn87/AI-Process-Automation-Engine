from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.ai_usage_service import AIUsageService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/usage")
def get_ai_usage(
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return AIUsageService(db).summary(limit=limit)
