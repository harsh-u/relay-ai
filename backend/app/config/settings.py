from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "RelayAI"
    app_env: str = "development"
    log_level: str = "INFO"

    api_v1_prefix: str = "/v1"

    database_url: str = "postgresql+asyncpg://relayai:relayai@localhost:5432/relayai"
    redis_url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()
