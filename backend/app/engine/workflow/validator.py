ALLOWED_STEP_TYPES = {
    "analyze", "approval", "email", "teams", "http",
    "trigger", "collect", "extract", "transform", "validate", "generate", "notify",
}
OUTBOUND_STEP_TYPES = {"notify", "email", "teams", "http"}


def validate(workflow: dict) -> None:
    steps = workflow.get("steps", [])
    seen_ids = set()

    for step in steps:
        step_type = step.get("type")
        if step_type not in ALLOWED_STEP_TYPES:
            raise ValueError(f"Unsupported workflow step: {step_type}")
        step_id = step.get("id")
        if step_id:
            if step_id in seen_ids:
                raise ValueError(f"Duplicate workflow step id: {step_id}")
            seen_ids.add(step_id)

    for index, step in enumerate(steps):
        config = step.get("config") or {}
        needs_approval = step.get("type") in OUTBOUND_STEP_TYPES or (
            step.get("type") == "http" and config.get("requiresApproval")
        )
        if needs_approval:
            has_prior_approval = any(previous.get("type") == "approval" for previous in steps[:index])
            if not has_prior_approval:
                raise ValueError("A human approval step must come before any outbound side-effect step.")
