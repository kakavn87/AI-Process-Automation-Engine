class WorkflowGenerator:
    """Build a transparent workflow proposal from detected process details."""

    def generate(
        self,
        description: str,
        signals: list[str] | None = None,
        details: dict | None = None,
    ) -> dict:
        text = description.lower()
        detected = set(signals or [])
        details = details or {}
        cadence = details.get("cadence") or {}
        frequency = cadence.get("frequency", "manual")
        day = cadence.get("day")
        source_channels = details.get("sourceChannels") or (
            ["Microsoft Outlook"] if "email" in detected else []
        )
        file_types = details.get("fileTypes") or [
            label for signal, label in (("pdf", "PDF"), ("excel", "Excel")) if signal in detected
        ]
        delivery_channels = details.get("deliveryChannels") or (
            ["Microsoft Teams"] if "teams" in detected else []
        )
        activities = set(details.get("activities") or [])
        domain = details.get("businessDomain", "general")
        output_types = details.get("outputTypes") or []

        if frequency == "weekly":
            trigger = f"Run every week{f' on {day}' if day else ''} at the agreed time."
        elif frequency == "daily":
            trigger = "Run every day at the agreed time."
        elif frequency == "monthly":
            trigger = "Run every month at the agreed time."
        elif frequency == "on_event" or source_channels:
            trigger = "Run when new matching input arrives in the configured source."
        else:
            trigger = "Start manually until a trigger is configured."

        steps: list[dict] = []

        def add(
            step_type: str,
            name: str,
            detail: str,
            connector: str | None = None,
            requires_approval: bool = False,
        ) -> None:
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

        add("trigger", "Start workflow", trigger, "scheduler" if frequency in {"weekly", "daily", "monthly"} else None)

        if source_channels:
            source = source_channels[0]
            connector = {
                "Microsoft Outlook": "microsoft_outlook",
                "SharePoint": "sharepoint",
                "Shared folder": "shared_folder",
                "SFTP": "sftp",
                "API": "rest_api",
            }.get(source)
            add("collect", f"Collect inputs from {source}", f"Retrieve new process inputs from the configured {source} source.", connector)
        elif "email" in detected:
            add("collect", "Collect email attachments", "Find matching messages and download supported attachments.", "microsoft_outlook")

        if file_types:
            formats = ", ".join(file_types)
            add("extract", "Extract document data", f"Read supported {formats} files and map the required fields into structured records.", "document_parser")

        if "transform_data" in activities or any(file_type in {"Excel", "CSV"} for file_type in file_types) or "excel" in detected:
            add("transform", "Normalize and consolidate data", "Standardize field names and values, then combine records into a consistent dataset.", "spreadsheet_processor")

        if "validate_data" in activities or "excel" in detected:
            add("validate", "Validate source data", "Check required fields, duplicates, invalid values, and unresolved exceptions.")

        if "calculate_metrics" in activities:
            add("transform", "Calculate process results", "Apply the agreed calculations to validated records.")

        if "report" in output_types or "generate_output" in activities or not output_types:
            output_description = "Create the report or document from validated data and agreed business rules."
            output_name = "Generate report"
        elif "invoice" in output_types:
            output_description = "Prepare the invoice output from validated source data."
            output_name = "Generate invoice"
        else:
            output_description = "Prepare the output defined by the process owner."
            output_name = "Prepare process output"
        add("generate", output_name, output_description)

        needs_approval = (
            "approval" in activities
            or bool(delivery_channels)
            or any(term in text for term in ("approve", "approval", "manager", "freigabe", "genehmig"))
        )
        if needs_approval:
            add("approval", "Human approval", "Pause until an authorized person reviews and approves the prepared output.")

        for channel in delivery_channels:
            if channel == "Microsoft Teams":
                add("notify", "Notify Microsoft Teams", "Publish the approved report or result to the configured Teams channel after approval.", "microsoft_teams", requires_approval=needs_approval)
            elif channel == "Microsoft Outlook":
                add("email", "Send approved email", "Send the prepared output to the configured recipients after approval.", "microsoft_outlook", requires_approval=needs_approval)
            elif channel == "Slack":
                add("notify", "Notify Slack", "Post the approved result to the configured Slack destination after approval.", "slack", requires_approval=needs_approval)
            else:
                add("notify", f"Notify through {channel}", f"Deliver the approved result through the configured {channel} destination after approval.", requires_approval=needs_approval)

        if not delivery_channels and "notify" in activities:
            add("notify", "Notify configured recipients", "Deliver the result through a destination that must be selected by the process owner.", requires_approval=True)

        domain_label = {
            "finance": "Finance",
            "human_resources": "HR",
            "sales": "Sales",
            "procurement": "Procurement",
            "customer_support": "Customer Support",
            "operations": "Operations",
        }.get(domain)
        if domain_label and "report" in output_types and frequency == "weekly":
            workflow_name = f"Weekly {domain_label} Reporting"
        elif domain_label:
            workflow_name = f"{domain_label} Process Workflow"
        else:
            workflow_name = "Proposed Process Workflow"

        return {
            "name": workflow_name,
            "trigger": trigger,
            "steps": steps,
        }
