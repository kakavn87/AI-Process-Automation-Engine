from app.engine.analyzer.process_analyzer import ProcessAnalyzer
from app.engine.workflow.generator import WorkflowGenerator
from app.engine.workflow.validator import validate


SAMPLE_PROCESS = """Every Monday, the finance team receives Excel and PDF reports from different departments by email.
Currently, an employee manually downloads all attachments, extracts the relevant data, combines the information
into a master Excel spreadsheet, checks for missing values and calculates the weekly results. After that, the
employee creates a summary report and sends it to the management team via Microsoft Teams. Before sending the
final report, a manager must review and approve it."""


GERMAN_PROCESS = """Jeden Montag erhält die Finanzabteilung PDF- und Excel-Rechnungen per E-Mail.
Mitarbeiter laden die Anhänge manuell herunter, extrahieren die Daten, prüfen fehlende Werte,
berechnen Summen, erstellen einen Bericht und senden ihn per Teams an den Manager zur Freigabe."""


def test_finance_process_is_expanded_into_structured_analysis():
    analysis = ProcessAnalyzer().analyze(SAMPLE_PROCESS)
    assert analysis["automationScore"] == 85
    assert analysis["signals"] == ["email", "pdf", "excel", "manual", "teams", "weekly"]
    assert len(analysis["currentProcess"]) >= 5
    assert len(analysis["automationOpportunities"]) >= 4
    assert analysis["humanApproval"]["required"] is True


def test_fallback_extracts_structured_process_details_without_an_llm():
    analysis = ProcessAnalyzer().analyze(GERMAN_PROCESS)
    details = analysis["detectedDetails"]

    assert details["businessDomain"] == "finance"
    assert details["cadence"] == {"frequency": "weekly", "day": "Monday"}
    assert details["sourceChannels"] == ["Microsoft Outlook"]
    assert details["fileTypes"] == ["PDF", "Excel"]
    assert "validate_data" in details["activities"]
    assert "calculate_metrics" in details["activities"]
    assert details["deliveryChannels"] == ["Microsoft Teams"]
    assert "Manager" in details["roles"]
    assert details["extractionMethod"] == "deterministic_rules"


def test_generated_workflow_uses_extracted_details_and_places_approval_before_teams():
    analysis = ProcessAnalyzer().analyze(SAMPLE_PROCESS)
    workflow = WorkflowGenerator().generate(
        SAMPLE_PROCESS,
        analysis["signals"],
        analysis["detectedDetails"],
    )
    validate(workflow)

    assert workflow["name"] == "Weekly Finance Reporting"
    assert "Monday" in workflow["trigger"]
    types = [step["type"] for step in workflow["steps"]]
    assert types.index("collect") < types.index("extract") < types.index("validate")
    assert types.index("generate") < types.index("approval") < types.index("notify")


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


def test_validator_rejects_outbound_step_without_explicit_approval_flag():
    workflow = {
        "steps": [
            {"id": "approval-1", "type": "approval", "config": {}},
            {"id": "notify-1", "type": "notify", "config": {"requiresApproval": False}},
        ]
    }
    try:
        validate(workflow)
        assert False, "Expected an outbound step without explicit approval to be rejected"
    except ValueError as error:
        assert "must explicitly require human approval" in str(error)
