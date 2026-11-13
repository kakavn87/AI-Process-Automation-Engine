from app.engine.execution.action_executor import ActionExecutor
from app.engine.workflow.validator import validate


class WorkflowExecutor:
    """Safe MVP executor: approved steps are dispatched in simulation mode only."""

    def __init__(self, action_executor: ActionExecutor | None = None):
        self.action_executor = action_executor or ActionExecutor()

    def execute(self, workflow: dict, approved: bool = False) -> dict:
        validate(workflow)
        if not approved:
            return {
                "status": "awaiting_approval",
                "executionMode": "simulation",
                "events": [],
            }

        events = [
            self.action_executor.execute_step(step, context={})
            for step in workflow.get("steps", [])
        ]
        return {
            "status": "completed",
            "executionMode": "simulation",
            "events": events,
        }
