class ProcessAnalyzer:
    def analyze(self, description: str) -> dict:
        text = description.lower()
        score = 0
        signals = []

        for keyword, points in [
            ("email", 20), ("pdf", 15), ("excel", 15),
            ("manuell", 15), ("manual", 15), ("teams", 10),
            ("wiederkehr", 15), ("weekly", 10)
        ]:
            if keyword in text:
                score += points
                signals.append(keyword)

        score = min(score, 100)
        return {
            "automationScore": score,
            "signals": signals,
            "description": description
        }
