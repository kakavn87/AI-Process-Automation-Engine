import pytest

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from app.core.database import Base
from app.services.execution_service import ExecutionService


def make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine, Session(engine)


def test_execution_waits_for_approval_and_approves_once():
    engine, session = make_session()
    try:
        service = ExecutionService(session)
        result = service.create({
            "name": "Weekly report",
            "trigger": "Every Monday",
            "steps": [
                {"id": "s1", "type": "trigger", "name": "Start", "description": "Start weekly run.", "config": {}},
                {"id": "s2", "type": "notify", "name": "Notify Teams", "description": "Send report.", "config": {}},
            ],
        })

        assert result["status"] == "awaiting_approval"
        step_types = [step["type"] for step in result["steps"]]
        assert step_types.index("approval") < step_types.index("notify")
        assert result["steps"][step_types.index("approval")]["status"] == "awaiting_approval"

        approved = service.approve(result["id"], "Reviewed the draft.")
        assert approved["status"] == "approved_ready"
        assert approved["decisionNote"] == "Reviewed the draft."
        assert next(step for step in approved["steps"] if step["type"] == "approval")["status"] == "approved"

        with pytest.raises(RuntimeError):
            service.reject(result["id"], "Too late")
    finally:
        session.close()
        engine.dispose()


def test_execution_can_be_rejected():
    engine, session = make_session()
    try:
        service = ExecutionService(session)
        result = service.create({
            "name": "Document process",
            "steps": [
                {"id": "s1", "type": "extract", "name": "Extract", "description": "Extract data.", "config": {}},
            ],
        })
        rejected = service.reject(result["id"], "The validation rules are incomplete.")
        assert rejected["status"] == "rejected"
        assert rejected["decisionNote"] == "The validation rules are incomplete."
        assert all(step["status"] in {"cancelled", "rejected"} for step in rejected["steps"])
    finally:
        session.close()
        engine.dispose()
