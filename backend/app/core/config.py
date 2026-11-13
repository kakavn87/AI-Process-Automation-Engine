from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Engine"
    DATABASE_URL: str = "sqlite:///./process_automation.db"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-6-luna"
    OPENAI_INPUT_USD_PER_1M: float | None = None
    OPENAI_OUTPUT_USD_PER_1M: float | None = None
    CORS_ORIGINS: str = "http://localhost:4200"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
