"""v4 phase 7 · Task 1 — the entrypoint that refuses to limp into production.

`src/config.py` has raised one error naming every missing variable since v2
phase 1. **Nothing ever called it on the way up.** `run_console.py` deliberately
does not (D-CL-053 contradiction 4: requiring every secret would kill an offline
console because a Supabase URL is missing) — which was right for a dev runner
and leaves a deployed service free to boot half-configured and fail later, on a
caller's request, with a stack trace.

Production mode is the flag that decision left room for. It is **not** a reversal
of it: the offline path is asserted below to still boot on an empty environment.
"""

import pytest

from scripts.run_console import (DEFAULT_MODEL, DEFAULT_PER_DAY, DEFAULT_PER_IP,
                                 build_limiter, is_production, preflight,
                                 resolve_model, trusted_proxy_hops)
from src.config import MissingConfigError

COMPLETE = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_KEY": "svc",
    "ANTHROPIC_API_KEY": "ak",
    "OPENAI_API_KEY": "ok",
    "COHERE_API_KEY": "ck",
    "DATABASE_URL": "postgresql://localhost/x",
}


# ── which mode ─────────────────────────────────────────────────────────
def test_development_is_the_default():
    assert is_production({}) is False
    assert is_production({"CALMLINE_ENV": "development"}) is False


@pytest.mark.parametrize("value", ["production", "PRODUCTION", " production "])
def test_production_is_recognised_however_it_is_written(value):
    assert is_production({"CALMLINE_ENV": value}) is True


# ── the offline console still boots on nothing (D-CL-053 preserved) ────
def test_development_boots_with_an_entirely_empty_environment():
    """The whole point of D-CL-053. A dev runner that needs six secrets to show
    the keyword path is a dev runner nobody can run."""
    assert preflight({}) is None


def test_development_does_not_validate_even_a_half_filled_environment():
    assert preflight({"SUPABASE_URL": "https://example.supabase.co"}) is None


# ── production refuses to start half-configured ────────────────────────
def test_production_with_everything_present_returns_the_config():
    config = preflight({**COMPLETE, "CALMLINE_ENV": "production"})
    assert config is not None
    assert config.SUPABASE_URL == "https://example.supabase.co"


def test_production_names_every_missing_variable_at_once():
    """Rule 14. Naming one at a time means six deploys to find six mistakes."""
    partial = {k: v for k, v in COMPLETE.items()
               if k not in ("OPENAI_API_KEY", "COHERE_API_KEY", "DATABASE_URL")}
    with pytest.raises(MissingConfigError) as exc:
        preflight({**partial, "CALMLINE_ENV": "production"})
    message = str(exc.value)
    for name in ("OPENAI_API_KEY", "COHERE_API_KEY", "DATABASE_URL"):
        assert name in message


def test_a_present_but_empty_variable_counts_as_missing():
    """A dashboard field someone cleared looks exactly like one never filled."""
    with pytest.raises(MissingConfigError) as exc:
        preflight({**COMPLETE, "ANTHROPIC_API_KEY": "   ",
                   "CALMLINE_ENV": "production"})
    assert "ANTHROPIC_API_KEY" in str(exc.value)


def test_production_does_not_demand_the_model_variables():
    """They carry committed defaults; demanding them would fail a correct deploy."""
    assert preflight({**COMPLETE, "CALMLINE_ENV": "production"}) is not None


# ── the hard gate, at the one place a deploy can break it ──────────────
def test_the_committed_default_model_is_haiku():
    """A Render dashboard that forgets ANTHROPIC_MODEL falls back to this, so
    the committed default is the last line of the phase-6 hard gate."""
    assert DEFAULT_MODEL == "claude-haiku-4-5"


def test_the_environment_still_wins_over_the_default():
    assert resolve_model({"ANTHROPIC_MODEL": "claude-haiku-4-5"}) == "claude-haiku-4-5"
    assert resolve_model({}) == DEFAULT_MODEL
    assert resolve_model({"ANTHROPIC_MODEL": "  "}) == DEFAULT_MODEL


# ── the caps the deploy actually runs with ─────────────────────────────
def test_the_caps_are_tunable_from_the_dashboard_without_a_deploy():
    """A rail nobody can adjust is a rail someone eventually removes."""
    limiter = build_limiter({"RATE_LIMIT_PER_IP": "7", "RATE_LIMIT_PER_DAY": "70"})
    assert limiter.per_ip.limit == 7
    assert limiter.overall.limit == 70


def test_the_caps_have_committed_defaults():
    limiter = build_limiter({})
    assert limiter.per_ip.limit == DEFAULT_PER_IP
    assert limiter.overall.limit == DEFAULT_PER_DAY
    assert limiter.overall.window_seconds == 86_400


def test_the_daily_cap_bounds_the_days_spend_to_something_survivable():
    """The number that matters: worst-case daily spend against one key."""
    assert build_limiter({}).overall.limit <= 1000


def test_production_trusts_exactly_one_proxy_because_render_runs_one():
    """Left at zero behind Render's proxy, every visitor shares one address and
    the per-IP cap silently becomes a second global one."""
    assert trusted_proxy_hops({"CALMLINE_ENV": "production"}) == 1


def test_development_trusts_no_proxy():
    assert trusted_proxy_hops({}) == 0


def test_the_hop_count_is_overridable_for_a_host_that_runs_none():
    assert trusted_proxy_hops({"CALMLINE_ENV": "production",
                               "TRUSTED_PROXY_HOPS": "0"}) == 0
