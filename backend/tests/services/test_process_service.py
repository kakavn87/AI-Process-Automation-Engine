from app.engine.analyzer.process_analyzer import ProcessAnalyzer
from app.services.ai_service import AIService
from app.services.process_service import ProcessService


SAMPLE_PROCESS = """Every Monday, the finance team receives Excel and PDF reports from different departments by email.
An employee manually downloads all attachments, extracts the relevant data, combines them into a master Excel
spreadsheet, checks for missing values, calculates weekly results, and creates a summary report.
The report is sent to management via Microsoft Teams after a manager reviews and approves it."""


def test_process_analyzer_detects_expected_signals():
    result = ProcessAnalyzer().analyze(SAMPLE_PROCESS)
    assert result["automationScore"] == 85
    assert result["signals"] == ["email", "pdf", "excel", "manual", "teams", "weekly"]


def test_process_service_falls_back_when_api_key_is_missing():
    service = ProcessService(db=None, ai_service=AIService(api_key=""))
    result = service.analyze(SAMPLE_PROCESS)

    assert result["llmUsed"] is False
    assert result["analysisMode"] == "deterministic_rules_v1"
    assert result["automationScore"] == 85
    assert result["proposedWorkflow"]["steps"]
    assert result["detectedDetails"]["businessDomain"] == "finance"


def test_fallback_workflow_has_approval_after_report_generation():
    service = ProcessService(db=None, ai_service=AIService(api_key=""))
    result = service.analyze(SAMPLE_PROCESS)
    steps = result["proposedWorkflow"]["steps"]
    types = [step["type"] for step in steps]

    assert types.index("generate") < types.index("approval") < types.index("notify")
    assert steps[types.index("notify")]["config"]["requiresApproval"] is True
    assert result["proposedWorkflow"]["name"] == "Weekly Finance Reporting"


class FakeAIService:
    is_configured = True
    model = "test-model"

    def __init__(self):
        self.calls = 0

    def analyze_process(self, description, signals):
        self.calls += 1
        return {
            "summary": "AI-generated summary.",
            "current_process": ["Receive source data.", "Create report."],
            "automation_opportunities": [
                {"title": "Automate extraction", "description": "Extract data.", "impact": "high"}
            ],
            "integrations": [{"name": "Microsoft Teams", "purpose": "Deliver approved reports."}],
            "human_approval_required": False,
            "human_approval_reason": "No approval was explicitly detected.",
            "human_approval_gate_before": "Not specified",
            "workflow_name": "AI Workflow",
            "workflow_trigger": "Start weekly.",
            "workflow_steps": [
                {
                    "type": "trigger",
                    "name": "Start",
                    "description": "Start the workflow.",
                    "connector": "",
                    "requires_approval": False,
                },
                {
                    "type": "generate",
                    "name": "Generate report",
                    "description": "Create the report.",
                    "connector": "",
                    "requires_approval": False,
                },
                {
                    "type": "notify",
                    "name": "Notify Teams",
                    "description": "Send approved report.",
                    "connector": "microsoft_teams",
                    "requires_approval": False,
                },
            ],
            "risks": ["Check data quality."],
            "assumptions": [],
            "questions": ["Which Teams channel should be used?"],
        }


def test_llm_result_is_used_and_backend_inserts_mandatory_approval_gate():
    service = ProcessService(db=None, ai_service=FakeAIService())
    result = service.analyze(SAMPLE_PROCESS, strategy="llm")
    steps = result["proposedWorkflow"]["steps"]
    types = [step["type"] for step in steps]

    assert result["llmUsed"] is True
    assert result["analysisMode"] == "openai_responses"
    assert result["detectedDetails"]["businessDomain"] == "finance"
    assert types.index("generate") < types.index("approval") < types.index("notify")
    assert steps[types.index("notify")]["config"]["requiresApproval"] is True



def test_auto_strategy_uses_python_for_a_supported_process_even_when_llm_is_available():
    ai_service = FakeAIService()
    service = ProcessService(db=None, ai_service=ai_service)

    result = service.analyze(SAMPLE_PROCESS)

    assert result["llmUsed"] is False
    assert ai_service.calls == 0
    assert result["routingDecision"]["selectedEngine"] == "rules"
    assert result["routingDecision"]["rulesSuitable"] is True
    assert result["routingDecision"]["ruleConfidence"] >= 70


def test_auto_strategy_uses_llm_for_ambiguous_conditional_process():
    ai_service = FakeAIService()
    service = ProcessService(db=None, ai_service=ai_service)
    description = (
        "Our team handles customer requests using different rules depending on customer risk "
        "and contract value. Some requests require multiple approval levels before notifying the customer."
    )

    result = service.analyze(description)

    assert result["llmUsed"] is True
    assert ai_service.calls == 1
    assert result["routingDecision"]["selectedEngine"] == "llm"
    assert "conditional_logic" in result["routingDecision"]["complexityFlags"]


def test_rules_strategy_never_calls_llm_even_for_complex_process():
    ai_service = FakeAIService()
    service = ProcessService(db=None, ai_service=ai_service)
    description = (
        "Our team handles customer requests using different rules depending on customer risk "
        "and contract value. Some requests require multiple approval levels before notifying the customer."
    )

    result = service.analyze(description, strategy="rules")

    assert result["llmUsed"] is False
    assert ai_service.calls == 0
    assert result["routingDecision"]["selectedEngine"] == "rules"
    assert result["routingDecision"]["requestedStrategy"] == "rules"


def test_llm_strategy_falls_back_when_api_key_is_missing():
    service = ProcessService(db=None, ai_service=AIService(api_key=""))

    result = service.analyze(SAMPLE_PROCESS, strategy="llm")

    assert result["llmUsed"] is False
    assert result["routingDecision"]["selectedEngine"] == "rules"
    assert result["routingDecision"]["llmAvailable"] is False
    assert "not configured" in result["routingDecision"]["reason"]
