from app.engine.workflow.validator import validate

class WorkflowExecutor:
    def execute(self, workflow: dict, approved: bool = False) -> dict:
        validate(workflow)
        if not approved:
            return {"status": "awaiting_approval"}
        return {"status": "completed", "events": []}
