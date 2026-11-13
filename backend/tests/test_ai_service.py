import json
from types import SimpleNamespace

import pytest

from app.services.ai_service import AIService
from app.services.process_service import ProcessService


def _valid_optimization() -> dict:
    return {
        "process_specification": {
            "business_domain": "finance",
            "business_domain_label": "Finanzen",
            "process_goal": "Rechnungen zuverlässig prüfen.",
            "actors": ["Finanzteam"],
            "inputs": ["PDF-Rechnungen"],
            "systems": ["SAP S/4HANA"],
            "business_rules": ["Abweichungen manuell prüfen."],
            "exception_paths": ["Unklare Rechnungen weiterleiten."],
            "outputs": ["Geprüfter Buchungsvorschlag"],
            "success_metrics": ["Bearbeitungszeit"],
        },
        "optimization_summary": "Rechnungsdaten werden automatisch erfasst und geprüft.",
        "design_principles": ["Standardfälle automatisieren.", "Ausnahmen gezielt weiterleiten."],
        "recommended_changes": [],
        "expected_benefits": [],
        "automation_potential_score": 80,
        "automation_potential_reason": "Wiederkehrende Prüfschritte sind standardisierbar.",
        "automation_opportunities": [],
        "integrations": [],
        "human_approval_required": True,
        "human_approval_reason": "Zahlungsrelevante Entscheidungen benötigen eine Freigabe.",
        "workflow_name": "Rechnungsprüfung",
        "workflow_trigger": "Neue Rechnung geht ein.",
        "workflow_steps": [
            {
                "type": "trigger",
                "name": "Rechnungseingang",
                "description": "Neue Rechnung erfassen.",
                "connector": "",
                "requires_approval": False,
            },
            {
                "type": "generate",
                "name": "Prüfergebnis vorbereiten",
                "description": "Geprüfte Rechnungsdaten bereitstellen.",
                "connector": "",
                "requires_approval": False,
            },
        ],
        "risks": [],
        "assumptions": [],
    }


def test_second_stage_optimization_uses_json_mode_and_validates_schema(monkeypatch):
    payload = _valid_optimization()
    response = SimpleNamespace(
        output_text=json.dumps(payload, ensure_ascii=False),
        usage=SimpleNamespace(input_tokens=900, output_tokens=500, total_tokens=1400),
    )

    class FakeResponses:
        def __init__(self):
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            return response

    fake_responses = FakeResponses()
    service = AIService(api_key="test-key", model="test-optimization-model")
    service._client = SimpleNamespace(responses=fake_responses)

    result = service.optimize_process(
        description="Eingangsrechnungen prüfen.",
        analysis={"summary": "Manuelle Rechnungsprüfung"},
        questions=[{"id": "q-1", "prompt": "Welches ERP wird verwendet?"}],
        answers={"q-1": "SAP S/4HANA"},
        language="de",
    )

    assert result["workflow_name"] == "Rechnungsprüfung"
    assert fake_responses.kwargs["text"] == {"format": {"type": "json_object"}}
    assert "text_format" not in fake_responses.kwargs
    assert "JSON" in fake_responses.kwargs["input"][0]["content"]
    assert service.last_call_telemetry["status"] == "success"
    assert service.last_call_telemetry["totalTokens"] == 1400


def test_second_stage_rejects_invalid_json_and_records_fallback():
    response = SimpleNamespace(
        output_text="{invalid json",
        usage=SimpleNamespace(input_tokens=100, output_tokens=20, total_tokens=120),
    )

    class FakeResponses:
        def create(self, **kwargs):
            return response

    service = AIService(api_key="test-key", model="test-optimization-model")
    service._client = SimpleNamespace(responses=FakeResponses())

    with pytest.raises(json.JSONDecodeError):
        service.optimize_process(
            description="Rechnungen prüfen.",
            analysis={},
            questions=[],
            answers={},
            language="de",
        )

    assert service.last_call_telemetry["status"] == "fallback"
    assert service.last_call_telemetry["errorType"] == "JSONDecodeError"
    assert service.last_call_telemetry["totalTokens"] == 120


def test_fallback_message_identifies_rate_limit_instead_of_generic_openai_failure():
    class RateLimitFailure(Exception):
        status_code = 429
        code = "rate_limit_exceeded"

    message = ProcessService._llm_fallback_reason(RateLimitFailure(), "de")

    assert "HTTP 429" in message
    assert "Rate-Limit" in message
