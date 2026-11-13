from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.workflow_session import AIUsageEvent


class AIUsageService:
    def __init__(self, db: Session):
        self.db = db

    def record(self, session_id: str | None, telemetry: dict) -> AIUsageEvent:
        input_tokens = telemetry.get("inputTokens")
        output_tokens = telemetry.get("outputTokens")
        total_tokens = telemetry.get("totalTokens")
        cost = None

        input_rate = settings.OPENAI_INPUT_USD_PER_1M
        output_rate = settings.OPENAI_OUTPUT_USD_PER_1M
        if (
            input_tokens is not None
            and output_tokens is not None
            and input_rate is not None
            and output_rate is not None
        ):
            cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000

        event = AIUsageEvent(
            id=str(uuid4()),
            session_id=session_id,
            provider=telemetry.get("provider", "openai"),
            model=telemetry.get("model") or settings.OPENAI_MODEL,
            task=telemetry.get("task", "process_analysis"),
            status=telemetry.get("status", "success"),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
            duration_ms=telemetry.get("durationMs"),
            error_type=telemetry.get("errorType"),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def summary(self, limit: int = 25) -> dict:
        rows = self.db.query(AIUsageEvent).order_by(AIUsageEvent.created_at.desc()).limit(limit).all()
        totals = self.db.query(
            func.count(AIUsageEvent.id),
            func.sum(AIUsageEvent.input_tokens),
            func.sum(AIUsageEvent.output_tokens),
            func.sum(AIUsageEvent.total_tokens),
            func.sum(AIUsageEvent.estimated_cost_usd),
        ).one()

        success_count = sum(1 for row in rows if row.status == "success")
        fallback_count = sum(1 for row in rows if row.status == "fallback")
        priced_count = sum(1 for row in rows if row.estimated_cost_usd is not None)

        return {
            "totalCalls": int(totals[0] or 0),
            "successfulCalls": success_count,
            "fallbackCalls": fallback_count,
            "inputTokens": int(totals[1] or 0),
            "outputTokens": int(totals[2] or 0),
            "totalTokens": int(totals[3] or 0),
            "estimatedCostUsd": float(totals[4]) if totals[4] is not None else None,
            "pricedCalls": priced_count,
            "pricingConfigured": (
                settings.OPENAI_INPUT_USD_PER_1M is not None
                and settings.OPENAI_OUTPUT_USD_PER_1M is not None
            ),
            "events": [
                {
                    "id": row.id,
                    "sessionId": row.session_id,
                    "provider": row.provider,
                    "model": row.model,
                    "task": row.task,
                    "status": row.status,
                    "inputTokens": row.input_tokens,
                    "outputTokens": row.output_tokens,
                    "totalTokens": row.total_tokens,
                    "estimatedCostUsd": row.estimated_cost_usd,
                    "durationMs": row.duration_ms,
                    "errorType": row.error_type,
                    "createdAt": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ],
        }
