import re


class ProcessAnalyzer:
    """Transparent rules-based process analysis baseline (no external AI calls)."""

    SIGNAL_RULES = (
        ("email", 20, ("email", "e-mail", "outlook", "mailbox")),
        ("pdf", 15, ("pdf",)),
        ("excel", 15, ("excel", "spreadsheet", "xlsx", "spread sheet")),
        ("manual", 15, ("manual", "manually", "manuell", "manuelle", "by hand", "von hand")),
        ("teams", 10, ("teams", "microsoft teams")),
        ("weekly", 10, ("weekly", "every week", "each week", "every monday", "each monday", "wöchentlich", "jede woche", "jeden montag")),
    )

    def analyze(self, description: str) -> dict:
        text = description.lower()
        signals: list[str] = []
        score = 0

        for signal, points, patterns in self.SIGNAL_RULES:
            if any(self._contains(text, pattern) for pattern in patterns):
                signals.append(signal)
                score += points

        has_approval = any(self._contains(text, term) for term in (
            "approve", "approval", "review", "manager", "freigabe", "genehmig"
        ))
        has_report = any(self._contains(text, term) for term in (
            "report", "summary", "management", "bericht", "auswertung"
        ))
        has_validation = any(self._contains(text, term) for term in (
            "validate", "validation", "check", "missing", "quality", "prüf", "fehler"
        ))
        has_financial_data = any(term in text for term in ("finance", "financial", "invoice", "payment", "finanz", "rechnung"))

        current_process = self._current_process(signals, has_validation, has_report, has_approval)
        opportunities = self._opportunities(signals, has_validation, has_report)
        integrations = self._integrations(signals)
        approval_required = "teams" in signals or has_approval

        risks = [
            "Validate extracted values against the source files before using them in calculations.",
            "Define an explicit exception path for missing, unreadable, or duplicate attachments.",
        ]
        if has_financial_data:
            risks.append("Restrict access to financial data and keep an auditable record of changes and approvals.")
        if approval_required:
            risks.append("Do not send the final report until the designated manager has approved it.")

        assumptions = []
        if "pdf" in signals or "excel" in signals:
            assumptions.append("Source files have reasonably consistent layouts that can be parsed reliably.")
        if approval_required:
            assumptions.append("A named manager or authorized role is available to review the generated output.")

        questions = [
            "Which mailbox or folder should the process monitor?",
            "Which fields and validation rules are mandatory, and what should happen when data is missing?",
        ]
        if approval_required:
            questions.append("Who is the authorized approver, and where should the approval request appear?")
        if "teams" in signals:
            questions.append("Which Microsoft Teams channel should receive the approved report?")

        return {
            "automationScore": min(score, 100),
            "signals": signals,
            "description": description,
            "analysisMode": "deterministic_rules_v1",
            "analysisNote": "Transparent rules-based baseline. No LLM is called and no business system is connected yet.",
            "summary": self._summary(signals, has_report, approval_required),
            "currentProcess": current_process,
            "automationOpportunities": opportunities,
            "integrations": integrations,
            "humanApproval": {
                "required": approval_required,
                "reason": "A human review gate is recommended before the report is distributed." if approval_required else "No external distribution step was detected; add an approval gate for consequential actions.",
                "gateBefore": "Final report distribution" if approval_required else "Not detected",
            },
            "risks": risks,
            "assumptions": assumptions,
            "questions": questions,
        }

    @staticmethod
    def _contains(text: str, pattern: str) -> bool:
        return re.search(rf"(?<!\w){re.escape(pattern)}(?!\w)", text, flags=re.IGNORECASE) is not None

    @staticmethod
    def _current_process(signals: list[str], has_validation: bool, has_report: bool, has_approval: bool) -> list[str]:
        steps = []
        if "email" in signals:
            steps.append("Receive process inputs and attachments through email.")
        if "pdf" in signals or "excel" in signals:
            steps.append("Download and inspect PDF and spreadsheet attachments.")
            steps.append("Extract relevant values from the source documents.")
        if "excel" in signals:
            steps.append("Combine extracted values in a master spreadsheet.")
        if has_validation or "excel" in signals:
            steps.append("Check data completeness and identify missing or inconsistent values.")
        steps.append("Calculate the required results and prepare the output.")
        if has_report:
            steps.append("Create a summary report for the intended audience.")
        if has_approval:
            steps.append("Ask a manager to review and approve the report.")
        if "teams" in signals:
            steps.append("Share the approved report with the team in Microsoft Teams.")
        elif "email" in signals:
            steps.append("Distribute the completed output to the relevant recipients.")
        return steps

    @staticmethod
    def _opportunities(signals: list[str], has_validation: bool, has_report: bool) -> list[dict]:
        opportunities = []
        if "email" in signals:
            opportunities.append({"title": "Collect email attachments", "description": "Monitor a designated mailbox and collect matching attachments automatically.", "impact": "high"})
        if "pdf" in signals or "excel" in signals:
            opportunities.append({"title": "Extract document data", "description": "Read supported PDF and spreadsheet files and map values to a common data structure.", "impact": "high"})
        if "excel" in signals:
            opportunities.append({"title": "Consolidate spreadsheet data", "description": "Combine records into a standardized dataset instead of copying values manually.", "impact": "high"})
        if has_validation or "excel" in signals:
            opportunities.append({"title": "Validate data quality", "description": "Check required fields, duplicates, and invalid values; route exceptions for correction.", "impact": "high"})
        if has_report or "weekly" in signals:
            opportunities.append({"title": "Generate recurring reports", "description": "Calculate agreed metrics and create a consistent report from validated data.", "impact": "medium"})
        if "teams" in signals:
            opportunities.append({"title": "Notify through Microsoft Teams", "description": "Send the report link and a concise summary only after approval.", "impact": "medium"})
        if not opportunities:
            opportunities.append({"title": "Map repetitive work", "description": "Identify repeated manual steps, decision points, and system handoffs before selecting automations.", "impact": "medium"})
        return opportunities

    @staticmethod
    def _integrations(signals: list[str]) -> list[dict]:
        integrations = []
        if "weekly" in signals:
            integrations.append({"name": "Scheduler", "purpose": "Start the workflow on the agreed weekly schedule.", "status": "planned_not_connected"})
        if "email" in signals:
            integrations.append({"name": "Microsoft Outlook", "purpose": "Find incoming messages and download matching attachments.", "status": "planned_not_connected"})
        if "pdf" in signals:
            integrations.append({"name": "PDF parser", "purpose": "Extract text and tabular values from PDF files.", "status": "planned_not_connected"})
        if "excel" in signals:
            integrations.append({"name": "Excel / Spreadsheet processor", "purpose": "Read, normalize, validate, and consolidate spreadsheet rows.", "status": "planned_not_connected"})
        if "teams" in signals:
            integrations.append({"name": "Microsoft Teams", "purpose": "Deliver the approved report to the selected channel.", "status": "planned_not_connected"})
        return integrations

    @staticmethod
    def _summary(signals: list[str], has_report: bool, approval_required: bool) -> str:
        parts = []
        if "weekly" in signals:
            parts.append("a recurring weekly trigger")
        if "email" in signals:
            parts.append("email-based input collection")
        if "pdf" in signals or "excel" in signals:
            parts.append("document and spreadsheet data extraction")
        if has_report:
            parts.append("report generation")
        if approval_required:
            parts.append("a human approval gate before distribution")
        if "teams" in signals:
            parts.append("Microsoft Teams delivery")
        if not parts:
            return "The description contains a process that should be mapped into clear steps before automation is designed."
        return "The process includes " + ", ".join(parts) + "."
