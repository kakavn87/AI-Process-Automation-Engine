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
        self.business_domain = "finance"

    def analyze_process(self, description, signals, language="en"):
        self.calls += 1
        return {
            "process_specification": {
                "business_domain": self.business_domain,
                "business_domain_label": self.business_domain.replace("_", " ").title(),
                "process_goal": "Prepare and distribute a reliable recurring report.",
                "actors": ["Finance team", "Manager"],
                "inputs": ["Excel reports", "PDF attachments"],
                "systems": ["Microsoft Outlook", "Microsoft Teams"],
                "business_rules": ["Validate source values before calculation."],
                "exception_paths": ["Route missing values for manual review."],
                "outputs": ["Approved summary report"],
                "success_metrics": ["Processing time", "Data accuracy"],
            },
            "automation_potential_score": 82,
            "automation_potential_reason": "Several repeatable data preparation and approval steps can be automated.",
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
    assert result["automationScore"] == 82
    assert result["automationScoreNote"] == "Several repeatable data preparation and approval steps can be automated."
    assert result["detectedDetails"]["businessDomain"] == "finance"
    assert types.index("generate") < types.index("approval") < types.index("notify")
    assert steps[types.index("notify")]["config"]["requiresApproval"] is True



def test_auto_strategy_uses_llm_first_when_api_is_available_even_for_supported_process():
    ai_service = FakeAIService()
    service = ProcessService(db=None, ai_service=ai_service)

    result = service.analyze(SAMPLE_PROCESS)

    assert result["llmUsed"] is True
    assert ai_service.calls == 1
    assert result["routingDecision"]["selectedEngine"] == "llm"
    assert result["routingDecision"]["rulesSuitable"] is True
    assert result["routingDecision"]["ruleConfidence"] >= 70
    assert result["processSpecification"]["schemaVersion"] == "1.0"
    assert result["processSpecification"]["goal"] == "Prepare and distribute a reliable recurring report."


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


def test_german_response_and_explicit_business_domain_are_localized():
    service = ProcessService(db=None, ai_service=AIService(api_key=""))
    description = (
        "Jeden Tag prüft die Produktion Qualitätsprotokolle. "
        "Mitarbeitende erfassen Produktionsmengen, validieren Messwerte, "
        "berechnen Ausschussquoten und erstellen einen Bericht."
    )

    result = service.analyze(
        description,
        strategy="rules",
        language="de",
        business_domain="manufacturing",
    )

    assert result["detectedDetails"]["businessDomain"] == "manufacturing"
    assert result["detectedDetails"]["businessDomainLabel"] == "Produktion"
    assert result["summary"].startswith("Der Prozess umfasst")
    assert result["analysisNote"].startswith("Python-Regeln") or "Python-Regeln" in result["analysisNote"]
    assert result["proposedWorkflow"]["name"].endswith("-Workflow")
    assert all("Start workflow" not in step["name"] for step in result["proposedWorkflow"]["steps"])


def test_explicit_industry_selection_is_respected_even_without_keywords():
    service = ProcessService(db=None, ai_service=AIService(api_key=""))
    result = service.analyze(
        "Collect requests, validate details, create an output and notify the owner.",
        strategy="rules",
        business_domain="legal_compliance",
    )

    assert result["detectedDetails"]["businessDomain"] == "legal_compliance"



def test_ai_engine_supports_a_business_domain_outside_the_example_gallery():
    ai_service = FakeAIService()
    ai_service.business_domain = "renewable_energy"
    service = ProcessService(db=None, ai_service=ai_service)

    result = service.analyze(
        "The energy team forecasts solar generation, compares output with grid demand, "
        "and prepares a balancing report for the market operator."
    )

    assert result["llmUsed"] is True
    assert result["detectedDetails"]["businessDomain"] == "renewable_energy"
    assert result["detectedDetails"]["businessDomainLabel"] == "Renewable Energy"
    assert result["processSpecification"]["businessDomain"] == "renewable_energy"
    assert result["processSpecification"]["inputs"] == ["Excel reports", "PDF attachments"]



def test_python_fallback_does_not_return_zero_for_a_described_german_process():
    service = ProcessService(db=None, ai_service=AIService(api_key=""))
    description = (
        "Die Mitarbeitenden prüfen eingehende Wartungsanfragen, priorisieren Störungen, "
        "weisen Techniker zu und dokumentieren die Reparatur."
    )

    result = service.analyze(description, strategy="rules", language="de")

    assert result["automationScore"] > 0


def test_routing_does_not_mark_long_description_as_complexity_failure():
    from app.engine.analyzer.routing_policy import ProcessRoutingPolicy

    analysis = ProcessAnalyzer().analyze(SAMPLE_PROCESS)
    result = ProcessRoutingPolicy().decide(
        description=SAMPLE_PROCESS + (" Zusatzinformationen." * 120),
        analysis=analysis,
        requested_strategy="auto",
        llm_available=True,
    )

    assert "long_description" not in result["complexityFlags"]


def test_incomplete_llm_response_has_actionable_fallback_message():
    error = ValueError("Invalid JSON: EOF while parsing an object")
    message = ProcessService._llm_fallback_reason(error, "de")

    assert "unvollständig" in message
    assert "erneut" in message


def test_exhausted_api_credits_have_specific_fallback_message():
    error = RuntimeError("insufficient_quota: credit_balance_exhausted")
    message = ProcessService._llm_fallback_reason(error, "de")

    assert "API-Guthaben" in message
