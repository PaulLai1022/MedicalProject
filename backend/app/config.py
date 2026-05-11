"""Application configuration — loaded from env vars / .env via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global settings; every field can be overridden by an env var of the same name."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "deepseek-v4-flash"
    llm_log_enabled: bool = True
    # Whether to use json_schema strict mode. Default is False because most
    # OpenAI-compatible endpoints we target (DeepSeek in particular) reject
    # `response_format: json_schema` with 400, causing a wasted round-trip per
    # call. Set to True only on endpoints that advertise strict json_schema
    # support (e.g. OpenAI GPT-4o, Azure OpenAI newer models). Even when True,
    # the client falls back to json_object at runtime on the first 400.
    llm_use_strict_schema: bool = False

    # JWT
    jwt_secret: str = "change-me-to-a-random-32-byte-string"
    jwt_expire_minutes: int = 1440

    # CORS
    frontend_origin: str = "http://localhost:5173"

    # Database
    database_url: str = "sqlite:///./data/app.db"

    # Logging
    log_level: str = "INFO"

    # Seed
    seed_demo: bool = True


def get_settings() -> Settings:
    """Return the global Settings singleton (injectable via FastAPI Depends)."""
    return Settings()
