from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import TenantContext, get_tenant_context
from app.services.ai_usage_service import AIUsageService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/usage")
def get_ai_usage(
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    return AIUsageService(db, tenant_id=tenant_context.tenant_id).summary(limit=limit)
