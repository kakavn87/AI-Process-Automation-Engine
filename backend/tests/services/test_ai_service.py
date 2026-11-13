from app.services.ai_service import AIService


def test_ai_service_is_disabled_without_api_key():
    service = AIService(api_key="")
    assert service.is_configured is False
