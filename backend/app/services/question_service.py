import hashlib
import re
from typing import Any


class QuestionService:
    """Convert analysis questions into stable, UI-ready question definitions."""

    @staticmethod
    def build(questions: list[str] | None) -> list[dict[str, Any]]:
        result = []
        seen: set[str] = set()

        for raw_question in questions or []:
            prompt = re.sub(r"\s+", " ", str(raw_question)).strip()
            if not prompt:
                continue

            question_id = "q-" + hashlib.sha256(prompt.casefold().encode("utf-8")).hexdigest()[:12]
            if question_id in seen:
                continue
            seen.add(question_id)

            lowered = prompt.casefold()
            is_boolean = (
                lowered.startswith(("is ", "are ", "do ", "does ", "should ", "can "))
                or lowered.startswith(("ist ", "sind ", "soll ", "kann ", "gibt es "))
            )
            result.append({
                "id": question_id,
                "prompt": prompt,
                "type": "boolean" if is_boolean else "text",
                "required": True,
                "options": ["yes", "no"] if is_boolean else [],
                "placeholder": (
                    "Please enter a short answer." if not is_boolean
                    else "Choose yes or no."
                ),
            })
        return result

    @staticmethod
    def validate_answer(question: dict, value: Any) -> str | bool:
        question_id = question.get("id", "unknown")
        if question.get("type") == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                normalized = value.strip().casefold()
                if normalized in {"yes", "ja", "true", "1"}:
                    return True
                if normalized in {"no", "nein", "false", "0"}:
                    return False
            raise ValueError(f"Question {question_id} expects yes/no.")

        if not isinstance(value, str):
            raise ValueError(f"Question {question_id} expects text.")
        normalized = value.strip()
        if question.get("required") and not normalized:
            raise ValueError(f"Question {question_id} requires an answer.")
        if len(normalized) > 4000:
            raise ValueError(f"Question {question_id} exceeds 4000 characters.")
        return normalized
