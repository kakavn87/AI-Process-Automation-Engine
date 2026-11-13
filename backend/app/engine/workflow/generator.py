class WorkflowGenerator:
    def generate(self, description: str) -> dict:
        return {
            "name": "AI generated workflow",
            "steps": [
                {"type": "analyze", "name": "Analyze process", "config": {}},
                {"type": "approval", "name": "Human approval", "config": {}}
            ]
        }
