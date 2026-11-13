from app.engine.workflow.validator import validate


class WorkflowExecutor:
    """Safe MVP executor: records simulated steps but performs no external side effects."""

    def execute(self, workflow: dict, approved: bool = False) -> dict:
        validate(workflow)
        if not approved:
            return {
                "status": "awaiting_approval",
                "executionMode": "simulation",
                "events": [],
            }

        events = []
        for step in workflow.get("steps", []):
            step_type = step.get("type")
            if step_type == "approval":
                events.append({
                    "stepId": step.get("id"),
                    "step": step.get("name"),
                    "status": "approved",
                    "message": "Human approval was recorded.",
                })
                continue

            events.append({
                "stepId": step.get("id"),
                "step": step.get("name"),
                "status": "simulated",
                "message": (
                    "External action simulated; no email, Teams message, or external system was contacted."
                    if step_type in {"notify", "email", "teams"}
                    else "Workflow step simulated successfully."
                ),
            })

        return {
            "status": "completed",
            "executionMode": "simulation",
            "events": events,
        }
