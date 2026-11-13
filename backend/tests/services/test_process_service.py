from app.engine.analyzer.process_analyzer import ProcessAnalyzer
from app.schemas.ai_analysis import LLMProcessAnalysis, LLMWorkflowStep
from app.services.process_service import ProcessService


def test_process_analyzer():
    result = ProcessAnalyzer().analyze("Weekly PDF email process")
    assert result["automationScore"] > 0


def test_process_service_uses_rules_fallback_when_llm_is_unavailable():
    service = ProcessService(db=None)
    service.ai_service.analyze_process = lambda description: None

    result = service.analyze("Weekly PDF email process")

    assert result["analysisMode"] == "rules_fallback"
    assert result["proposedWorkflow"]["steps"]


def test_process_service_inserts_approval_before_outbound_llm_step():
    service = ProcessService(db=None)
    analysis = LLMProcessAnalysis(
        automation_score=80,
        signals=["teams"],
        summary="A process that publishes a report to Teams.",
        current_process=["Prepare the report.", "Send it to Teams."],
        automation_opportunities=[],
        integrations=[],
        approval_required=False,
        approval_reason="External delivery requires review.",
        approval_gate_before="Teams delivery",
        risks=[],
        assumptions=[],
        questions=[],
        workflow_name="Report delivery",
        workflow_trigger="Start when ready.",
        workflow_steps=[
            LLMWorkflowStep(
                type="trigger", name="Start", description="Start workflow.",
                connector="", requires_approval=False,
            ),
            LLMWorkflowStep(
                type="notify", name="Send to Teams", description="Publish the report.",
                connector="microsoft_teams", requires_approval=False,
            ),
        ],
    )
    service.ai_service.analyze_process = lambda description: analysis

    result = service.analyze("Send a report to Teams.")

    steps = result["proposedWorkflow"]["steps"]
    types = [step["type"] for step in steps]
    assert result["analysisMode"] == "openai_llm"
    assert types.index("approval") < types.index("notify")
    assert steps[types.index("notify")]["config"]["requiresApproval"] is True
