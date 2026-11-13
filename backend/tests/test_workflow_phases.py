import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, settings
from app.core.database import Base
from app.engine.execution.action_executor import ActionExecutor
from app.engine.workflow.automation_engine import WorkflowAutomationEngine
from app.models.execution import ApprovalExecution  # noqa: F401 - registers approval execution table
from app.models.workflow_session import AIUsageEvent, WorkflowSession
from app.services.execution_service import ExecutionService
from app.services.question_service import QuestionService
from app.services.workflow_session_service import WorkflowSessionService


def test_question_service_builds_stable_typed_questions():
    service = QuestionService()
    questions = service.build([
        "Which mailbox should receive the report?",
        "Is manager approval required?",
        "  Is manager approval required?  ",
    ])

    assert len(questions) == 2
    assert questions[0]["type"] == "text"
    assert questions[1]["type"] == "boolean"
    assert questions[1]["id"] == service.build(["Is manager approval required?"])[0]["id"]
    assert questions[0]["placeholder"] == "Please enter a short answer."
    assert questions[1]["placeholder"] == "Choose yes or no."

    german_questions = service.build([
        "Welche Angaben werden benötigt?",
        "Ist eine Freigabe erforderlich?",
    ], language="de")
    assert german_questions[0]["placeholder"] == "Bitte kurz antworten …"
    assert german_questions[1]["placeholder"] == "Bitte Ja oder Nein auswählen."


def test_german_customer_support_questions_are_renderable_and_typed():
    questions = QuestionService().build([
        "Welche Themen- und Dringlichkeitsklassen sollen verwendet werden?",
        "Wie werden SLA-Fristen ermittelt und in Prioritäten übersetzt?",
        "Welche Zuständigkeitsregeln bestimmen das Team?",
        "In welchem System werden Anfragen nach der Zuordnung weiterbearbeitet?",
        "Soll die Freigabe für alle Anfragen gelten oder nur für unklare Fälle?",
    ])

    assert len(questions) == 5
    assert all(question["required"] for question in questions)
    assert [question["type"] for question in questions] == [
        "text", "text", "text", "text", "boolean"
    ]
    assert len({question["id"] for question in questions}) == 5


def test_question_service_validates_boolean_and_required_text():
    service = QuestionService()
    boolean_question = service.build(["Is approval required?"])[0]
    text_question = service.build(["Which folder should be monitored?"])[0]

    assert service.validate_answer(boolean_question, "no") is False
    assert service.validate_answer(boolean_question, True) is True
    assert service.validate_answer(text_question, "  Finance/Invoices  ") == "Finance/Invoices"

    try:
        service.validate_answer(text_question, "   ")
    except ValueError as error:
        assert "requires an answer" in str(error)
    else:
        raise AssertionError("A blank required answer must be rejected.")


def test_workflow_session_saves_partial_answers_then_prepares():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    analysis = {
        "questions": [
            "Which mailbox should receive the maintenance report?",
            "Is a manager review required before distribution?",
        ],
        "proposedWorkflow": {
            "name": "Maintenance review",
            "trigger": "Manual start",
            "steps": [
                {
                    "id": "step-1",
                    "type": "trigger",
                    "name": "Start",
                    "description": "Start manually",
                    "config": {"requiresApproval": False},
                },
                {
                    "id": "step-2",
                    "type": "generate",
                    "name": "Prepare report",
                    "description": "Prepare the maintenance report",
                    "config": {"requiresApproval": False},
                },
            ],
        },
    }

    with Session(engine) as db:
        service = WorkflowSessionService(db)
        created = service.create(
            description="Prepare a maintenance report and ask for missing information.",
            analysis=analysis,
            strategy="rules",
            language="en",
            business_domain="operations",
        )
        assert created["status"] == "needs_input"
        assert len(created["openQuestions"]) == 2

        first_question = created["questions"][0]
        partial = service.submit_answers(
            created["id"],
            {first_question["id"]: "maintenance@example.com"},
        )
        assert partial["status"] == "needs_input"
        assert len(partial["openQuestions"]) == 1

        second_question = partial["openQuestions"][0]
        prepared = service.submit_answers(
            created["id"],
            {second_question["id"]: "no"},
        )

        assert prepared["status"] == "ready_for_approval"
        assert prepared["openQuestions"] == []
        assert prepared["analysis"]["processingResult"]["engine"] == "deterministic_python"
        assert prepared["analysis"]["processingResult"]["externalActionsExecuted"] is False
        assert len(prepared["analysis"]["proposedWorkflow"]["confirmedContext"]) == 2
        assert prepared["answers"][second_question["id"]] is False

        approval_request = service.create_execution(created["id"])
        assert approval_request["session"]["status"] == "awaiting_approval"
        assert approval_request["execution"]["status"] == "awaiting_approval"

        approved = ExecutionService(db).approve(
            approval_request["execution"]["id"],
            "Reviewed in the workflow demo.",
        )
        completed = service.get(created["id"])
        assert approved["status"] == "completed"
        assert completed["status"] == "completed"
        assert completed["events"][-1]["event"] == "execution_completed"

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_automation_engine_never_enables_external_actions():
    analysis = {
        "proposedWorkflow": {
            "name": "Test workflow",
            "trigger": "Manual",
            "steps": [
                {
                    "id": "step-1",
                    "type": "trigger",
                    "name": "Start",
                    "description": "Manual start",
                    "config": {"requiresApproval": False},
                },
            ],
        }
    }

    result = WorkflowAutomationEngine().prepare(analysis, {"q-1": "confirmed"})

    assert result["proposedWorkflow"]["executionPolicy"]["mode"] == "simulation"
    assert result["proposedWorkflow"]["executionPolicy"]["externalActionsEnabled"] is False
    assert result["processingResult"]["externalActionsExecuted"] is False


