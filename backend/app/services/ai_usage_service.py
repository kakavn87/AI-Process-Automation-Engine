from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.workflow_session import AIUsageEvent


class AIUsageService:
    def __init__(self, db: Session, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    def record(self, session_id: str | None, telemetry: dict) -> AIUsageEvent:
        input_tokens = telemetry.get("inputTokens")
        output_tokens = telemetry.get("outputTokens")
        total_tokens = telemetry.get("totalTokens")
        cost = None

        input_rate = settings.OPENAI_INPUT_USD_PER_1M
        output_rate = settings.OPENAI_OUTPUT_USD_PER_1M
        if telemetry.get("task") == "rag_embedding":
            embedding_rate = settings.RAG_EMBEDDING_INPUT_USD_PER_1M
            if input_tokens is not None and embedding_rate is not None:
                cost = input_tokens * embedding_rate / 1_000_000
        elif (
            input_tokens is not None
            and output_tokens is not None
            and input_rate is not None
            and output_rate is not None
        ):
            cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000

        event = AIUsageEvent(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
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
        base_query = self.db.query(AIUsageEvent)
        if self.tenant_id is not None:
            base_query = base_query.filter(AIUsageEvent.tenant_id == self.tenant_id)
        rows = base_query.order_by(AIUsageEvent.created_at.desc()).limit(limit).all()
        totals = base_query.with_entities(
            func.count(AIUsageEvent.id),
            func.sum(AIUsageEvent.input_tokens),
            func.sum(AIUsageEvent.output_tokens),
            func.sum(AIUsageEvent.total_tokens),
            func.sum(AIUsageEvent.estimated_cost_usd),
        ).one()
        success_count = (
            base_query.filter(AIUsageEvent.status == "success")
            .with_entities(func.count(AIUsageEvent.id))
            .scalar() or 0
        )
        fallback_count = (
            base_query.filter(AIUsageEvent.status == "fallback")
            .with_entities(func.count(AIUsageEvent.id))
            .scalar() or 0
        )
        priced_count = (
            base_query.filter(AIUsageEvent.estimated_cost_usd.is_not(None))
            .with_entities(func.count(AIUsageEvent.id))
            .scalar() or 0
        )

        return {
            "totalCalls": int(totals[0] or 0),
            "successfulCalls": int(success_count),
            "fallbackCalls": int(fallback_count),
            "inputTokens": int(totals[1] or 0),
            "outputTokens": int(totals[2] or 0),
            "totalTokens": int(totals[3] or 0),
            "estimatedCostUsd": float(totals[4]) if totals[4] is not None else None,
            "pricedCalls": int(priced_count),
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
