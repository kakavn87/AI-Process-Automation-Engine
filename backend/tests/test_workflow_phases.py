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




class FakeOptimizationAIService:
    model = "test-optimizer"

    def __init__(self, fail_first: bool = False):
        self.calls = []
        self.last_call_telemetry = None
        self.fail_first = fail_first

    def optimize_process(self, analysis, answers, questions, language):
        self.calls.append({
            "analysis": analysis,
            "answers": answers,
            "questions": questions,
            "language": language,
        })
        if self.fail_first and len(self.calls) == 1:
            self.last_call_telemetry = {
                "provider": "openai",
                "model": self.model,
                "task": "process_optimization",
                "status": "fallback",
                "inputTokens": 20,
                "outputTokens": 0,
                "totalTokens": 20,
                "durationMs": 10,
                "errorType": "RuntimeError",
            }
            raise RuntimeError("temporary model error")

        self.last_call_telemetry = {
            "provider": "openai",
            "model": self.model,
            "task": "process_optimization",
            "status": "success",
            "inputTokens": 100,
            "outputTokens": 200,
            "totalTokens": 300,
            "durationMs": 25,
        }
        return {
            "summary": "Automate document intake and validation, then route only exceptions for review.",
            "optimized_process": [
                "Collect source documents automatically.",
                "Extract and normalize the relevant fields.",
                "Validate required data and route exceptions.",
                "Generate the reviewed output.",
                "Obtain human approval before distribution.",
            ],
            "changes": [
                {
                    "current_step": "Employees manually download and copy document data.",
                    "optimized_step": "Documents are collected and extracted automatically.",
                    "reason": "Avoid duplicate manual data entry.",
                    "expected_benefit": "Less handling time and fewer transcription errors.",
                }
            ],
            "opportunities": [
                {
                    "title": "Automated document intake",
                    "description": "Extract standard fields from uploaded documents.",
                    "priority": "high",
                    "implementation_effort": "medium",
                    "expected_benefit": "Reduce repetitive manual work.",
                }
            ],
            "automation_potential_score": 84,
            "optimized_workflow_name": "Optimized maintenance reporting",
            "optimized_workflow_trigger": "Start when a new report arrives.",
            "optimized_workflow_steps": [
                {
                    "type": "trigger",
                    "name": "New report received",
                    "description": "Start when a new report arrives.",
                    "connector": "",
                    "requires_approval": False,
                },
                {
                    "type": "extract",
                    "name": "Extract report data",
                    "description": "Extract structured data from the source document.",
                    "connector": "document_parser",
                    "requires_approval": False,
                },
                {
                    "type": "validate",
                    "name": "Validate extracted data",
                    "description": "Check required fields and exceptions.",
                    "connector": "",
                    "requires_approval": False,
                },
                {
                    "type": "generate",
                    "name": "Prepare report",
                    "description": "Generate the report from validated data.",
                    "connector": "",
                    "requires_approval": False,
                },
                {
                    "type": "email",
                    "name": "Send report",
                    "description": "Send the approved report.",
                    "connector": "microsoft_outlook",
                    "requires_approval": False,
                },
            ],
            "metrics": [
                {
                    "name": "Bearbeitungszeit pro Bericht",
                    "current_value": 12,
                    "proposed_value": 4,
                    "unit": "Minuten",
                    "direction": "lower_is_better",
                    "rationale": "The target is an explicit model estimate based on automatic intake.",
                    "current_value_source": "user_input",
                    "proposed_value_source": "model_estimate",
                    "confidence": "medium",
                }
            ],
            "remaining_questions": [],
            "risks": ["Unleserliche Dokumente müssen manuell geprüft werden."],
            "assumptions": ["Die Quelldokumente besitzen eine ausreichend einheitliche Struktur."],
            "implementation_notes": ["Document parser and source connector need configuration."],
        }


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
        ai_service = FakeOptimizationAIService()
        service = WorkflowSessionService(db, ai_service=ai_service)
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
        assert prepared["analysis"]["processingResult"]["engine"] == "openai_llm_and_deterministic_python"
        assert prepared["analysis"]["processingResult"]["externalActionsExecuted"] is False
        assert len(prepared["analysis"]["proposedWorkflow"]["confirmedContext"]) == 2
        assert prepared["answers"][second_question["id"]] is False
        assert len(ai_service.calls) == 1
        assert ai_service.calls[0]["answers"] == prepared["answers"]
        assert prepared["analysis"]["currentWorkflow"]["name"] == "Maintenance review"
        assert prepared["analysis"]["proposedWorkflow"]["name"] == "Optimized maintenance reporting"
        assert prepared["analysis"]["processOptimization"]["llmUsed"] is True
        metric = prepared["analysis"]["processOptimization"]["metrics"][0]
        assert metric["absoluteChange"] == -8
        assert metric["improvementPercent"] == 66.67
        assert metric["isEstimate"] is True
        workflow_types = [step["type"] for step in prepared["analysis"]["proposedWorkflow"]["steps"]]
        assert workflow_types.index("approval") < workflow_types.index("email")
        assert prepared["analysis"]["proposedWorkflow"]["steps"][workflow_types.index("email")]["config"]["requiresApproval"] is True
        usage_events = db.query(AIUsageEvent).filter(AIUsageEvent.task == "process_optimization").all()
        assert len(usage_events) == 1
        assert usage_events[0].total_tokens == 300

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


def test_failed_second_pass_llm_optimization_can_be_retried():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    ai_service = FakeOptimizationAIService(fail_first=True)
    analysis = {
        "questions": ["Which mailbox should receive the report?"],
        "proposedWorkflow": {
            "name": "Current workflow",
            "trigger": "Manual",
            "steps": [
                {
                    "id": "step-1",
                    "type": "trigger",
                    "name": "Start",
                    "description": "Start manually",
                    "config": {"requiresApproval": False},
                }
            ],
        },
    }

    with Session(engine) as db:
        service = WorkflowSessionService(db, ai_service=ai_service)
        created = service.create(
            description="Prepare and distribute a maintenance report.",
            analysis=analysis,
            language="de",
        )
        question = created["openQuestions"][0]
        failed = service.submit_answers(created["id"], {question["id"]: "technik@example.de"})

        assert failed["status"] == "failed"
        assert failed["analysis"]["optimizationFailure"]["errorType"] == "RuntimeError"
        assert len(ai_service.calls) == 1

        retried = service.retry_optimization(created["id"])
        assert retried["status"] == "ready_for_approval"
        assert len(ai_service.calls) == 2
        assert retried["analysis"]["processOptimization"]["llmUsed"] is True
        assert db.query(AIUsageEvent).filter(AIUsageEvent.task == "process_optimization").count() == 2

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_optimization_metrics_are_calculated_by_python_only():
    result = WorkflowAutomationEngine._calculate_metrics([
        {
            "name": "Cycle time",
            "current_value": 10,
            "proposed_value": 5,
            "unit": "minutes",
            "direction": "lower_is_better",
            "rationale": "Estimated from the proposed automation.",
            "current_value_source": "user_input",
            "proposed_value_source": "model_estimate",
            "confidence": "low",
        },
        {
            "name": "Accuracy",
            "current_value": None,
            "proposed_value": None,
            "unit": "%",
            "direction": "higher_is_better",
            "rationale": "No baseline was provided.",
            "current_value_source": "not_available",
            "proposed_value_source": "not_available",
            "confidence": "low",
        },
    ])

    assert result[0]["improvementPercent"] == 50
    assert result[0]["isEstimate"] is True
    assert result[1]["improvementPercent"] is None
    assert result[1]["absoluteChange"] is None

