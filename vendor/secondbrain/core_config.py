"""Environment config loader. Reads `.env` at repo root in development; in
production env vars come from the host (Railway / CI)."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    SUPABASE_URL: str
    SUPABASE_PROJECT_REF: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWKS_URL: str
    DATABASE_URL: str

    UPSTASH_REDIS_URL: str

    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: str

    GEMINI_API_KEY: str = ""
    COHERE_API_KEY: str = ""
    FIRECRAWL_API_KEY: str = ""

    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Cached accessor. Tests reset `_settings = None` via conftest."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
