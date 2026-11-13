import re

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Process Optimierung"
    DATABASE_URL: str = "sqlite:///./process_automation.db"
    PREVIEW_DATABASE_URL: str = ""
    OPENAI_API_KEY: str = ""
    PREVIEW_OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-6-luna"
    OPENAI_INPUT_USD_PER_1M: float | None = None
    OPENAI_OUTPUT_USD_PER_1M: float | None = None
    WEBHOOK_EXECUTION_ENABLED: bool = False
    WORKFLOW_WEBHOOK_URL: str = ""
    WORKFLOW_WEBHOOK_BEARER_TOKEN: str = ""
    WORKFLOW_LIVE_EXECUTION_TOKEN: str = ""
    WORKFLOW_WEBHOOK_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0, le=60)
    CORS_ORIGINS: str = "http://localhost:4200"
    IS_PULL_REQUEST: bool = False
    RENDER_EXTERNAL_HOSTNAME: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("OPENAI_INPUT_USD_PER_1M", "OPENAI_OUTPUT_USD_PER_1M", mode="before")
    @classmethod
    def empty_price_is_unconfigured(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def isolate_preview_credentials(self):
        # Render copies base-service environment variables into service previews.
        # Never let a PR preview silently consume the Production OpenAI key.
        if self.IS_PULL_REQUEST:
            self.OPENAI_API_KEY = self.PREVIEW_OPENAI_API_KEY.strip()
            # PR previews must never inherit a Production webhook destination or token.
            self.WEBHOOK_EXECUTION_ENABLED = False
            self.WORKFLOW_WEBHOOK_URL = ""
            self.WORKFLOW_WEBHOOK_BEARER_TOKEN = ""
            self.WORKFLOW_LIVE_EXECUTION_TOKEN = ""
        return self

    @property
    def effective_database_url(self) -> str:
        if not self.IS_PULL_REQUEST:
            return self.DATABASE_URL

        if self.PREVIEW_DATABASE_URL.strip():
            return self.PREVIEW_DATABASE_URL.strip()

        # The current Render service uses SQLite without a persistent disk.
        # A preview gets its own service filesystem, so use a distinct local file.
        if self.DATABASE_URL.strip().startswith("sqlite:///"):
            return "sqlite:///./process_automation_preview.db"

        # Do not copy a remote Production database URL into a preview.
        raise ValueError(
            "This pull-request preview needs PREVIEW_DATABASE_URL. "
            "Refusing to connect to the Production DATABASE_URL."
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def preview_cors_origin_regex(self) -> str | None:
        if not self.IS_PULL_REQUEST:
            return None

        # Render service preview URLs follow <service>-pr-<number>.onrender.com.
        # Pair this backend preview only with the frontend preview for the same PR.
        backend_host = self.RENDER_EXTERNAL_HOSTNAME.strip().lower()
        match = re.fullmatch(
            r"ai-process-automation-backend-4bsh(-pr-[0-9]+)\.onrender\.com",
            backend_host,
        )
        if not match:
            return None

        suffix = re.escape(match.group(1))
        return (
            rf"^https://ai-process-automation-frontend-4bsh{suffix}\.onrender\.com$"
        )


settings = Settings()
