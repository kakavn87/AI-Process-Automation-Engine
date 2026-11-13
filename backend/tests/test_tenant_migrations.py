from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import settings

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_CONFIG = BACKEND_ROOT / "alembic.ini"
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def run_migrations(database_url: str, target: str = "head", monkeypatch=None) -> None:
    if monkeypatch is not None:
        monkeypatch.setattr(settings, "IS_PULL_REQUEST", False)
        monkeypatch.setattr(settings, "DATABASE_URL", database_url)
    config = Config(str(ALEMBIC_CONFIG))
    command.upgrade(config, target)


def test_fresh_database_migrates_to_tenant_schema(tmp_path, monkeypatch):
    database_path = tmp_path / "fresh-flowpilot.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    run_migrations(database_url, monkeypatch=monkeypatch)

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {
            "alembic_version",
            "tenants",
            "users",
            "tenant_memberships",
            "tenant_invitations",
            "workflow_sessions",
            "approval_executions",
            "ai_usage_events",
        }.issubset(tables)
        for table_name in ("workflow_sessions", "approval_executions", "ai_usage_events"):
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            assert "tenant_id" in columns

        with engine.connect() as connection:
            tenant = connection.execute(
                text("SELECT id, slug FROM tenants WHERE id = :tenant_id"),
                {"tenant_id": DEFAULT_TENANT_ID},
            ).one()
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

        assert tenant.slug == "flowpilot-demo"
        assert revision == "0002_tenant_identity"
    finally:
        engine.dispose()


def test_existing_demo_database_keeps_workflow_rows_and_backfills_tenant(tmp_path, monkeypatch):
    database_path = tmp_path / "existing-flowpilot.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    # Install only the frozen pre-tenant schema and insert a legacy demo record.
    run_migrations(database_url, target="0001_initial_schema", monkeypatch=monkeypatch)
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO workflow_sessions (
                        id, description, analysis_strategy, language, business_domain,
                        analysis, questions, answers, status, events, related_execution_id
                    ) VALUES (
                        :id, :description, :strategy, :language, :domain,
                        :analysis, :questions, :answers, :status, :events, :related_id
                    )
                    """
                ),
                {
                    "id": "legacy-session-1",
                    "description": "Legacy demo workflow",
                    "strategy": "rules",
                    "language": "de",
                    "domain": "operations",
                    "analysis": "{}",
                    "questions": "[]",
                    "answers": "{}",
                    "status": "needs_input",
                    "events": "[]",
                    "related_id": None,
                },
            )
    finally:
        engine.dispose()

    run_migrations(database_url, target="head", monkeypatch=monkeypatch)

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT id, description, tenant_id FROM workflow_sessions "
                    "WHERE id = :session_id"
                ),
                {"session_id": "legacy-session-1"},
            ).one()
        assert row.id == "legacy-session-1"
        assert row.description == "Legacy demo workflow"
        assert row.tenant_id == DEFAULT_TENANT_ID
    finally:
        engine.dispose()
