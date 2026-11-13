from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.processes import router as processes_router
from app.api.routes.workflow_sessions import router as workflow_sessions_router
from app.core.config import settings
from app.core.database import Base, get_db
from app.models.execution import ApprovalExecution  # noqa: F401 - register all workflow tables
from app.models.workflow_session import AIUsageEvent, WorkflowSession  # noqa: F401
from app.services.process_service import ProcessService


def test_document_metadata_is_available_after_reloading_workflow_session(monkeypatch):
    monkeypatch.setattr(settings, "RAG_ENABLED", False)
    monkeypatch.setattr(settings, "QDRANT_URL", "")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")

    def fake_analyze(self, description, strategy, language, business_domain, image_data_urls=None):
        return {
            "questions": ["Which team owns this process?"],
            "proposedWorkflow": {"name": "Document process", "trigger": "Manual", "steps": []},
            "description": description,
            "llmUsed": False,
        }

    monkeypatch.setattr(ProcessService, "analyze", fake_analyze)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(processes_router)
    app.include_router(workflow_sessions_router)

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/processes/analyze-with-documents",
                data={"analysis_strategy": "rules", "analysis_language": "en"},
                files={"files": ("workflow.txt", b"Receive request and route it to the owning team.", "text/plain")},
            )
            assert response.status_code == 200, response.text
            result = response.json()
            session_id = result["processSessionId"]

            assert result["sourceDocuments"][0]["filename"] == "workflow.txt"
            assert result["documentWarnings"] == []

            reloaded = client.get(f"/processes/sessions/{session_id}")
            assert reloaded.status_code == 200
            session_analysis = reloaded.json()["analysis"]
            assert session_analysis["sourceDocuments"][0]["filename"] == "workflow.txt"
            assert session_analysis["documentWarnings"] == []
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
