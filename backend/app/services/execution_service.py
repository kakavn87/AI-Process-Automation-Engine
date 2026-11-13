from datetime import datetime, timezone
from uuid import uuid4
from urllib.parse import urlparse

import httpx
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.orm import Session

from app.core.config import settings
from app.engine.execution.executor import WorkflowExecutor
from app.engine.workflow.validator import validate
from app.models.execution import ApprovalExecution
from app.models.workflow_session import WorkflowSession


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
            *(execution.events or []),
            {
                "event": "approval_granted",
                "status": "approved",
                "message": note or "Approved by a human reviewer.",
            },
            *result["events"],
        ]
        execution.updated_at = datetime.now(timezone.utc)
        self._sync_workflow_session(
            execution.id,
            "completed",
            "Human approval was recorded and the workflow simulation completed.",
        )
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
            *(execution.events or []),
            {
                "event": "approval_rejected",
                "status": "rejected",
                "message": (
                    f"Rejected: {note}. No workflow steps were executed."
                    if note
                    else "Rejected by a human reviewer. No workflow steps were executed."
                ),
            },
        ]
        execution.updated_at = datetime.now(timezone.utc)
        self._sync_workflow_session(
            execution.id,
            "rejected",
            note or "The reviewer rejected the workflow. No workflow steps were executed.",
        )
        self.db.commit()
        self.db.refresh(execution)
        return self._serialize(execution)

    @staticmethod
    def live_execution_readiness() -> dict:
        endpoint = settings.WORKFLOW_WEBHOOK_URL.strip()
        enabled = settings.WEBHOOK_EXECUTION_ENABLED
        status = "disabled"
        message = "Live execution is disabled. The workflow remains in simulation mode."

        if enabled and not endpoint:
            status = "missing_endpoint"
            message = "Add WORKFLOW_WEBHOOK_URL to configure the approved webhook endpoint."
        elif enabled:
            try:
                ExecutionService._validate_webhook_url(endpoint)
                status = "ready"
                message = "A secure HTTPS webhook is configured and live execution is enabled."
            except ValueError as error:
                status = "invalid_endpoint"
                message = str(error)

        return {
            "provider": "Webhook",
            "enabled": enabled,
            "ready": status == "ready",
            "endpointConfigured": bool(endpoint),
            "status": status,
            "message": message,
            "secretConfigured": bool(settings.WORKFLOW_WEBHOOK_BEARER_TOKEN.strip()),
        }

    @staticmethod
    def _validate_webhook_url(endpoint: str) -> str:
        parsed = urlparse(endpoint)
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme != "https"
            or not host
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError("The webhook endpoint must be an HTTPS URL without embedded credentials or fragments.")
        if host in {"localhost"} or host.endswith((".localhost", ".local", ".internal")):
            raise ValueError("Local and internal webhook hosts are not allowed.")
        if ":" in host:
            raise ValueError("Use a public DNS hostname for the webhook endpoint, not an IP address.")
        return endpoint

    def run_live(self, execution_id: str, confirmed: bool) -> dict:
        if confirmed is not True:
            raise ValueError("Explicit confirmation is required before sending data to the configured webhook.")

        execution = self.db.get(ApprovalExecution, execution_id)
        if execution is None:
            raise KeyError("Execution was not found.")
        if execution.status != "completed":
            raise ValueError("A workflow must be approved and simulation-completed before live dispatch.")

        events = list(execution.events or [])
        previous_attempt = next(
            (
                event for event in events
                if event.get("event") in {
                    "live_execution_started",
                    "live_execution_succeeded",
                    "live_execution_failed",
                    "live_execution_unknown",
                }
            ),
            None,
        )
        if previous_attempt:
            raise ValueError(
                "A live webhook attempt has already been recorded. Check the receiving system before taking any further action."
            )

        readiness = self.live_execution_readiness()
        if not readiness["ready"]:
            raise ValueError(readiness["message"])

        endpoint = self._validate_webhook_url(settings.WORKFLOW_WEBHOOK_URL.strip())
        workflow = execution.workflow_definition or {}
        payload = {
            "event": "ai_process_optimierung.workflow.approved",
            "execution": {
                "id": execution.id,
                "workflowName": execution.workflow_name,
                "approvedAt": execution.updated_at.isoformat() if execution.updated_at else None,
            },
            "workflow": {
                "name": workflow.get("name"),
                "trigger": workflow.get("trigger"),
                "steps": [
                    {
                        "id": step.get("id"),
                        "type": step.get("type"),
                        "name": step.get("name"),
                        "description": step.get("description"),
                        "connector": (step.get("config") or {}).get("connector"),
                        "requiresApproval": (step.get("config") or {}).get("requiresApproval", False),
                    }
                    for step in workflow.get("steps", [])
                ],
            },
        }

        timestamp = datetime.now(timezone.utc).isoformat()
        execution.events = [
            *events,
            {
                "event": "live_execution_started",
                "status": "running",
                "message": "A one-time dispatch to the configured HTTPS webhook was started.",
                "recordedAt": timestamp,
            },
        ]
        execution.updated_at = datetime.now(timezone.utc)
        # Persist the attempt before the network call so a refresh or timeout cannot
        # accidentally cause a duplicate external dispatch.
        self.db.commit()

        headers = {"Content-Type": "application/json"}
        token = settings.WORKFLOW_WEBHOOK_BEARER_TOKEN.strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            response = httpx.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=settings.WORKFLOW_WEBHOOK_TIMEOUT_SECONDS,
                follow_redirects=False,
            )
        except httpx.RequestError as error:
            final_status = "unknown"
            event_name = "live_execution_unknown"
            message = (
                "The webhook request ended without a confirmed response. The receiver may have processed it; "
                "check the receiving system before any manual retry."
            )
            http_status = None
            error_type = type(error).__name__
        else:
            http_status = response.status_code
            if 200 <= response.status_code < 300:
                final_status = "succeeded"
                event_name = "live_execution_succeeded"
                message = f"The configured webhook confirmed receipt with HTTP {response.status_code}."
                error_type = None
            else:
                final_status = "failed"
                event_name = "live_execution_failed"
                message = (
                    f"The webhook returned HTTP {response.status_code}. Check the receiver's logs before any manual retry."
                )
                error_type = "WebhookHTTPError"

        execution.events = [
            *(execution.events or []),
            {
                "event": event_name,
                "status": final_status,
                "message": message,
                "httpStatus": http_status,
                "errorType": error_type,
                "externalSideEffect": final_status == "succeeded",
                "recordedAt": datetime.now(timezone.utc).isoformat(),
            },
        ]
        execution.updated_at = datetime.now(timezone.utc)
        self._sync_live_workflow_session(execution.id, final_status, message)
        self.db.commit()
        self.db.refresh(execution)
        return self._serialize(execution)

    def _sync_workflow_session(self, execution_id: str, status: str, message: str) -> None:
        # Older tests and pre-upgrade databases may not have the new session table yet.
        # Main application startup creates it; skip the optional sync if it is absent.
        if not sqlalchemy_inspect(self.db.get_bind()).has_table(WorkflowSession.__tablename__):
            return

        session = (
            self.db.query(WorkflowSession)
            .filter(WorkflowSession.related_execution_id == execution_id)
            .one_or_none()
        )
        if session is None:
            return
        session.status = status
        session.events = [
            *(session.events or []),
            {
                "event": "execution_" + status,
                "status": status,
                "message": message,
                "executionId": execution_id,
                "recordedAt": datetime.now(timezone.utc).isoformat(),
            },
        ]
        session.updated_at = datetime.now(timezone.utc)

    def _sync_live_workflow_session(self, execution_id: str, status: str, message: str) -> None:
        if not sqlalchemy_inspect(self.db.get_bind()).has_table(WorkflowSession.__tablename__):
            return
        session = (
            self.db.query(WorkflowSession)
            .filter(WorkflowSession.related_execution_id == execution_id)
            .one_or_none()
        )
        if session is None:
            return
        session.events = [
            *(session.events or []),
            {
                "event": "live_execution_" + status,
                "status": status,
                "message": message,
                "executionId": execution_id,
                "recordedAt": datetime.now(timezone.utc).isoformat(),
            },
        ]
        session.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _serialize(execution: ApprovalExecution) -> dict:
        events = execution.events or []
        live_events = [
            event for event in events
            if event.get("event") in {
                "live_execution_started",
                "live_execution_succeeded",
                "live_execution_failed",
                "live_execution_unknown",
            }
        ]
        live_status = live_events[-1]["status"] if live_events else "not_started"
        return {
            "id": execution.id,
            "workflowName": execution.workflow_name,
            "status": execution.status,
            "decisionNote": execution.decision_note,
            "createdAt": execution.created_at.isoformat() if execution.created_at else None,
            "updatedAt": execution.updated_at.isoformat() if execution.updated_at else None,
            "executionMode": "live_webhook" if live_status == "succeeded" else "simulation",
            "liveExecutionStatus": live_status,
            "events": events,
        }
