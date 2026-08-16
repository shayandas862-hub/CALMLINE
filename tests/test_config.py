"""Config loading must fail loudly, naming every missing variable at once.

Tests are hermetic: `load_config(env=...)` reads ONLY the given mapping —
whatever the developer's shell exports must not leak in.
"""

import pytest

from src.config import Config, MissingConfigError, load_config

COMPLETE_ENV = {
    "SUPABASE_URL": "https://demo.supabase.co",
    "SUPABASE_SERVICE_KEY": "service-key-value",
    "ANTHROPIC_API_KEY": "anthropic-demo-key",
    "OPENAI_API_KEY": "openai-demo-key",
    "COHERE_API_KEY": "cohere-demo-key",
    "DATABASE_URL": "postgresql://demo:demo@db.demo.supabase.co:5432/postgres",
}


def test_loads_complete_env_into_config():
    # Act
    cfg = load_config(env=dict(COMPLETE_ENV))

    # Assert
    assert isinstance(cfg, Config)
    assert cfg.SUPABASE_URL == "https://demo.supabase.co"
    assert cfg.SUPABASE_SERVICE_KEY == "service-key-value"
    assert cfg.ANTHROPIC_API_KEY == "anthropic-demo-key"
    assert cfg.OPENAI_API_KEY == "openai-demo-key"
    assert cfg.COHERE_API_KEY == "cohere-demo-key"
    assert cfg.DATABASE_URL.startswith("postgresql://")


def test_missing_variable_raises_naming_it():
    # Arrange
    env = {k: v for k, v in COMPLETE_ENV.items() if k != "OPENAI_API_KEY"}

    # Act / Assert
    with pytest.raises(MissingConfigError, match="OPENAI_API_KEY"):
        load_config(env=env)


def test_all_missing_variables_are_named_in_one_error():
    # Arrange — drop three at once; the error must name all three together
    env = {
        k: v
        for k, v in COMPLETE_ENV.items()
        if k not in ("OPENAI_API_KEY", "COHERE_API_KEY", "DATABASE_URL")
    }

    # Act
    with pytest.raises(MissingConfigError) as excinfo:
        load_config(env=env)

    # Assert — one loud error, every missing name present
    message = str(excinfo.value)
    for name in ("OPENAI_API_KEY", "COHERE_API_KEY", "DATABASE_URL"):
        assert name in message


def test_empty_string_is_treated_as_missing():
    # Arrange
    env = dict(COMPLETE_ENV, SUPABASE_URL="   ")

    # Act / Assert
    with pytest.raises(MissingConfigError, match="SUPABASE_URL"):
        load_config(env=env)


def test_model_ids_default_when_unset():
    # D-CL-024 the agent defaults to Sonnet 5 — near-Opus
    # quality on coding and agentic work at $3/$15 per MTok against Opus's
    # $5/$25. The phase-6 eval baseline is the empirical check on that choice.
    cfg = load_config(env=dict(COMPLETE_ENV))
    assert cfg.ANTHROPIC_MODEL == "claude-sonnet-5"
    assert cfg.JUDGE_MODEL == "claude-sonnet-5"


def test_model_ids_are_overridable():
    env = dict(COMPLETE_ENV, ANTHROPIC_MODEL="claude-sonnet-5", JUDGE_MODEL="claude-haiku-4-5")
    cfg = load_config(env=env)
    assert cfg.ANTHROPIC_MODEL == "claude-sonnet-5"
    assert cfg.JUDGE_MODEL == "claude-haiku-4-5"


def test_mapping_mode_is_hermetic(monkeypatch):
    # Arrange — a var present in the process env but NOT in the mapping must
    # not leak into mapping-mode loading.
    monkeypatch.setenv("OPENAI_API_KEY", "leaked-from-shell")
    env = {k: v for k, v in COMPLETE_ENV.items() if k != "OPENAI_API_KEY"}

    # Act / Assert — still missing, despite the shell export
    with pytest.raises(MissingConfigError, match="OPENAI_API_KEY"):
        load_config(env=env)


def test_config_is_frozen():
    cfg = load_config(env=dict(COMPLETE_ENV))
    with pytest.raises(Exception):
        cfg.ANTHROPIC_API_KEY = "mutated"  # type: ignore[misc]
