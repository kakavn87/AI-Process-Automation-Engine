from urllib.parse import urlparse

from fastapi import APIRouter

from app.core.config import settings
from app.services.execution_service import ExecutionService

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


@router.get("/readiness")
def get_integration_readiness():
    """Expose non-secret integration state for the Step 6 setup dashboard."""
    base_url = settings.OPENAI_BASE_URL.strip()
    is_litellm = (
        settings.AI_GATEWAY_PROVIDER.strip().lower() == "litellm"
        or "litellm" in base_url.lower()
    )
    gateway_provider = (
        "LiteLLM" if is_litellm
        else "OpenAI-compatible gateway" if base_url
        else "Direct OpenAI API"
    )
    open_webui_url = _safe_http_url(settings.OPENWEBUI_URL)

    webhook = ExecutionService.live_execution_readiness()
    return {
        "aiGateway": {
            "provider": gateway_provider,
            "configured": bool(settings.OPENAI_API_KEY.strip()),
            "baseUrlConfigured": bool(base_url),
            "model": settings.OPENAI_MODEL,
            "status": "ready" if settings.OPENAI_API_KEY.strip() else "not_configured",
        },
        "openWebUI": {
            "configured": open_webui_url is not None,
            "url": open_webui_url,
            "status": "ready" if open_webui_url else "not_configured",
        },
        "businessConnectors": [
            {
                "id": "workflow_webhook",
                "name": "HTTPS Workflow Webhook",
                "status": "ready" if webhook["ready"] else "setup_required",
                "description": "Admin-configured outbound workflow handoff.",
            },
            {
                "id": "microsoft_365",
                "name": "Microsoft 365",
                "status": "planned",
                "description": "Outlook, Teams and SharePoint require tenant OAuth configuration.",
            },
            {
                "id": "sap",
                "name": "SAP / ERP",
                "status": "planned",
                "description": "Requires an approved SAP API destination and credentials.",
            },
            {
                "id": "custom_rest",
                "name": "Custom REST API",
                "status": "planned",
                "description": "A per-workspace connector with credential storage is not enabled in this single-user MVP.",
            },
        ],
        "liveWebhook": webhook,
        "securityNote": (
            "Connector credentials are server-side only. Per-user OAuth connections and tenant isolation "
            "must be implemented before customer-managed integrations are enabled."
        ),
    }
