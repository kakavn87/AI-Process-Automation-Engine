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
