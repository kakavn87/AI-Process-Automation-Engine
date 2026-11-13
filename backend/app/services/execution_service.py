from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.engine.execution.executor import WorkflowExecutor
from app.engine.workflow.validator import validate
from app.models.execution import ApprovalExecution


class ExecutionService:
    def __init__(self, db: Session):
        self.db = db
        self.executor = WorkflowExecutor()

    def create(self, workflow: dict) -> dict:
        validate(workflow)
        execution = ApprovalExecution(
            id=str(uuid4()),
            workflow_name=workflow.get("name", "Untitled workflow"),
            workflow_definition=workflow,
            status="awaiting_approval",
            events=[{
                "event": "execution_created",
                "status": "awaiting_approval",
                "message": "Execution is paused. Review the workflow and approve it before running.",
            }],
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return self._serialize(execution)

    def get(self, execution_id: str) -> dict | None:
        execution = self.db.get(ApprovalExecution, execution_id)
        return self._serialize(execution) if execution else None

    def list(self, limit: int = 20) -> list[dict]:
        items = (
            self.db.query(ApprovalExecution)
            .order_by(ApprovalExecution.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._serialize(item) for item in items]

    def approve(self, execution_id: str, note: str | None = None) -> dict:
        execution = self.db.get(ApprovalExecution, execution_id)
        if execution is None:
            raise KeyError("Execution was not found.")
        if execution.status != "awaiting_approval":
            raise ValueError(f"Cannot approve an execution with status '{execution.status}'.")

        result = self.executor.execute(execution.workflow_definition, approved=True)
        execution.status = result["status"]
        execution.decision_note = note
        execution.events = [
            *execution.events,
            {
                "event": "approval_granted",
                "status": "approved",
                "message": note or "Approved by a human reviewer.",
            },
            *result["events"],
        ]
        execution.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(execution)
        return self._serialize(execution)

    def reject(self, execution_id: str, note: str | None = None) -> dict:
        execution = self.db.get(ApprovalExecution, execution_id)
        if execution is None:
            raise KeyError("Execution was not found.")
        if execution.status != "awaiting_approval":
            raise ValueError(f"Cannot reject an execution with status '{execution.status}'.")

        execution.status = "rejected"
        execution.decision_note = note
        execution.events = [
            *execution.events,
            {
                "event": "approval_rejected",
                "status": "rejected",
                "message": note or "Rejected by a human reviewer. No workflow steps were executed.",
            },
        ]
        execution.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(execution)
        return self._serialize(execution)

    @staticmethod
    def _serialize(execution: ApprovalExecution) -> dict:
        return {
            "id": execution.id,
            "workflowName": execution.workflow_name,
            "status": execution.status,
            "decisionNote": execution.decision_note,
            "createdAt": execution.created_at.isoformat() if execution.created_at else None,
            "updatedAt": execution.updated_at.isoformat() if execution.updated_at else None,
            "executionMode": "simulation",
            "events": execution.events or [],
        }
