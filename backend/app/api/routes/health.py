from fastapi import APIRouter

from app.core.config import settings
from app.services.ai_service import AIService

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    ai_service = AIService()
    return {
        "status": "ok",
        "llm": {
            "enabled": ai_service.is_configured,
            "provider": "openai",
            "model": settings.OPENAI_MODEL,
        },
    }
