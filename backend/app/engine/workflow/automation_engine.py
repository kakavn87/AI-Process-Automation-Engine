from datetime import datetime, timezone
from typing import Any

from app.engine.workflow.validator import validate


class WorkflowAutomationEngine:
    """Runs deterministic preparation and validation without making external calls."""

    def prepare(self, analysis: dict, answers: dict[str, Any]) -> dict:
        updated = dict(analysis)
        workflow = dict(updated.get("proposedWorkflow") or {})
        validate(workflow)

        confirmed_details = updated.get("userConfirmedDetails") or []
        confirmed_details = list(confirmed_details)
        confirmed_details.extend(
            {"questionId": question_id, "answer": answer}
            for question_id, answer in answers.items()
        )

        specification = dict(updated.get("processSpecification") or {})
        specification["confirmedDetails"] = confirmed_details
        updated["processSpecification"] = specification
        updated["userConfirmedDetails"] = confirmed_details
        updated["openQuestions"] = []
        updated["processingResult"] = {
            "engine": "deterministic_python",
            "status": "prepared",
            "preparedAt": datetime.now(timezone.utc).isoformat(),
            "externalActionsExecuted": False,
        }

        workflow["confirmedContext"] = confirmed_details
        workflow["executionPolicy"] = {
            "mode": "simulation",
            "externalActionsRequireApproval": True,
            "externalActionsEnabled": False,
        }
        updated["proposedWorkflow"] = workflow
        return updated
