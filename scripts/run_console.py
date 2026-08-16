#!/usr/bin/env python3
"""Serve the operational console — seeded book, no database.

    python scripts/run_console.py            →   http://127.0.0.1:8001
    python scripts/run_console.py --prod     →   the deployed shape

Sign in as Front office or Back office and drive the whole flow: look up a
policy, verify the caller, ask the agent, raise a case, approve it, watch the
ledger move.

**The agent runs live only if `ANTHROPIC_API_KEY` is set**, and the console says
which path answered either way. The key is read straight from the environment
(or a `.env` line) rather than through `load_config()`: the loader requires
every secret, so asking it for this one would stop an offline console booting
because a Supabase URL is missing (D-CL-053 contradiction 4).

**Production mode is the flag that decision left room for** (v4 phase 7). With
`--prod`, or `CALMLINE_ENV=production` as the host sets it, configuration is
loaded and validated *on the way up* and a missing variable stops the boot with
one error naming every one of them (rule 14). Development is untouched and still
boots on an empty environment — that was the point of D-CL-053, and a deployed
service limping half-configured until a caller trips over it was never it.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Mapping, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config, load_config  # noqa: E402
from src.records.seed import build_world_book  # noqa: E402
from src.records.world_seed import WorldSeedError  # noqa: E402
from src.web.console.app import create_console_app  # noqa: E402
from src.web.console.ratelimit import Allowance, RateLimiter  # noqa: E402

import os  # noqa: E402

import uvicorn  # noqa: E402

# The phase-6 hard gate's last line. A Render dashboard that forgets
# `ANTHROPIC_MODEL` falls back to this, so a committed default naming any other
# model is a deploy one omission away from spending on the wrong one.
DEFAULT_MODEL = "claude-haiku-4-5"
PRODUCTION = "production"

# AD-CL-008's spend rails, as numbers. 30 requests an hour is more than a
# reviewer clicking through the demo will ever use and far less than a script
# can spend; 500 a day is the one that bounds the bill — at Haiku's rates a
# fully-spent day is low single-digit dollars, not a surprise. Both are
# dashboard-overridable, because a rail nobody can adjust is a rail someone
# eventually deletes.
DEFAULT_PER_IP = 30
PER_IP_WINDOW = 60.0 * 60
DEFAULT_PER_DAY = 500
DAY = 60.0 * 60 * 24


def build_limiter(env: Mapping[str, str]) -> RateLimiter:
    """The deployed console's two allowances."""
    return RateLimiter(
        per_ip=Allowance(int(env.get("RATE_LIMIT_PER_IP") or DEFAULT_PER_IP),
                         PER_IP_WINDOW),
        overall=Allowance(int(env.get("RATE_LIMIT_PER_DAY") or DEFAULT_PER_DAY),
                          DAY))


def trusted_proxy_hops(env: Mapping[str, str]) -> int:
    """How many proxies sit in front of us, for reading X-Forwarded-For.

    **One in production**, because the documented deploy target puts exactly one
    proxy in front of the service. Left at zero there, every visitor arrives
    wearing the proxy's address and the per-IP cap quietly becomes a second
    global one. Overridable for a host that runs none.
    """
    override = (env.get("TRUSTED_PROXY_HOPS") or "").strip()
    if override:
        return int(override)
    return 1 if is_production(env) else 0


def is_production(env: Mapping[str, str]) -> bool:
    """Is this the deployed shape? Read from the host, never guessed."""
    return (env.get("CALMLINE_ENV") or "").strip().lower() == PRODUCTION


def preflight(env: Mapping[str, str]) -> Optional[Config]:
    """Validate configuration before serving, in production only.

    Returns the loaded ``Config`` in production, ``None`` in development — where
    nothing is validated at all, deliberately. Raises ``MissingConfigError``
    naming every missing or empty variable at once.

    ``env`` is read **exclusively**: on the host there is no `.env` file, and a
    check that could silently fall through to a developer's one would pass on
    the only machine where it does not matter.
    """
    if not is_production(env):
        return None
    return load_config(env)


def resolve_model(env: Mapping[str, str]) -> str:
    """The agent's model — the environment's, or the committed Haiku default."""
    return (env.get("ANTHROPIC_MODEL") or "").strip() or DEFAULT_MODEL


def _from_env(name: str) -> str:
    """``name`` from the process environment, falling back to a `.env` line.

    A variable that is **present but empty** wins outright and does not fall
    through. `ANTHROPIC_API_KEY= python scripts/run_console.py` is how you run
    the offline console, and until this distinction existed there was no way to
    do it without editing `.env` — which made the keyword path, a first-class
    product behaviour (D-CL-020), unreachable from the runner that exists to
    demonstrate the product.
    """
    if name in os.environ:
        return os.environ[name].strip()
    value = os.environ.get(name, "")
    if value:
        return value.strip()
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key, sep, rest = line.strip().partition("=")
            if sep and key == name:
                return rest.strip()
    return ""


def main(argv: Optional[list[str]] = None) -> int:
    # seed_demo=True populates the ops (and back-office) screens with a spread of
    # illustrative cases so the whole console is live on first login.
    env = dict(os.environ)
    if "--prod" in (argv if argv is not None else sys.argv[1:]):
        env["CALMLINE_ENV"] = PRODUCTION

    production = is_production(env)
    config_ok: Optional[bool] = None
    limiter: Optional[RateLimiter] = None
    if production:
        preflight(env)  # raises, naming every missing variable, before serving
        config_ok = True
        limiter = build_limiter(env)
        print(f"config OK — every required variable is present. "
              f"Rails: {limiter.per_ip.limit}/h per address, "
              f"{limiter.overall.limit}/day overall.")

    api_key = _from_env("ANTHROPIC_API_KEY")
    model = resolve_model({"ANTHROPIC_MODEL": _from_env("ANTHROPIC_MODEL")})

    # v4.5 phase 3 — the console serves **the world**: two hundred policies read
    # from committed files, not eighty invented at boot. A dataset that will not
    # load stops the console here rather than serving a book missing policies
    # nobody can identify.
    try:
        book = build_world_book()
        # The dataset's live queue (v4.5 phase 5): the same rows the loader
        # carries into Postgres, admitted under their own references so the
        # back-office screen and the database agree about what is open.
        from src.casework.world_cases import cases_from_queue
        from src.records.world_seed import read_queue

        queue_cases = cases_from_queue(read_queue())
    except WorldSeedError as error:
        print(f"the world will not load: {error}")
        return 1

    app = create_console_app(book=book, seed_demo=True,
                             queue_cases=queue_cases, api_key=api_key,
                             model=model, rate_limit=limiter,
                             config_ok=config_ok,
                             trusted_proxy_hops=trusted_proxy_hops(env))
    mode = f"LIVE agent — {model}" if api_key else "OFFLINE — keyword fallback"
    # PORT lets a second console run alongside the first — two sessions on this
    # repo at once is a real thing, and a hardcoded port makes the second fail
    # with a stack trace rather than a choice. 8001 stays the default.
    port = int(os.environ.get("PORT") or 8001)
    # The host binds the world; a laptop binds itself. Getting this backwards
    # either exposes a dev console or makes a deployed one unreachable.
    host = "0.0.0.0" if production else "127.0.0.1"  # noqa: S104
    print(f"CalmLine console ({mode}; {len(book.list_policies())} policies from "
          f"data/world) → http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
