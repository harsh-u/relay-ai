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

    embedding_model_dir: str = "models/indic-sentence-bert-nli-int8"
    embedding_similarity_threshold: float = 0.75

    knowledge_cache_ttl_days: int = 30
    conversation_message_ttl_hours: int = 48

    session_secret_key: str = "dev-only-insecure-session-secret-change-me"
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    beta_allowlist_emails: str = ""

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
