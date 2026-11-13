from urllib.parse import urlparse

from fastapi import APIRouter

from app.core.config import settings
from app.services.execution_service import ExecutionService
from app.services.knowledge_base_service import KnowledgeBaseService

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _safe_http_url(value: str) -> str | None:
    candidate = value.strip()
    if not candidate:
        return None
    parsed = urlparse(candidate)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.query
    ):
        return None
    return candidate.rstrip("/")


def _rag_readiness() -> dict:
    try:
        return KnowledgeBaseService().readiness()
    except Exception:
        return {
            "enabled": settings.RAG_ENABLED,
            "configured": False,
            "connected": False,
            "status": "unavailable",
            "collection": settings.QDRANT_COLLECTION,
            "embeddingModel": settings.RAG_EMBEDDING_MODEL,
            "scope": "process_session",
            "message": "Der konfigurierte Vektorspeicher konnte nicht initialisiert werden. Prüfen Sie die serverseitige Qdrant-Konfiguration.",
        }


@router.get("/readiness")
def get_integration_readiness():
    """Expose non-secret integration state for the Step 6 setup dashboard."""
    base_url = settings.OPENAI_BASE_URL.strip()
    is_litellm = settings.AI_GATEWAY_PROVIDER.strip().lower() == "litellm"
    gateway_provider = (
        "LiteLLM-Gateway" if is_litellm
        else "OpenAI-kompatibles Gateway" if base_url
        else "Direkte OpenAI-Schnittstelle"
    )
    open_webui_url = _safe_http_url(settings.OPENWEBUI_URL)

    webhook = ExecutionService.live_execution_readiness()
    return {
        "aiGateway": {
            "provider": gateway_provider,
            "configured": bool(settings.OPENAI_API_KEY.strip()),
            "baseUrlConfigured": bool(base_url),
            "model": settings.OPENAI_MODEL,
            "visionModel": settings.OPENAI_VISION_MODEL.strip() or settings.OPENAI_MODEL,
            "embeddingModel": settings.RAG_EMBEDDING_MODEL,
            "status": "configured" if settings.OPENAI_API_KEY.strip() else "not_configured",
        },
        "rag": _rag_readiness(),
        "openWebUI": {
            "configured": open_webui_url is not None,
            "url": open_webui_url,
            "status": "configured" if open_webui_url else "not_configured",
        },
        "businessConnectors": [
            {
                "id": "workflow_webhook",
                "name": "HTTPS-Workflow-Webhook",
                "status": "ready" if webhook["ready"] else "setup_required",
                "description": "Serverseitig konfigurierter Übergabepunkt für freigegebene Workflows.",
            },
            {
                "id": "microsoft_365",
                "name": "Microsoft 365",
                "status": "planned",
                "description": "Outlook, Teams und SharePoint benötigen eine OAuth-Konfiguration pro Arbeitsbereich.",
            },
            {
                "id": "sap",
                "name": "SAP / ERP",
                "status": "planned",
                "description": "Benötigt einen freigegebenen SAP-API-Endpunkt und passende Zugangsdaten.",
            },
            {
                "id": "custom_rest",
                "name": "Individuelle REST-API",
                "status": "planned",
                "description": "Eine Schnittstelle mit getrennt gespeicherten Zugangsdaten pro Arbeitsbereich ist in diesem MVP noch nicht aktiviert.",
            },
        ],
        "liveWebhook": webhook,
        "securityNote": (
            "Zugangsdaten für Schnittstellen werden ausschließlich serverseitig gespeichert. Vor kundenseitig verwalteten Integrationen "
            "müssen OAuth-Verbindungen pro Benutzer und die Trennung der Arbeitsbereiche vollständig umgesetzt sein."
        ),
    }
