from app.api.routes.health import health


def test_health_exposes_llm_readiness_without_secret_values():
    result = health()
    assert result["status"] == "ok"
    assert result["llm"]["provider"] == "openai"
    assert "enabled" in result["llm"]
    assert "model" in result["llm"]
    assert "api_key" not in result["llm"]
