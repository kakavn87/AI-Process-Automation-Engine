from app.engine.analyzer.process_analyzer import ProcessAnalyzer
from app.services.ai_service import AIService
from app.services.process_service import ProcessService


SAMPLE_PROCESS = """Every Monday, the finance team receives Excel and PDF reports from different departments by email.
An employee manually downloads all attachments, extracts the relevant data, combines it into a master Excel
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


def test_fallback_workflow_has_approval_before_teams_notification():
    service = ProcessService(db=None, ai_service=AIService(api_key=""))
    result = service.analyze(SAMPLE_PROCESS)
    steps = result["proposedWorkflow"]["steps"]
    types = [step["type"] for step in steps]

    assert types.index("approval") < types.index("notify")
    assert steps[types.index("notify")]["config"]["requiresApproval"] is True
