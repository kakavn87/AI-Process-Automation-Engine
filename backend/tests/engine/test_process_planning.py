from app.engine.analyzer.process_analyzer import ProcessAnalyzer
from app.engine.workflow.generator import WorkflowGenerator
from app.engine.workflow.validator import validate


SAMPLE_PROCESS = """Every Monday, the finance team receives Excel and PDF reports from different departments by email.
Currently, an employee manually downloads all attachments, extracts the relevant data, combines the information
into a master Excel spreadsheet, checks for missing values and calculates the weekly results. After that, the
employee creates a summary report and sends it to the management team via Microsoft Teams. Before sending the
final report, a manager must review and approve it."""


def test_finance_process_is_expanded_into_structured_analysis():
    analysis = ProcessAnalyzer().analyze(SAMPLE_PROCESS)
    assert analysis["automationScore"] == 85
    assert analysis["signals"] == ["email", "pdf", "excel", "manual", "teams", "weekly"]
    assert len(analysis["currentProcess"]) >= 5
    assert len(analysis["automationOpportunities"]) >= 4
    assert analysis["humanApproval"]["required"] is True


def test_generated_workflow_places_approval_before_teams_notification():
    analysis = ProcessAnalyzer().analyze(SAMPLE_PROCESS)
    workflow = WorkflowGenerator().generate(SAMPLE_PROCESS, analysis["signals"])
    validate(workflow)
    types = [step["type"] for step in workflow["steps"]]
    assert types.index("approval") < types.index("notify")


def test_validator_rejects_notification_without_required_approval():
    workflow = {
        "steps": [
            {"id": "notify-1", "type": "notify", "config": {"requiresApproval": True}}
        ]
    }
    try:
        validate(workflow)
        assert False, "Expected a missing approval gate to be rejected"
    except ValueError as error:
        assert "approval step must come before" in str(error)
