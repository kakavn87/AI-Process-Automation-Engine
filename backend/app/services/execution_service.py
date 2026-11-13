class ExecutionService:
    def execute(self, workflow: dict, approved: bool = False) -> dict:
        if not approved:
            return {"status": "awaiting_approval"}
        return {"status": "completed"}
