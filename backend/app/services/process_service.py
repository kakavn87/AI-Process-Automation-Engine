from sqlalchemy.orm import Session

from app.engine.analyzer.process_analyzer import ProcessAnalyzer
from app.engine.workflow.generator import WorkflowGenerator
from app.engine.workflow.validator import validate
from app.services.ai_service import AIService


class ProcessService:
    def __init__(self, db: Session):
        self.db = db
        self.analyzer = ProcessAnalyzer()
        self.workflow_generator = WorkflowGenerator()
        self.ai_service = AIService()

    def analyze(self, description: str) -> dict:
        ai_analysis = self.ai_service.analyze_process(description)
        if ai_analysis is not None:
            result = self._from_llm(ai_analysis, description)
            result["analysisMode"] = "openai_llm"
            result["analysisNote"] = (
                f"Analyzed with OpenAI {self._model_name()} using structured outputs. "
                "Scores are estimates; integrations are proposed, not connected."
            )
        else:
            result = self.analyzer.analyze(description)
            result["analysisMode"] = "rules_fallback"
            result["analysisNote"] = (
                "OpenAI LLM is not configured or unavailable. This result was produced by transparent "
                "local rules; configure OPENAI_API_KEY to enable model-based analysis."
            )

        validate(result["proposedWorkflow"])
        return result

    def _from_llm(self, analysis, description: str) -> dict:
        steps = []
        for index, item in enumerate(analysis.workflow_steps, start=1):
            config = {"requiresApproval": item.requires_approval}
            if item.connector:
                config["connector"] = item.connector
            steps.append({
                "id": f"step-{index}",
                "type": item.type,
                "name": item.name,
                "description": item.description,
                "config": config,
            })

        outbound_types = {"notify", "email", "teams"}
        outbound_indexes = [i for i, step in enumerate(steps) if step["type"] in outbound_types]
        approval_required = analysis.approval_required or bool(outbound_indexes)
        approval_index = next((i for i, step in enumerate(steps) if step["type"] == "approval"), -1)

        # Enforce a server-side approval gate for outbound side effects.
        if approval_required and approval_index < 0:
            insert_at = outbound_indexes[0] if outbound_indexes else len(steps)
            steps.insert(insert_at, {
                "id": "approval-inserted",
                "type": "approval",
                "name": "Human approval",
                "description": "Pause until an authorized person reviews and approves this workflow.",
                "config": {"requiresApproval": False},
            })
            approval_index = insert_at

        for step in steps:
            if step["type"] in outbound_types:
                step["config"]["requiresApproval"] = True

        if approval_required:
            first_outbound = next((i for i, step in enumerate(steps) if step["type"] in outbound_types), len(steps))
            approval_index = next((i for i, step in enumerate(steps) if step["type"] == "approval"), -1)
            if approval_index > first_outbound:
                approval = steps.pop(approval_index)
                steps.insert(first_outbound, approval)

        for index, step in enumerate(steps, start=1):
            step["id"] = f"step-{index}"

        return {
            "automationScore": max(0, min(100, analysis.automation_score)),
            "signals": list(dict.fromkeys(signal.lower().strip() for signal in analysis.signals if signal.strip())),
            "description": description,
            "summary": analysis.summary,
            "currentProcess": analysis.current_process,
            "automationOpportunities": [item.model_dump() for item in analysis.automation_opportunities],
            "integrations": [item.model_dump() for item in analysis.integrations],
            "humanApproval": {
                "required": approval_required,
                "reason": analysis.approval_reason,
                "gateBefore": analysis.approval_gate_before or ("External distribution" if approval_required else "Not required"),
            },
            "risks": analysis.risks,
            "assumptions": analysis.assumptions,
            "questions": analysis.questions,
            "proposedWorkflow": {
                "name": analysis.workflow_name,
                "trigger": analysis.workflow_trigger,
                "steps": steps,
            },
        }

    @staticmethod
    def _model_name() -> str:
        from app.core.config import settings
        return settings.OPENAI_MODEL
