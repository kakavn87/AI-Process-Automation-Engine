import re

from app.core.localization import localize_process_analysis


class ProcessAnalyzer:
    """Transparent rules-based process analysis baseline (no external AI calls)."""

    SIGNAL_RULES = (
        ("email", 20, ("email", "e-mail", "outlook", "mailbox")),
        ("pdf", 15, ("pdf",)),
        ("excel", 15, ("excel", "spreadsheet", "xlsx", "spread sheet", "csv")),
        ("manual", 15, ("manual", "manually", "manuell", "manuelle", "by hand", "von hand")),
        ("teams", 10, ("teams", "microsoft teams")),
        ("weekly", 10, ("weekly", "every week", "each week", "every monday", "each monday", "wöchentlich", "jede woche", "jeden montag")),
    )

    ACTIVITY_RULES = (
        ("collect_inputs", "Collect inputs", ("receive", "receives", "collect", "retrieve", "download", "import", "incoming", "erhalt", "empfang", "abruf", "herunterlad", "eingang")),
        ("extract_data", "Extract data", ("extract", "parse", "read", "ocr", "ausles", "extrahier", "einles")),
        ("transform_data", "Transform and consolidate data", ("combine", "consolidate", "merge", "normalize", "normalise", "map", "zusammenführ", "konsolidier", "normalisier", "vereinheitlich")),
        ("validate_data", "Validate data", ("validate", "validation", "check", "verify", "missing", "quality", "prüf", "kontroll", "validier", "fehlend", "fehler")),
        ("calculate_metrics", "Calculate results", ("calculate", "calculates", "compute", "sum", "total", "berechn", "kalkulier")),
        ("generate_output", "Generate output", ("generate", "create", "prepare", "produce", "erstelle", "erstell", "generier", "vorbereit")),
        ("approval", "Obtain human approval", ("approve", "approval", "manager", "sign off", "sign-off", "freigabe", "genehmig")),
        ("notify", "Notify recipients", ("notify", "send", "distribute", "share", "publish", "benachrichtig", "verschick", "sende", "verteil")),
        ("update_records", "Update system records", ("update", "save", "write to", "store", "aktualisier", "speicher", "eintrag")),
    )

    DOMAIN_RULES = (
        ("finance", ("finance", "financial", "invoice", "payment", "accounting", "accounts payable", "accounts receivable", "expense", "finanz", "rechnung", "buchhaltung", "zahlung", "abrechnung")),
        ("human_resources", ("human resources", "hr ", "employee", "payroll", "vacation", "leave request", "personalabteilung", "mitarbeiter", "gehaltsabrechnung", "lohn", "urlaub")),
        ("sales", ("sales", "lead", "opportunity", "customer order", "vertrieb", "verkauf", "kundenauftrag")),
        ("procurement", ("procurement", "purchase order", "supplier", "vendor", "bestellung", "lieferant", "einkauf")),
        ("customer_support", ("customer support", "support ticket", "complaint", "service request", "kundenservice", "beschwerde")),
        ("legal_compliance", ("legal", "compliance", "contract review", "contract clause", "regulatory", "datenschutz", "recht", "vertrag", "vertragsklausel", "richtlinie", "gesetz")),
        ("manufacturing", ("manufacturing", "production line", "production planning", "quality inspection", "quality management", "factory", "fertigung", "produktion", "qualitätsmanagement", "qualitaetsmanagement", "prüfprotokoll", "pruefprotokoll", "ausschuss")),
        ("it_operations", ("it operations", "it support", "helpdesk", "help desk", "service desk", "incident", "access rights", "zugriffsrechte", "it-ticket", "it ticket", "störung", "stoerung", "bereitschaftsdienst")),
        ("marketing", ("marketing", "campaign", "advertising", "social media", "content approval", "conversion rate", "kampagne", "werbung", "anzeigen", "reichweite")),
        ("project_management", ("project management", "project status", "milestone", "steering committee", "projektmanagement", "projektstatus", "meilenstein", "lenkungskreis", "projektbericht")),
        ("logistics", ("logistics", "shipment", "shipping", "freight", "transportation", "delivery route", "supply chain", "versand", "fracht", "transport", "spedition", "lieferroute")),
        ("operations", ("inventory", "warehouse", "stock", "facility", "maintenance request", "building maintenance", "lager", "bestand", "facility management", "wartung", "gebäudemanagement", "gebaeudemanagement", "haustechnik")),
    )

    def analyze(self, description: str, language: str = "en") -> dict:
        text = description.lower()
        signals: list[str] = []
        score = 0

        for signal, points, patterns in self.SIGNAL_RULES:
            if any(self._contains(text, pattern) for pattern in patterns):
                signals.append(signal)
                score += points

        activities = self._detect_activities(text)
        details = self._extract_process_details(text, signals, activities)

        has_approval = "approval" in activities or any(
            self._contains_variant(text, term)
            for term in ("approve", "approval", "review", "manager", "freigabe", "genehmig")
        )
        has_report = any(
            self._contains_variant(text, term)
            for term in ("report", "summary", "management", "dashboard", "bericht", "auswertung")
        )
        has_validation = "validate_data" in activities
        has_financial_data = details["businessDomain"] == "finance"

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
        if details["fileTypes"]:
            assumptions.append("Source files have reasonably consistent layouts that can be parsed reliably.")
        if approval_required:
            assumptions.append("A named manager or authorized role is available to review the generated output.")

        questions = []
        if details["sourceChannels"]:
            questions.append("Which exact mailbox, folder, or source location should the process monitor?")
        else:
            questions.append("Where does the process receive its input data?")
        if details["fileTypes"]:
            questions.append("Which fields and validation rules are mandatory, and what should happen when data is missing?")
        if approval_required:
            questions.append("Who is the authorized approver, and where should the approval request appear?")
        if "teams" in signals:
            questions.append("Which Microsoft Teams channel should receive the approved report?")

        # The legacy signal score remains unchanged when it has evidence. For new
        # German or niche processes, use detected activities and context instead
        # of incorrectly displaying 0% just because fixed keywords did not match.
        context_evidence = (
            len(details["sourceChannels"])
            + len(details["fileTypes"])
            + len(details["systems"])
            + len(details["outputTypes"])
        )
        activity_evidence = min(len(activities), 6) * 10
        context_score = min(context_evidence, 5) * 5
        minimum_evidence_score = 15 if len(description.strip()) >= 20 else 0
        inferred_score = min(85, minimum_evidence_score + activity_evidence + context_score)
        automation_score = max(min(score, 100), inferred_score)

        result = {
            "automationScore": automation_score,
            "signals": signals,
            "description": description,
            "analysisMode": "deterministic_rules_v1",
            "analysisNote": (
                "Analyzed with deterministic Python rules. Process details are inferred from detected phrases; "
                "external systems are not connected and workflow execution remains simulated."
            ),
            "detectedDetails": details,
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
        return localize_process_analysis(result, language)

    @staticmethod
    def _contains(text: str, pattern: str) -> bool:
        return re.search(rf"(?<!\w){re.escape(pattern)}(?!\w)", text, flags=re.IGNORECASE) is not None

    @staticmethod
    def _contains_variant(text: str, pattern: str) -> bool:
        """Match a whole word or a known stem, including common German word endings."""
        return re.search(rf"(?<!\w){re.escape(pattern)}\w*", text, flags=re.IGNORECASE) is not None

    @classmethod
    def _has_any(cls, text: str, patterns: tuple[str, ...]) -> bool:
        return any(cls._contains_variant(text, pattern) for pattern in patterns)

    @classmethod
    def _detect_activities(cls, text: str) -> list[str]:
        return [
            key
            for key, _label, patterns in cls.ACTIVITY_RULES
            if cls._has_any(text, patterns)
        ]

    @classmethod
    def _extract_process_details(
        cls,
        text: str,
        signals: list[str],
        activities: list[str],
    ) -> dict:
        frequency = "manual"
        day = None
        if cls._has_any(text, ("weekly", "every week", "each week", "wöchentlich", "jede woche", "jeden montag")):
            frequency = "weekly"
            if cls._has_any(text, ("monday", "montag")):
                day = "Monday"
            elif cls._has_any(text, ("tuesday", "dienstag")):
                day = "Tuesday"
            elif cls._has_any(text, ("wednesday", "mittwoch")):
                day = "Wednesday"
            elif cls._has_any(text, ("thursday", "donnerstag")):
                day = "Thursday"
            elif cls._has_any(text, ("friday", "freitag")):
                day = "Friday"
        elif cls._has_any(text, ("daily", "every day", "each day", "täglich", "jeden tag")):
            frequency = "daily"
        elif cls._has_any(text, ("monthly", "every month", "each month", "monatlich", "jeden monat")):
            frequency = "monthly"
        elif "email" in signals:
            frequency = "on_event"

        source_channels = []
        if "email" in signals:
            source_channels.append("Microsoft Outlook")
        if cls._has_any(text, ("sharepoint",)):
            source_channels.append("SharePoint")
        if cls._has_any(text, ("shared folder", "network drive", "gemeinsamer ordner", "netzlaufwerk")):
            source_channels.append("Shared folder")
        if cls._has_any(text, ("sftp", "ftp server")):
            source_channels.append("SFTP")
        if cls._has_any(text, ("api endpoint", "webhook", "rest api")):
            source_channels.append("API")

        file_types = []
        if cls._has_any(text, ("pdf",)):
            file_types.append("PDF")
        if cls._has_any(text, ("excel", "xlsx", "spreadsheet", "spread sheet")):
            file_types.append("Excel")
        if cls._has_any(text, ("csv",)):
            file_types.append("CSV")
        if cls._has_any(text, ("word document", "docx", "microsoft word")):
            file_types.append("Word")
        if cls._has_any(text, ("json",)):
            file_types.append("JSON")
        if cls._has_any(text, ("xml",)):
            file_types.append("XML")
        if cls._has_any(text, ("scanned image", "image file", "jpg", "jpeg", "png", "scan")):
            file_types.append("Image")

        delivery_channels = []
        if "teams" in signals:
            delivery_channels.append("Microsoft Teams")
        if cls._has_any(text, ("slack",)):
            delivery_channels.append("Slack")
        email_delivery = re.search(
            r"(send|sent|deliver|email|e-mail|verschick|sende|versend)\w*.{0,50}(email|e-mail|outlook)"
            r"|(?:per|via|über)\s+e-?mail\s+(?:versend|schick|send)",
            text,
            flags=re.IGNORECASE,
        )
        if email_delivery:
            delivery_channels.append("Microsoft Outlook")

        systems = list(dict.fromkeys(source_channels + delivery_channels))
        for system, patterns in (
            ("SAP", ("sap",)),
            ("Salesforce", ("salesforce",)),
            ("Microsoft Dynamics", ("dynamics 365", "microsoft dynamics")),
            ("Google Drive", ("google drive",)),
            ("Database", ("database", "sql database", "datenbank")),
        ):
            if cls._has_any(text, patterns) and system not in systems:
                systems.append(system)

        domain = "general"
        for candidate, patterns in cls.DOMAIN_RULES:
            if cls._has_any(text, patterns):
                domain = candidate
                break

        outputs = []
        if cls._has_any(text, ("report", "summary report", "dashboard", "bericht", "auswertung")):
            outputs.append("report")
        if cls._has_any(text, ("invoice", "rechnung")):
            outputs.append("invoice")
        if cls._has_any(text, ("spreadsheet", "excel file", "csv file", "master excel", "tabelle")):
            outputs.append("spreadsheet")
        if cls._has_any(text, ("database", "crm", "datensatz", "record")):
            outputs.append("system_record")
        if delivery_channels:
            outputs.append("notification")
        if not outputs:
            outputs.append("process_output")

        roles = []
        if domain == "finance" and cls._has_any(text, ("finance team", "finance department", "finanzabteilung", "buchhaltung")):
            roles.append("Finance team")
        if cls._has_any(text, ("employee", "staff", "mitarbeiter", "sachbearbeiter")):
            roles.append("Employee")
        if cls._has_any(text, ("manager", "management", "team lead", "vorgesetzt", "leitung")):
            roles.append("Manager")
        if cls._has_any(text, ("customer", "client", "kunde")):
            roles.append("Customer")

        activity_labels = {
            key: label for key, label, _patterns in cls.ACTIVITY_RULES
        }
        return {
            "businessDomain": domain,
            "cadence": {
                "frequency": frequency,
                "day": day,
            },
            "sourceChannels": source_channels,
            "fileTypes": file_types,
            "activities": activities,
            "activityLabels": [activity_labels[key] for key in activities],
            "deliveryChannels": delivery_channels,
            "systems": systems,
            "outputTypes": outputs,
            "roles": roles,
            "extractionMethod": "deterministic_rules",
        }

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
