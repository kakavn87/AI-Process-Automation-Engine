import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.engine.analyzer.process_analyzer import ProcessAnalyzer
from app.engine.workflow.generator import WorkflowGenerator
from app.engine.workflow.validator import validate
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)
OUTBOUND_STEP_TYPES = {"notify", "email", "teams", "http"}


class ProcessService:
    def __init__(self, db: Session, ai_service: AIService | None = None):
        self.db = db
        self.analyzer = ProcessAnalyzer()
        self.workflow_generator = WorkflowGenerator()
        self.ai_service = ai_service or AIService()

    def analyze(self, description: str) -> dict:
        analysis = self.analyzer.analyze(description)
        analysis["llmUsed"] = False
        analysis["llmModel"] = None
        analysis["analysisMode"] = "deterministic_rules_v1"

        if self.ai_service.is_configured:
            try:
                ai_result = self.ai_service.analyze_process(description, analysis["signals"])
                self._apply_ai_result(analysis, ai_result)
                analysis["llmUsed"] = True
                analysis["llmModel"] = self.ai_service.model
                analysis["analysisMode"] = "openai_responses"
                analysis["analysisNote"] = (
                    f"Analyzed with OpenAI Responses API ({self.ai_service.model}). "
                    "The workflow is a proposal; integrations are not connected and execution is simulated."
                )
                return analysis
            except Exception:
                logger.exception("OpenAI process analysis failed; using the deterministic fallback.")
                analysis["analysisNote"] = (
                    "The OpenAI request could not be completed. A deterministic rules-based fallback was used. "
                    "Check the backend API key, model access, and API billing configuration."
                )
        else:
            analysis["analysisNote"] = (
                "OpenAI is not enabled because OPENAI_API_KEY is missing on the backend. "
                "A deterministic rules-based fallback was used."
            )

        workflow = self.workflow_generator.generate(
            description,
            analysis["signals"],
            analysis.get("detectedDetails"),
        )
        self._ensure_approval_gate(workflow)
        validate(workflow)
        analysis["proposedWorkflow"] = workflow
        return analysis

    def _apply_ai_result(self, analysis: dict, ai_result: dict) -> None:
        workflow_steps = []
        for index, item in enumerate(ai_result["workflow_steps"], start=1):
            config = {"requiresApproval": bool(item["requires_approval"])}
            connector = item.get("connector", "").strip()
            if connector:
                config["connector"] = connector
            workflow_steps.append({
                "id": f"step-{index}",
                "type": item["type"],
                "name": item["name"],
                "description": item["description"],
                "config": config,
            })

        workflow = {
            "name": ai_result["workflow_name"],
            "trigger": ai_result["workflow_trigger"],
            "steps": workflow_steps,
        }
        self._ensure_approval_gate(
            workflow,
            force_approval=bool(ai_result["human_approval_required"]),
        )
        validate(workflow)

        analysis.update({
            "summary": ai_result["summary"],
            "currentProcess": ai_result["current_process"],
            "automationOpportunities": ai_result["automation_opportunities"],
            "integrations": [
                {**item, "status": "planned_not_connected"}
                for item in ai_result["integrations"]
            ],
            "humanApproval": {
                "required": bool(ai_result["human_approval_required"]) or any(
                    step["type"] in OUTBOUND_STEP_TYPES for step in workflow["steps"]
                ),
                "reason": ai_result["human_approval_reason"],
                "gateBefore": ai_result["human_approval_gate_before"],
            },
            "risks": ai_result["risks"],
            "assumptions": ai_result["assumptions"],
            "questions": ai_result["questions"],
            "proposedWorkflow": workflow,
        })

    @staticmethod
    def _ensure_approval_gate(workflow: dict, force_approval: bool = False) -> None:
        steps = workflow.setdefault("steps", [])
        if not steps or steps[0].get("type") != "trigger":
            steps.insert(0, {
                "type": "trigger",
                "name": "Start workflow",
                "description": workflow.get("trigger", "Start the workflow manually."),
                "config": {"requiresApproval": False},
            })

        if not any(step.get("type") == "generate" for step in steps):
            approval_index = next(
                (i for i, step in enumerate(steps) if step.get("type") == "approval"),
                len(steps),
            )
            steps.insert(approval_index, {
                "type": "generate",
                "name": "Prepare process output",
                "description": "Prepare the output defined by the process owner.",
                "config": {"requiresApproval": False},
            })

        outbound_positions = [
            i for i, step in enumerate(steps)
            if step.get("type") in OUTBOUND_STEP_TYPES
        ]
        must_approve = force_approval or bool(outbound_positions)
        if must_approve:
            # Place exactly one approval step after the last output-preparation step
            # and before the first external notification.
            first_outbound = outbound_positions[0] if outbound_positions else len(steps)
            prior_steps = steps[:first_outbound]
            last_preparation = max(
                (i for i, step in enumerate(prior_steps)
                 if step.get("type") in {"generate", "validate", "transform"}),
                default=first_outbound - 1,
            )
            steps[:] = [step for step in steps if step.get("type") != "approval"]
            first_outbound = next(
                (i for i, step in enumerate(steps) if step.get("type") in OUTBOUND_STEP_TYPES),
                len(steps),
            )
            insertion_index = min(last_preparation + 1, first_outbound)
            steps.insert(insertion_index, {
                "type": "approval",
                "name": "Human approval",
                "description": "Pause until an authorized person reviews and approves the output.",
                "config": {"requiresApproval": False},
            })

        for index, step in enumerate(steps, start=1):
            step["id"] = f"step-{index}"
            step.setdefault("config", {})
            if step.get("type") in OUTBOUND_STEP_TYPES:
                step["config"]["requiresApproval"] = True
