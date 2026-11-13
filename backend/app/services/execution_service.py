from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.workflow.validator import validate
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep


OUTBOUND_TYPES = {"notify", "email", "teams"}


class ExecutionService:
    """Persist a reviewable workflow run; do not invoke external connectors yet."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, workflow: dict) -> dict:
        workflow = self._ensure_approval_gate(workflow)
        validate(workflow)
        steps = workflow.get("steps", [])
        if not steps:
            raise ValueError("The workflow must contain at least one step.")

        approval_index = next(i for i, step in enumerate(steps) if step.get("type") == "approval")
        execution = Execution(
            workflow_name=workflow.get("name", "Workflow execution"),
            status="awaiting_approval",
            workflow_data=workflow,
        )
        for index, step in enumerate(steps):
            if index < approval_index:
                step_status = "pending"
            elif index == approval_index:
                step_status = "awaiting_approval"
            else:
                step_status = "blocked"
            execution.steps.append(ExecutionStep(
                step_key=step.get("id", f"step-{index + 1}"),
                step_type=step["type"],
                name=step.get("name", step["type"]),
                description=step.get("description", ""),
                status=step_status,
                position=index,
                config=step.get("config", {}),
            ))

        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return self._serialize(execution)

    def list(self) -> list[dict]:
        executions = self.db.scalars(
            select(Execution).order_by(Execution.created_at.desc(), Execution.id.desc())
        ).all()
        return [self._serialize(item) for item in executions]

    def get(self, execution_id: int) -> dict | None:
        execution = self.db.get(Execution, execution_id)
        return self._serialize(execution) if execution else None

    def approve(self, execution_id: int, note: str = "") -> dict:
        execution = self._require_pending(execution_id)
        execution.status = "approved_ready"
        execution.decision_note = note
        execution.decided_at = datetime.now(timezone.utc)
        for step in execution.steps:
            if step.step_type == "approval":
                step.status = "approved"
            elif step.status == "blocked":
                step.status = "pending"
        self.db.commit()
        self.db.refresh(execution)
        return self._serialize(execution)

    def reject(self, execution_id: int, reason: str = "") -> dict:
        execution = self._require_pending(execution_id)
        execution.status = "rejected"
        execution.decision_note = reason
        execution.decided_at = datetime.now(timezone.utc)
        for step in execution.steps:
            step.status = "rejected" if step.step_type == "approval" else "cancelled"
        self.db.commit()
        self.db.refresh(execution)
        return self._serialize(execution)

    def _require_pending(self, execution_id: int) -> Execution:
        execution = self.db.get(Execution, execution_id)
        if execution is None:
            raise LookupError("Execution not found.")
        if execution.status != "awaiting_approval":
            raise RuntimeError(f"Execution is already {execution.status}.")
        return execution

    @staticmethod
    def _ensure_approval_gate(workflow: dict) -> dict:
        definition = {
            **workflow,
            "steps": [dict(step, config=dict(step.get("config") or {})) for step in workflow.get("steps", [])],
        }
        approval_index = next((i for i, step in enumerate(definition["steps"]) if step.get("type") == "approval"), -1)
        first_outbound = next((i for i, step in enumerate(definition["steps"]) if step.get("type") in OUTBOUND_TYPES), len(definition["steps"]))

        if approval_index < 0:
            approval = {
                "id": "approval-gate",
                "type": "approval",
                "name": "Human approval",
                "description": "Review and approve this workflow before any execution begins.",
                "config": {"requiresApproval": False},
            }
            definition["steps"].insert(first_outbound, approval)
        elif approval_index > first_outbound:
            approval = definition["steps"].pop(approval_index)
            definition["steps"].insert(first_outbound, approval)

        for step in definition["steps"]:
            if step.get("type") in OUTBOUND_TYPES:
                step.setdefault("config", {})["requiresApproval"] = True
        for index, step in enumerate(definition["steps"], start=1):
            step["id"] = f"step-{index}"
        return definition

    @staticmethod
    def _serialize(execution: Execution) -> dict:
        return {
            "id": execution.id,
            "workflowName": execution.workflow_name,
            "status": execution.status,
            "workflow": execution.workflow_data,
            "decisionNote": execution.decision_note or "",
            "createdAt": execution.created_at.isoformat() if execution.created_at else None,
            "decidedAt": execution.decided_at.isoformat() if execution.decided_at else None,
            "steps": [
                {
                    "id": step.step_key,
                    "type": step.step_type,
                    "name": step.name,
                    "description": step.description,
                    "status": step.status,
                    "position": step.position,
                }
                for step in execution.steps
            ],
            "executionNote": (
                "Approval is recorded. Workflow actions have not been executed in this release; "
                "connectors must be configured and tested before external side effects are enabled."
                if execution.status == "approved_ready"
                else "No workflow actions have been executed."
            ),
        }
