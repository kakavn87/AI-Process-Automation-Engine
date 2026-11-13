class WorkflowGenerator:
    """Build a transparent draft workflow from the detected process signals."""

    def generate(self, description: str, signals: list[str] | None = None) -> dict:
        text = description.lower()
        detected = set(signals or [])
        steps: list[dict] = []

        def add(step_type: str, name: str, detail: str, connector: str | None = None, requires_approval: bool = False) -> None:
            config = {"requiresApproval": requires_approval}
            if connector:
                config["connector"] = connector
            steps.append({
                "id": f"step-{len(steps) + 1}",
                "type": step_type,
                "name": name,
                "description": detail,
                "config": config,
            })

        if "weekly" in detected:
            trigger = "Run every week at the agreed time."
        elif "email" in detected:
            trigger = "Run when a matching email is received."
        else:
            trigger = "Start manually until a trigger is configured."

        add("trigger", "Start workflow", trigger, "scheduler" if "weekly" in detected else None)

        if "email" in detected:
            add("collect", "Collect email attachments", "Find matching messages and download supported attachments.", "microsoft_outlook")
        if "pdf" in detected or "excel" in detected:
            add("extract", "Extract document data", "Read supported source files and map the required fields.", "document_parser")
        if "excel" in detected:
            add("transform", "Consolidate spreadsheet data", "Normalize records and combine them into the reporting dataset.", "spreadsheet_processor")
        if "excel" in detected:
            add("validate", "Validate source data", "Check required fields, duplicates, and invalid values; stop on unresolved exceptions.")
        elif any(word in text for word in ("validate", "missing", "check", "prüf")):
            add("validate", "Validate process data", "Apply the validation rules defined by the process owner.")
        add("generate", "Generate report", "Calculate the agreed metrics and create the report output.")

        needs_approval = "teams" in detected or any(word in text for word in ("approve", "approval", "review", "manager", "freigabe", "genehmig"))
        if needs_approval:
            add("approval", "Manager approval", "Pause the workflow until an authorized manager approves the generated report.")

        if "teams" in detected:
            add("notify", "Send report to Microsoft Teams", "Publish the report summary or link to the configured channel after approval.", "microsoft_teams", requires_approval=needs_approval)

        return {
            "name": "Weekly Financial Report" if "weekly" in detected and "excel" in detected else "Proposed Process Workflow",
            "trigger": trigger,
            "steps": steps,
        }