def test_action_executor_rejects_unapproved_outbound_step():
    executor = ActionExecutor()
    step = {
        "id": "step-2",
        "type": "email",
        "name": "Send report",
        "config": {"requiresApproval": False},
    }

    try:
        executor.execute_step(step)
    except ValueError as error:
        assert "human approval" in str(error)
    else:
        raise AssertionError("Outbound actions without approval must be rejected.")


def test_approved_outbound_step_is_simulated_without_side_effect():
    result = ActionExecutor().execute_step({
        "id": "step-2",
        "type": "email",
        "name": "Send report",
        "config": {"requiresApproval": True},
    })

    assert result["status"] == "simulated"
    assert result["externalSideEffect"] is False



def _approved_execution(db):
    workflow = {
        "name": "Customer support routing",
        "trigger": "New support ticket",
        "steps": [
            {
                "id": "step-1",
                "type": "trigger",
                "name": "New ticket",
                "description": "A support ticket is created.",
                "config": {"requiresApproval": False},
            },
            {
                "id": "step-2",
                "type": "generate",
                "name": "Classify ticket",
                "description": "Classify topic and urgency.",
                "config": {"requiresApproval": False},
            },
        ],
    }
    service = ExecutionService(db)
    created = service.create(workflow)
    return service.approve(created["id"], "Approved for the demo.")


