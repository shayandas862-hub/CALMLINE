"""The single place every environment variable is read and validated.

Pydantic-settings pattern adapted from the vendored RAG config
(vendor/secondbrain/core_config.py): reads `.env` at the repo root in
development; in production (Render / CI) env vars come from the host.
Missing or empty required variables fail loudly at startup with ONE error
naming every missing variable, so a misconfigured deploy never limps on.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Secret-bearing variables with no safe default — must be provided.
REQUIRED = (
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "COHERE_API_KEY",
    "DATABASE_URL",
)


class MissingConfigError(RuntimeError):
    """Raised at startup when required environment variables are unset or empty."""


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
        frozen=True,
    )

    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: str
    COHERE_API_KEY: str
    DATABASE_URL: str

    # Non-secret config with committed defaults (env-overridable).
    # D-CL-024 Sonnet 5 is the agent default — near-Opus
    # quality on coding and agentic work at $3/$15 per MTok against Opus's
    # $5/$25. Env-overridable; phase 6's eval baseline is the empirical check.
    ANTHROPIC_MODEL: str = "claude-sonnet-5"
    JUDGE_MODEL: str = "claude-sonnet-5"

    @field_validator(*REQUIRED, mode="before")
    @classmethod
    def _empty_is_missing(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError("must not be empty")
        return value


class _MappingOnlyConfig(Config):
    """Hermetic variant: reads ONLY constructor kwargs — no env, no .env file.

    Used by load_config(env=...) so tests never leak the developer's shell.
    """

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):  # noqa: ANN001, ANN206 — pydantic-settings hook signature
        return (init_settings,)


def load_config(env: Mapping[str, str] | None = None) -> Config:
    """Read and validate configuration.

    With no argument, reads the process environment (plus `.env` at the repo
    root). Pass a mapping to load from it EXCLUSIVELY — hermetic for tests.
    """
    try:
        if env is None:
            return Config()
        return _MappingOnlyConfig(**dict(env))
    except ValidationError as exc:
        missing = sorted({str(error["loc"][0]) for error in exc.errors()})
        raise MissingConfigError(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill them in."
        ) from exc
