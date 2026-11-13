ALLOWED_STEP_TYPES = {"analyze", "approval", "email", "teams", "http"}

def validate(workflow: dict) -> None:
    for step in workflow.get("steps", []):
        if step.get("type") not in ALLOWED_STEP_TYPES:
            raise ValueError(f"Unsupported workflow step: {step.get('type')}")
