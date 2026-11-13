import re

import pytest

from app.core.config import Settings


def test_pull_request_preview_uses_a_separate_sqlite_file():
    settings = Settings(
        _env_file=None,
        IS_PULL_REQUEST=True,
        DATABASE_URL="sqlite:///./process_automation.db",
    )

    assert settings.effective_database_url == "sqlite:///./process_automation_preview.db"


def test_pull_request_preview_refuses_a_remote_production_database():
    settings = Settings(
        _env_file=None,
        IS_PULL_REQUEST=True,
        DATABASE_URL="postgresql+psycopg://production.example/database",
    )

    with pytest.raises(ValueError, match="PREVIEW_DATABASE_URL"):
        _ = settings.effective_database_url


def test_pull_request_preview_can_use_an_explicit_preview_database():
    settings = Settings(
        _env_file=None,
        IS_PULL_REQUEST=True,
        DATABASE_URL="postgresql+psycopg://production.example/database",
        PREVIEW_DATABASE_URL="postgresql+psycopg://preview.example/database",
    )

    assert settings.effective_database_url == "postgresql+psycopg://preview.example/database"


def test_preview_cors_only_allows_the_frontend_for_the_same_pull_request():
    settings = Settings(
        _env_file=None,
        IS_PULL_REQUEST=True,
        RENDER_EXTERNAL_HOSTNAME="ai-process-automation-backend-4bsh-pr-5.onrender.com",
    )

    pattern = settings.preview_cors_origin_regex
    assert pattern is not None
    assert re.fullmatch(pattern, "https://ai-process-automation-frontend-4bsh-pr-5.onrender.com")
    assert not re.fullmatch(pattern, "https://ai-process-automation-frontend-4bsh.onrender.com")
    assert not re.fullmatch(pattern, "https://another-site.onrender.com")


def test_preview_never_uses_the_production_openai_key():
    settings = Settings(
        _env_file=None,
        IS_PULL_REQUEST=True,
        OPENAI_API_KEY="production-key",
        PREVIEW_OPENAI_API_KEY="",
    )

    assert settings.OPENAI_API_KEY == ""


def test_preview_can_use_an_explicit_test_openai_key():
    settings = Settings(
        _env_file=None,
        IS_PULL_REQUEST=True,
        OPENAI_API_KEY="production-key",
        PREVIEW_OPENAI_API_KEY="preview-key",
    )

    assert settings.OPENAI_API_KEY == "preview-key"

def test_pull_request_preview_never_inherits_production_rag_or_qdrant():
    settings = Settings(
        _env_file=None,
        IS_PULL_REQUEST=True,
        RAG_ENABLED=True,
        QDRANT_URL="https://production-qdrant.example",
        QDRANT_API_KEY="production-qdrant-secret",
    )

    assert settings.RAG_ENABLED is False
    assert settings.QDRANT_URL == ""
    assert settings.QDRANT_API_KEY == ""


def test_postgres_urls_are_normalized_for_psycopg_v3():
    standard = Settings(
        _env_file=None,
        DATABASE_URL="postgres://flowpilot:secret@db.example.com:5432/flowpilot",
    )
    sqlalchemy_url = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://flowpilot:secret@db.example.com:5432/flowpilot",
    )
    explicit = Settings(
        _env_file=None,
        DATABASE_URL="postgresql+psycopg://flowpilot:secret@db.example.com:5432/flowpilot",
    )

    assert standard.sqlalchemy_database_url == (
        "postgresql+psycopg://flowpilot:secret@db.example.com:5432/flowpilot"
    )
    assert sqlalchemy_url.sqlalchemy_database_url == (
        "postgresql+psycopg://flowpilot:secret@db.example.com:5432/flowpilot"
    )
    assert explicit.sqlalchemy_database_url == (
        "postgresql+psycopg://flowpilot:secret@db.example.com:5432/flowpilot"
    )


def test_preview_postgres_url_is_normalized_without_using_production_database():
    settings = Settings(
        _env_file=None,
        IS_PULL_REQUEST=True,
        DATABASE_URL="postgres://production:secret@db.example.com/production",
        PREVIEW_DATABASE_URL="postgres://preview:secret@db.example.com/preview",
    )

    assert settings.sqlalchemy_database_url == (
        "postgresql+psycopg://preview:secret@db.example.com/preview"
    )


def test_authentication_is_disabled_by_default():
    settings = Settings(_env_file=None)
    assert settings.AUTH_ENABLED is False


def test_authentication_requires_a_long_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(
            _env_file=None,
            AUTH_ENABLED=True,
            JWT_SECRET_KEY="short-secret",
        )


def test_pull_request_preview_never_inherits_production_authentication_secrets():
    settings = Settings(
        _env_file=None,
        IS_PULL_REQUEST=True,
        AUTH_ENABLED=True,
        JWT_SECRET_KEY="production-signing-secret-with-more-than-32-characters",
        BOOTSTRAP_ADMIN_EMAIL="admin@example.com",
        BOOTSTRAP_ADMIN_PASSWORD="Production-Password-12!",
    )

    assert settings.AUTH_ENABLED is False
    assert settings.JWT_SECRET_KEY == ""
    assert settings.BOOTSTRAP_ADMIN_EMAIL == ""
    assert settings.BOOTSTRAP_ADMIN_PASSWORD == ""
