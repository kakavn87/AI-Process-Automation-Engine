from datetime import datetime, timezone


class ActionExecutor:
    """Dispatches workflow steps safely; external connectors remain disabled in this MVP."""

    OUTBOUND_TYPES = {"notify", "email", "teams", "http"}

    def execute_step(self, step: dict, context: dict | None = None) -> dict:
        step_type = step.get("type")
        config = step.get("config") or {}

        if step_type in self.OUTBOUND_TYPES:
            if config.get("requiresApproval") is not True:
                raise ValueError("Outbound actions must require explicit human approval.")
            status = "simulated"
            message = (
                "External action simulated. No email, Teams message, HTTP request, "
                "or other external side effect was performed."
            )
        elif step_type == "approval":
            status = "approved"
            message = "Human approval was recorded before continuing the simulation."
        else:
            status = "simulated"
            message = f"{step_type or 'workflow'} step validated and simulated successfully."

        return {
            "stepId": step.get("id"),
            "step": step.get("name"),
            "stepType": step_type,
            "status": status,
            "message": message,
            "recordedAt": datetime.now(timezone.utc).isoformat(),
            "externalSideEffect": False,
        }