def test_live_webhook_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_EXECUTION_ENABLED", False)
    monkeypatch.setattr(settings, "WORKFLOW_WEBHOOK_URL", "")
    readiness = ExecutionService.live_execution_readiness()

    assert readiness["ready"] is False
    assert readiness["status"] == "disabled"

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        completed = _approved_execution(db)
        with pytest.raises(ValueError, match="disabled"):
            ExecutionService(db).run_live(completed["id"], confirmed=True, confirmation_token="")

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_live_webhook_requires_confirmation_and_dispatches_once(monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_EXECUTION_ENABLED", True)
    monkeypatch.setattr(settings, "WORKFLOW_WEBHOOK_URL", "https://hooks.example.com/process")
    monkeypatch.setattr(settings, "WORKFLOW_WEBHOOK_BEARER_TOKEN", "receiver-token")
    monkeypatch.setattr(settings, "WORKFLOW_LIVE_EXECUTION_TOKEN", "operator-token")
    monkeypatch.setattr(settings, "WORKFLOW_WEBHOOK_TIMEOUT_SECONDS", 4.0)

    calls = []

    class Accepted:
        status_code = 202

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return Accepted()

    monkeypatch.setattr("app.services.execution_service.httpx.post", fake_post)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        completed = _approved_execution(db)
        service = ExecutionService(db)

        with pytest.raises(ValueError, match="Explicit confirmation"):
            service.run_live(completed["id"], confirmed=False, confirmation_token="operator-token")
        with pytest.raises(ValueError, match="operator confirmation token"):
            service.run_live(completed["id"], confirmed=True, confirmation_token="wrong-token")

        delivered = service.run_live(completed["id"], confirmed=True, confirmation_token="operator-token")
        assert delivered["status"] == "completed"
        assert delivered["executionMode"] == "live_webhook"
        assert delivered["liveExecutionStatus"] == "succeeded"
        assert len(calls) == 1
        assert calls[0][0] == "https://hooks.example.com/process"
        assert calls[0][1]["headers"]["Authorization"] == "Bearer receiver-token"
        assert "operator-token" not in calls[0][1]["headers"].values()
        assert calls[0][1]["follow_redirects"] is False
        payload = calls[0][1]["json"]
        assert payload["event"] == "ai_process_optimierung.workflow.approved"
        assert payload["workflow"]["name"] == "Customer support routing"
        assert "description" not in payload
        assert "answers" not in payload

        with pytest.raises(ValueError, match="already been recorded"):
            service.run_live(completed["id"], confirmed=True, confirmation_token="operator-token")
        assert len(calls) == 1

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_live_webhook_rejects_insecure_or_internal_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_EXECUTION_ENABLED", True)
    monkeypatch.setattr(settings, "WORKFLOW_LIVE_EXECUTION_TOKEN", "operator-token")
    for endpoint in (
        "http://hooks.example.com/process",
        "https://localhost/process",
        "https://127.0.0.1/process",
    ):
        monkeypatch.setattr(settings, "WORKFLOW_WEBHOOK_URL", endpoint)
        readiness = ExecutionService.live_execution_readiness()
        assert readiness["ready"] is False
        assert readiness["status"] == "invalid_endpoint"


def test_pull_request_settings_always_disable_live_webhooks():
    preview = Settings(
        IS_PULL_REQUEST=True,
        OPENAI_API_KEY="production-key",
        PREVIEW_OPENAI_API_KEY="preview-key",
        WEBHOOK_EXECUTION_ENABLED=True,
        WORKFLOW_WEBHOOK_URL="https://hooks.example.com/production",
        WORKFLOW_WEBHOOK_BEARER_TOKEN="production-token",
        WORKFLOW_LIVE_EXECUTION_TOKEN="production-operator-token",
    )

    assert preview.OPENAI_API_KEY == "preview-key"
    assert preview.WEBHOOK_EXECUTION_ENABLED is False
    assert preview.WORKFLOW_WEBHOOK_URL == ""
    assert preview.WORKFLOW_WEBHOOK_BEARER_TOKEN == ""
    assert preview.WORKFLOW_LIVE_EXECUTION_TOKEN == ""



class FakeOptimizationAI:
    is_configured = True
    model = "optimization-test-model"

    def __init__(self):
        self.calls = 0
        self.last_call_telemetry = None
        self.received_answers = None

    def optimize_process(self, description, analysis, questions, answers, language="de"):
        self.calls += 1
        self.received_answers = answers
        self.last_call_telemetry = {
            "provider": "openai",
            "model": self.model,
            "task": "process_optimization",
            "status": "success",
            "inputTokens": 1200,
            "outputTokens": 600,
            "totalTokens": 1800,
            "durationMs": 900,
        }
        return {
            "process_specification": {
                "business_domain": "finance",
                "business_domain_label": "Finanzen",
                "process_goal": "Rechnungen schneller und fehlerfrei prüfen.",
                "actors": ["Finanzteam", "Manager"],
                "inputs": ["PDF-Rechnungen", "Bestellungen"],
                "systems": ["ERP"],
                "business_rules": ["Betragsabweichungen manuell prüfen."],
                "exception_paths": ["Fehlende Bestellnummer zur Klärung weiterleiten."],
                "outputs": ["Geprüfte Rechnung"],
                "success_metrics": ["Bearbeitungszeit"],
            },
            "optimization_summary": "Die bestätigten Angaben ermöglichen eine automatische Datenerfassung und einen regelbasierten Abgleich.",
            "design_principles": ["Standardfälle automatisch verarbeiten.", "Ausnahmen gezielt an Mitarbeitende geben."],
            "recommended_changes": [{
                "title": "Rechnungsdaten automatisch auslesen",
                "current_state": "Mitarbeitende übertragen Daten manuell.",
                "proposed_change": "PDF-Daten automatisch extrahieren und validieren.",
                "expected_effect": "Weniger manuelle Erfassung.",
                "priority": "high",
            }],
            "expected_benefits": [{
                "metric": "Bearbeitungszeit",
                "description": "Kürzere manuelle Bearbeitung.",
                "baseline_value": 20,
                "target_value": 10,
                "unit": "Minuten",
                "direction": "lower_is_better",
                "confidence": "medium",
                "basis": "Die Ausgangsdauer wurde vom Benutzer bestätigt; der Zielwert ist eine zu validierende Planungsannahme.",
            }],
            "automation_potential_score": 88,
            "automation_potential_reason": "Die wiederkehrenden Erfassungs- und Prüfhandlungen sind gut standardisierbar.",
            "automation_opportunities": [{
                "title": "Automatische Extraktion",
                "description": "Rechnungsdaten strukturiert auslesen.",
                "impact": "high",
            }],
            "integrations": [{"name": "ERP", "purpose": "Bestellabgleich und Statusübernahme."}],
            "human_approval_required": True,
            "human_approval_reason": "Abweichungen und zahlungsrelevante Entscheidungen benötigen eine Freigabe.",
            "workflow_name": "Optimierte Rechnungsprüfung",
            "workflow_trigger": "Neue Rechnung geht ein.",
            "workflow_steps": [
                {"type": "trigger", "name": "Rechnungseingang", "description": "Neue Rechnung erfassen.", "connector": "", "requires_approval": False},
                {"type": "extract", "name": "Daten auslesen", "description": "Rechnungsdaten aus dem PDF extrahieren.", "connector": "", "requires_approval": False},
                {"type": "validate", "name": "Bestellung abgleichen", "description": "Daten mit der Bestellung vergleichen.", "connector": "erp", "requires_approval": False},
                {"type": "approval", "name": "Ausnahme freigeben", "description": "Abweichungen durch einen Menschen prüfen lassen.", "connector": "", "requires_approval": False},
                {"type": "generate", "name": "Prüfergebnis erstellen", "description": "Prüfergebnis und Buchungsvorschlag vorbereiten.", "connector": "", "requires_approval": False},
            ],
            "risks": ["ERP-Stammdaten müssen aktuell sein."],
            "assumptions": ["Die ERP-Schnittstelle wird später eingerichtet."],
        }


def test_answers_trigger_a_second_llm_optimization_and_usage_is_recorded():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    ai_service = FakeOptimizationAI()

    analysis = {
        "llmUsed": True,
        "llmModel": "analysis-test-model",
        "questions": ["Which invoice system should be used?"],
        "proposedWorkflow": {
            "name": "Initial invoice workflow",
            "trigger": "A new invoice arrives.",
            "steps": [{
                "id": "step-1",
                "type": "trigger",
                "name": "Receive invoice",
                "description": "Receive an invoice.",
                "config": {"requiresApproval": False},
            }],
        },
    }

    with Session(engine) as db:
        service = WorkflowSessionService(db, ai_service=ai_service)
        created = service.create(
            description="Finance receives PDF invoices and checks them manually.",
            analysis=analysis,
            strategy="auto",
            language="de",
            business_domain="finance",
        )
        question = created["openQuestions"][0]
        partial = service.submit_answers(created["id"], {})
        assert partial["status"] == "needs_input"
        assert ai_service.calls == 0

        prepared = service.submit_answers(
            created["id"],
            {question["id"]: "SAP"},
        )

        assert prepared["status"] == "ready_for_approval"
        assert ai_service.calls == 1
        assert ai_service.received_answers == {question["id"]: "SAP"}
        assert prepared["analysis"]["optimization"]["status"] == "completed"
        assert prepared["analysis"]["optimization"]["engine"] == "llm"
        assert prepared["analysis"]["originalWorkflow"]["name"] == "Initial invoice workflow"
        assert prepared["analysis"]["proposedWorkflow"]["name"] == "Optimierte Rechnungsprüfung"
        assert prepared["analysis"]["optimization"]["expectedBenefits"][0]["changePercent"] == 50.0
        assert prepared["analysis"]["optimization"]["recommendedChanges"][0]["proposedChange"].startswith("PDF-Daten")
        assert prepared["analysis"]["proposedWorkflow"]["executionPolicy"]["externalActionsEnabled"] is False

        usage = db.query(AIUsageEvent).filter_by(session_id=created["id"]).all()
        assert any(item.task == "process_optimization" and item.total_tokens == 1800 for item in usage)
        assert any(event["event"] == "ai_optimization_completed" for event in prepared["events"])

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_rules_strategy_keeps_the_python_path_without_a_second_llm_call():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    ai_service = FakeOptimizationAI()
    analysis = {
        "llmUsed": False,
        "questions": ["Which folder should be used?"],
        "proposedWorkflow": {
            "name": "Rules workflow",
            "trigger": "Manual",
            "steps": [{
                "id": "step-1",
                "type": "trigger",
                "name": "Start",
                "description": "Manual start.",
                "config": {"requiresApproval": False},
            }],
        },
    }

    with Session(engine) as db:
        service = WorkflowSessionService(db, ai_service=ai_service)
        created = service.create(
            description="Collect requests and prepare a report.",
            analysis=analysis,
            strategy="rules",
            language="de",
            business_domain="operations",
        )
        question = created["openQuestions"][0]
        prepared = service.submit_answers(created["id"], {question["id"]: "Finance"})

        assert prepared["status"] == "ready_for_approval"
        assert ai_service.calls == 0
        assert prepared["analysis"]["optimization"]["status"] == "rules_only"
        assert prepared["analysis"]["proposedWorkflow"]["name"] == "Rules workflow"

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
