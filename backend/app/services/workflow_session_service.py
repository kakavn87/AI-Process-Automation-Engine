import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.engine.workflow.automation_engine import WorkflowAutomationEngine
from app.models.workflow_session import WorkflowSession
from app.services.question_service import QuestionService
from app.services.ai_service import AIService
from app.services.ai_usage_service import AIUsageService

logger = logging.getLogger(__name__)


class WorkflowSessionService:
    def __init__(self, db: Session, tenant_id: str | None = None, ai_service: AIService | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.ai_service = ai_service or AIService()
        self.question_service = QuestionService()
        self.automation_engine = WorkflowAutomationEngine()

    def _get_session(self, session_id: str):
        query = self.db.query(WorkflowSession).filter(WorkflowSession.id == session_id)
        if self.tenant_id is not None:
            query = query.filter(WorkflowSession.tenant_id == self.tenant_id)
        return query.one_or_none()

    def create(
        self,
        description: str,
        analysis: dict,
        strategy: str = "auto",
        language: str = "de",
        business_domain: str = "general",
        session_id: str | None = None,
    ) -> dict:
        questions = self.question_service.build(analysis.get("questions") or [])
        initial_status = "needs_input" if questions else "processing"
        session = WorkflowSession(
            id=session_id or str(uuid4()),
            tenant_id=self.tenant_id,
            description=description,
            analysis_strategy=strategy,
            language=language,
            business_domain=business_domain,
            analysis=analysis,
            questions=questions,
            answers={},
            status=initial_status,
            events=[{
                "event": "analysis_completed",
                "status": "success",
                "message": "Analysis persisted. The workflow is waiting for missing information."
                if questions
                else "Analysis persisted. No clarification questions are required.",
                "recordedAt": datetime.now(timezone.utc).isoformat(),
            }],
        )
        self.db.add(session)
        self.db.flush()

        if not questions:
            self._prepare(session)

        self.db.commit()
        self.db.refresh(session)
        return self.serialize(session)

    def get(self, session_id: str) -> dict | None:
        session = self._get_session(session_id)
        return self.serialize(session) if session else None

    def submit_answers(self, session_id: str, answers: dict) -> dict:
        session = self._get_session(session_id)
        if session is None:
            raise KeyError("Workflow session was not found.")
        if session.status != "needs_input":
            raise ValueError(f"Cannot submit answers while session status is '{session.status}'.")

        question_map = {item["id"]: item for item in (session.questions or [])}
        unknown = set(answers) - set(question_map)
        if unknown:
            raise ValueError(f"Unknown question id(s): {', '.join(sorted(unknown))}")

        stored_answers = dict(session.answers or {})
        for question_id, value in answers.items():
            stored_answers[question_id] = self.question_service.validate_answer(
                question_map[question_id], value
            )

        session.answers = stored_answers
        unanswered = [
            question for question in (session.questions or [])
            if question.get("required", True) and question["id"] not in stored_answers
        ]

        if unanswered:
            session.events = [
                *(session.events or []),
                {
                    "event": "answers_saved",
                    "status": "needs_input",
                    "message": f"Saved {len(answers)} answer(s); {len(unanswered)} required question(s) remain.",
                    "recordedAt": datetime.now(timezone.utc).isoformat(),
                },
            ]
        else:
            session.status = "processing"
            self.db.flush()
            self._prepare(session)

        session.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(session)
        return self.serialize(session)

    def create_execution(self, session_id: str) -> dict:
        session = self._get_session(session_id)
        if session is None:
            raise KeyError("Workflow session was not found.")
        if session.status != "ready_for_approval":
            raise ValueError("The workflow must finish preparation before an approval request can be created.")
        if session.related_execution_id:
            raise ValueError("An execution request already exists for this workflow session.")

        from app.services.execution_service import ExecutionService

        workflow = (session.analysis or {}).get("proposedWorkflow") or {}
        execution = ExecutionService(self.db, tenant_id=self.tenant_id).create(workflow)
        session.related_execution_id = execution["id"]
        session.status = "awaiting_approval"
        session.events = [
            *(session.events or []),
            {
                "event": "approval_requested",
                "status": "awaiting_approval",
                "message": "Workflow is paused until an authorized reviewer approves or rejects it.",
                "executionId": execution["id"],
                "recordedAt": datetime.now(timezone.utc).isoformat(),
            },
        ]
        session.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(session)
        return {"session": self.serialize(session), "execution": execution}

    def retry_optimization(self, session_id: str) -> dict:
        session = self._get_session(session_id)
        if session is None:
            raise KeyError("Workflow session was not found.")
        if session.status != "failed":
            raise ValueError("Only a failed optimization can be retried.")

        unanswered = [
            question for question in (session.questions or [])
            if question.get("required", True) and question["id"] not in (session.answers or {})
        ]
        if unanswered:
            raise ValueError("Complete all required clarification questions before retrying optimization.")

        session.status = "processing"
        session.events = [
            *(session.events or []),
            {
                "event": "optimization_retry_requested",
                "status": "processing",
                "message": "Die Optimierung wird erneut mit dem KI-Modell gestartet."
                if session.language == "de"
                else "The optimization is being retried with the AI model.",
                "recordedAt": datetime.now(timezone.utc).isoformat(),
            },
        ]
        self.db.flush()
        self._prepare(session)
        session.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(session)
        return self.serialize(session)

    def _record_optimization_usage(self, session: WorkflowSession) -> None:
        telemetry = getattr(self.ai_service, "last_call_telemetry", None)
        if not telemetry:
            return
        try:
            AIUsageService(self.db, tenant_id=self.tenant_id).record(
                session.id,
                telemetry,
                commit=False,
            )
        except Exception:
            logger.exception("Could not persist process-optimization usage telemetry.")

    def _prepare(self, session: WorkflowSession) -> None:
        usage_recorded = False
        try:
            optimization = self.ai_service.optimize_process(
                analysis=session.analysis or {},
                answers=session.answers or {},
                questions=session.questions or [],
                language=session.language,
            )
            telemetry = getattr(self.ai_service, "last_call_telemetry", None)
            prepared = self.automation_engine.prepare(
                session.analysis or {},
                session.answers or {},
                optimization=optimization,
            )
            if telemetry:
                prepared["processOptimization"]["model"] = telemetry.get("model")
                prepared["processOptimization"]["provider"] = telemetry.get("provider")
            self._record_optimization_usage(session)
            usage_recorded = True
            session.analysis = prepared
            session.status = "ready_for_approval"
            session.events = [
                *(session.events or []),
                {
                    "event": "llm_optimization_completed",
                    "status": "success",
                    "message": "Das KI-Modell hat Ihre Antworten ausgewertet und einen optimierten Prozess erstellt. Python hat Workflow-Regeln und Kennzahlen validiert."
                    if session.language == "de"
                    else "The AI model used your answers to design an optimized process. Python validated workflow rules and calculated the metric deltas.",
                    "recordedAt": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "event": "workflow_prepared",
                    "status": "ready_for_approval",
                    "message": "Der optimierte Workflow ist bereit zur menschlichen Prüfung. Externe Aktionen bleiben bis zu einer gesonderten Freigabe deaktiviert."
                    if session.language == "de"
                    else "The optimized workflow is ready for human review. External actions remain disabled until separately authorized.",
                    "recordedAt": datetime.now(timezone.utc).isoformat(),
                },
            ]
        except Exception as error:
            if not usage_recorded:
                self._record_optimization_usage(session)
            logger.exception("Second-pass LLM process optimization failed.")
            detail = (
                "Die KI-Optimierung ist fehlgeschlagen. Prüfen Sie API-Guthaben, Modellzugriff und Backend-Protokolle. Sie können den Schritt erneut versuchen."
                if session.language == "de"
                else "The AI optimization failed. Check API credits, model access and backend logs. You can retry this step."
            )
            updated_analysis = dict(session.analysis or {})
            updated_analysis["optimizationFailure"] = {
                "message": detail,
                "errorType": type(error).__name__,
            }
            updated_analysis["processingResult"] = {
                "engine": "openai_llm_and_deterministic_python",
                "status": "failed",
                "preparedAt": datetime.now(timezone.utc).isoformat(),
                "externalActionsExecuted": False,
            }
            session.analysis = updated_analysis
            session.status = "failed"
            session.events = [
                *(session.events or []),
                {
                    "event": "llm_optimization_failed",
                    "status": "failed",
                    "message": detail,
                    "recordedAt": datetime.now(timezone.utc).isoformat(),
                },
            ]

    @staticmethod
    def serialize(session: WorkflowSession) -> dict:
        answers = session.answers or {}
        all_questions = session.questions or []
        return {
            "id": session.id,
            "description": session.description,
            "analysisStrategy": session.analysis_strategy,
            "language": session.language,
            "businessDomain": session.business_domain,
            "status": session.status,
            "analysis": session.analysis or {},
            "answers": answers,
            "questions": [
                {**question, "answered": question["id"] in answers}
                for question in all_questions
            ],
            "openQuestions": [
                question for question in all_questions
                if question["id"] not in answers and question.get("required", True)
            ],
            "relatedExecutionId": session.related_execution_id,
            "events": session.events or [],
            "createdAt": session.created_at.isoformat() if session.created_at else None,
            "updatedAt": session.updated_at.isoformat() if session.updated_at else None,
        }
