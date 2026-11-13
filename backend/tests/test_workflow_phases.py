from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.engine.execution.action_executor import ActionExecutor
from app.engine.workflow.automation_engine import WorkflowAutomationEngine
from app.models.workflow_session import AIUsageEvent, WorkflowSession
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
