import math
from datetime import datetime, timezone
from typing import Any

from app.engine.workflow.validator import validate


OUTBOUND_TYPES = {"notify", "email", "teams", "http"}


class WorkflowAutomationEngine:
    """Applies confirmed user input and validates an LLM-designed target process."""

    def prepare(
        self,
        analysis: dict,
        answers: dict[str, Any],
        optimization: dict | None = None,
    ) -> dict:
        updated = dict(analysis)
        current_workflow = dict(updated.get("proposedWorkflow") or {})

        confirmed_details = list(updated.get("userConfirmedDetails") or [])
        confirmed_details.extend(
            {"questionId": question_id, "answer": answer}
            for question_id, answer in answers.items()
        )

        specification = dict(updated.get("processSpecification") or {})
        specification["confirmedDetails"] = confirmed_details
        updated["processSpecification"] = specification
        updated["userConfirmedDetails"] = confirmed_details
        updated["openQuestions"] = []

        if optimization is not None:
            workflow = self._build_optimized_workflow(optimization)
            validate(workflow)
            metrics = self._calculate_metrics(optimization.get("metrics") or [])
            updated["currentWorkflow"] = current_workflow
            updated["currentProcess"] = updated.get("currentProcess") or []
            updated["optimizedProcess"] = optimization.get("optimized_process") or []
            updated["processOptimization"] = {
                "status": "completed",
                "llmUsed": True,
                "summary": optimization.get("summary", ""),
                "changes": optimization.get("changes") or [],
                "opportunities": optimization.get("opportunities") or [],
                "automationPotentialScore": optimization.get("automation_potential_score"),
                "metrics": metrics,
                "remainingQuestions": optimization.get("remaining_questions") or [],
                "risks": optimization.get("risks") or [],
                "assumptions": optimization.get("assumptions") or [],
                "implementationNotes": optimization.get("implementation_notes") or [],
            }
            updated["automationScore"] = optimization.get("automation_potential_score", updated.get("automationScore", 0))
            updated["processingResult"] = {
                "engine": "openai_llm_and_deterministic_python",
                "status": "optimized",
                "preparedAt": datetime.now(timezone.utc).isoformat(),
                "externalActionsExecuted": False,
            }
        else:
            workflow = current_workflow
            validate(workflow)
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

    @staticmethod
    def _build_optimized_workflow(optimization: dict) -> dict:
        raw_steps = optimization.get("optimized_workflow_steps") or []
        if not raw_steps:
            raise ValueError("The optimization model did not return any workflow steps.")

        steps: list[dict] = []
        for raw in raw_steps:
            step_type = raw.get("type")
            config = {"requiresApproval": bool(raw.get("requires_approval", False))}
            connector = (raw.get("connector") or "").strip()
            if connector:
                config["connector"] = connector
            steps.append({
                "id": "",
                "type": step_type,
                "name": raw.get("name", "").strip(),
                "description": raw.get("description", "").strip(),
                "config": config,
            })

        # Insert an approval gate immediately before the first outbound side effect
        # when the model omitted it or placed it too late.
        guarded_steps: list[dict] = []
        prior_approval = False
        for step in steps:
            if step["type"] in OUTBOUND_TYPES:
                if not prior_approval:
                    guarded_steps.append({
                        "id": "",
                        "type": "approval",
                        "name": "Human approval",
                        "description": "An authorized person reviews and approves the result before any external action.",
                        "config": {"requiresApproval": False},
                    })
                    prior_approval = True
                step["config"]["requiresApproval"] = True
            if step["type"] == "approval":
                prior_approval = True
            guarded_steps.append(step)

        for index, step in enumerate(guarded_steps, start=1):
            step["id"] = f"step-{index}"

        workflow = {
            "name": (optimization.get("optimized_workflow_name") or "Optimized process workflow").strip(),
            "trigger": (optimization.get("optimized_workflow_trigger") or "Manual start until configured").strip(),
            "steps": guarded_steps,
        }
        return workflow

    @staticmethod
    def _calculate_metrics(raw_metrics: list[dict]) -> list[dict]:
        """Calculate deltas in Python; never trust percentages supplied by the LLM."""
        calculated: list[dict] = []
        for item in raw_metrics:
            current = item.get("current_value")
            proposed = item.get("proposed_value")
            change = None
            change_percent = None

            if (
                isinstance(current, (int, float))
                and not isinstance(current, bool)
                and isinstance(proposed, (int, float))
                and not isinstance(proposed, bool)
                and math.isfinite(float(current))
                and math.isfinite(float(proposed))
            ):
                change = round(float(proposed) - float(current), 3)
                if float(current) != 0:
                    if item.get("direction") == "higher_is_better":
                        change_percent = round((float(proposed) - float(current)) / abs(float(current)) * 100, 2)
                    else:
                        change_percent = round((float(current) - float(proposed)) / abs(float(current)) * 100, 2)

            calculated.append({
                "name": item.get("name", ""),
                "currentValue": current,
                "proposedValue": proposed,
                "unit": item.get("unit", ""),
                "direction": item.get("direction", "lower_is_better"),
                "absoluteChange": change,
                "improvementPercent": change_percent,
                "rationale": item.get("rationale", ""),
                "evidenceBasis": item.get("evidence_basis", "not_available"),
                "confidence": item.get("confidence", "low"),
                "isEstimate": item.get("evidence_basis") == "model_estimate",
            })
        return calculated
