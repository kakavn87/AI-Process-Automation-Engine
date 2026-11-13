COMPLEXITY_RULES = (
    ("conditional_logic", (
        "depending on", "based on customer", "based on risk", "if ... then",
        "unless", "except when", "different rules", "multiple approval",
        "approval levels", "decision tree", "classify", "prioritize",
        "je nach", "abhängig von", "abhaengig von", "falls ... dann",
        "unterschiedliche regeln", "mehrere freigabestufen",
    )),
    ("ambiguous_exceptions", (
        "edge cases", "case by case", "exception handling", "special cases",
        "individually assess", "einzelfall", "sonderfall", "ausnahmefall",
    )),
)

SUPPORTED_SYSTEMS = {
    "Microsoft Outlook", "Microsoft Teams", "SharePoint",
    "Shared folder", "SFTP", "API",
}


class ProcessRoutingPolicy:
    """Choose a deterministic Python path or an LLM path using explainable rules."""

    def decide(
        self,
        description: str,
        analysis: dict,
        requested_strategy: str = "auto",
        llm_available: bool = False,
    ) -> dict:
        if requested_strategy not in {"auto", "rules", "llm"}:
            raise ValueError("analysis_strategy must be one of: auto, rules, llm")

        details = analysis.get("detectedDetails") or {}
        activities = details.get("activities") or []
        cadence = details.get("cadence") or {}
        domain = details.get("businessDomain", "general")
        context_count = sum((
            bool(details.get("sourceChannels")),
            bool(details.get("fileTypes")),
            bool(details.get("deliveryChannels")),
            cadence.get("frequency", "manual") != "manual",
            domain != "general",
        ))
        complexity_flags = []
        normalized = description.lower()

        for flag, patterns in COMPLEXITY_RULES:
            if any(pattern in normalized for pattern in patterns):
                complexity_flags.append(flag)

        unsupported_systems = sorted(
            set(details.get("systems") or []) - SUPPORTED_SYSTEMS
        )
        if unsupported_systems:
            complexity_flags.append("unsupported_systems")
        if len(description) > 1600:
            complexity_flags.append("long_description")

        activity_score = min(len(activities), 4) * 15
        context_score = min(context_count, 3) * 10
        domain_score = 10 if domain != "general" else 0
        cadence_score = 10 if cadence.get("frequency", "manual") != "manual" else 0
        rule_confidence = min(100, activity_score + context_score + domain_score + cadence_score)

        rules_suitable = len(activities) >= 2 and context_count >= 1 and not complexity_flags

        if requested_strategy == "rules":
            selected_engine = "rules"
            reason = "Python rules were selected manually. This path does not call an LLM."
        elif requested_strategy == "llm":
            if llm_available:
                selected_engine = "llm"
                reason = "AI analysis was selected manually; the backend will call the configured LLM."
            else:
                selected_engine = "rules"
                reason = (
                    "AI analysis was requested, but OPENAI_API_KEY is not configured. "
                    "Python rules were used instead."
                )
        elif rules_suitable:
            selected_engine = "rules"
            reason = (
                "The process matches supported activities and has enough context for deterministic analysis. "
                "Python rules were selected to avoid an unnecessary LLM call."
            )
        elif llm_available:
            selected_engine = "llm"
            reason = (
                "The process is ambiguous or outside the current rules coverage. "
                "The configured LLM was selected for semantic analysis."
            )
        else:
            selected_engine = "rules"
            reason = (
                "The process is outside the current rules coverage, but no LLM API key is configured. "
                "The deterministic fallback will provide a best-effort proposal."
            )

        return {
            "requestedStrategy": requested_strategy,
            "selectedEngine": selected_engine,
            "llmAvailable": bool(llm_available),
            "ruleConfidence": rule_confidence,
            "rulesSuitable": rules_suitable,
            "complexityFlags": complexity_flags,
            "reason": reason,
        }
