"""Wiring for a LIVE eval run — the one place in this repo that spends money.

Everything here is deliberate about two things.

**The registry holds `retrieve_clause` and nothing else.** The 44 golden cases
are questions about the rules (`06-RAGOPS §3`), not about any customer's record.
Handing the agent record tools it cannot satisfy — there is no verification in an
eval run — would make every one of them refuse, and a refused tool appends a
**guardrail event**. Tier G passes on a guardrail event. So the full registry
would have made every guardrail case pass for a reason that has nothing to do
with guardrails, and the headline safety number would have been meaningless and
perfect (D-CL-095).

**Retrieval returns five, not the console's three.** `recall@5` asks whether the
expected chunk was in the top five; a retriever capped at three cannot answer
that question, only `recall@3`. The eval measures the ranker at the k its own
metric names, and the console's k is recorded as the difference it is
(D-CL-096).

**The eval retriever is unbound by audience, and the console's is not.** The two
are asking different questions: the eval asks *can retrieval find the governing
clause in the corpus*, the console asks *may this handler see it*. Binding the
eval to `front_office` makes **26 of the 44 cases unanswerable by construction**
— Tier O expects `07-RUNBOOK` material that is `aud=ops`, Tier X is almost
entirely `back_office` — so the number it produces measures the audience filter
rather than the ranker. Found by running it bound and reading a Tier O recall of
0% (D-CL-098). Rule 11 is untouched: the audience is still a build-time decision
of the server's, never something a query can widen.

The model comes from the environment and is **asserted before a single call** —
a run that quietly used a different model than the one recorded is a baseline
that defends a number nobody measured.
"""

from __future__ import annotations

import os
from functools import partial
from pathlib import Path
from typing import Any, Callable, Optional

from src.agent.tools.knowledge_tool import retrieve_clause
from src.agent.tools.registry import Tool, ToolRegistry
from src.web.console.offline_agent import build_offline_retriever

# `recall@5` names its own k. See the module docstring.
EVAL_TOP_K = 5
# None = every audience. The eval audits the corpus; the console scopes a
# session. See the module docstring — binding this hid 26 of the 44 cases.
AUDIENCE: Optional[str] = None

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class LiveRunRefused(RuntimeError):
    """Raised before any call when the run is not the one that was asked for."""


def from_env(name: str, *, env: Optional[dict[str, str]] = None) -> str:
    """``name`` from the process environment, falling back to a `.env` line.

    A variable **present but empty wins outright** and does not fall through —
    `ANTHROPIC_API_KEY= python …` is how this repo runs offline, and D-CL-070
    records what it cost the last time that distinction was missing.
    """
    environ = os.environ if env is None else env
    if name in environ:
        return environ[name].strip()
    if env is not None or not _ENV_FILE.exists():
        return ""
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == name:
            return value.strip()
    return ""


def resolve_model(expected: str, *, env: Optional[dict[str, str]] = None) -> str:
    """The model this run will use, or refuse to start.

    ``expected`` is the model the operator has stated they intend to spend money
    on, and it is **required** — a live run that silently used a different model
    would record a baseline describing a model that never ran, which is the
    fabricated-number rule reached by drift rather than by invention.
    """
    if not (expected or "").strip():
        raise LiveRunRefused(
            "a live run must be pinned to a model with --model. Stating it out "
            "loud is what stops the baseline describing a model that never ran.")
    resolved = from_env("ANTHROPIC_MODEL", env=env)
    if not resolved:
        raise LiveRunRefused(
            "ANTHROPIC_MODEL is unset — nothing to check --model against.")
    if resolved != expected:
        raise LiveRunRefused(
            f"this run is pinned to {expected!r} but the environment resolves "
            f"{resolved!r}. Refusing to spend on a model the baseline would then "
            "misdescribe.")
    return resolved


def require_key(*, env: Optional[dict[str, str]] = None) -> str:
    """The API key, or a loud refusal naming what is missing (rule 14)."""
    key = from_env("ANTHROPIC_API_KEY", env=env)
    if not key:
        raise LiveRunRefused(
            "ANTHROPIC_API_KEY is empty or unset — a live run needs it. "
            "Use `--replay <run-id>` to score committed outputs offline instead.")
    return key


def eval_registry(*, top_k: int = EVAL_TOP_K,
                  aud: Optional[str] = AUDIENCE) -> ToolRegistry:
    """The tools a golden case may use: retrieval, and only retrieval."""
    retriever = build_offline_retriever(top_k=top_k, aud=aud)
    registry = ToolRegistry()
    registry.register(Tool(
        name="retrieve_clause",
        description="Search the Aldercrest knowledge base for the clauses that "
                    "govern a question. Returns clause ids and text, or nothing.",
        fn=partial(retrieve_clause, retriever),
    ))
    return registry


def anthropic_client(api_key: str) -> Any:
    """The real client, imported here so nothing offline ever needs the SDK."""
    import anthropic

    return anthropic.Anthropic(api_key=api_key)


class TokenMeter:
    """What a live run actually consumed, accumulated as it goes.

    Added because the first baseline run's cost had to be **estimated** — the
    runner made ~390 calls and recorded not one token, so the only figure
    available was a guess. Rule 7 says every number comes from real state, and a
    cost is a number: a run that cannot say what it spent is reporting a
    fabricated one however carefully it is hedged (D-CL-099).
    """

    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls = 0

    def record(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.calls += 1

    def totals(self) -> dict[str, int]:
        return {"input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "calls": self.calls}

    def cost_usd(self, *, input_per_mtok: float, output_per_mtok: float) -> float:
        """Spend at the given published rates. The rates are the caller's to state."""
        return (self.input_tokens / 1_000_000 * input_per_mtok
                + self.output_tokens / 1_000_000 * output_per_mtok)


def metered(client: Any, meter: TokenMeter) -> Any:
    """``client`` with every ``messages.create`` counted into ``meter``.

    A wrapper rather than a change to the loop: the loop's job is to answer a
    question, not to keep the books, and threading usage through it would put
    accounting in three files instead of one. A response carrying no ``usage``
    still counts as a call — bookkeeping must never take a run down.
    """
    inner = client.messages

    class _CountedMessages:
        def create(self, **kwargs: Any) -> Any:
            response = inner.create(**kwargs)
            usage = getattr(response, "usage", None)
            meter.record(int(getattr(usage, "input_tokens", 0) or 0),
                         int(getattr(usage, "output_tokens", 0) or 0))
            return response

    class _MeteredClient:
        messages = _CountedMessages()

        def __getattr__(self, name: str) -> Any:
            return getattr(client, name)

    return _MeteredClient()


def trace_ids(prefix: str) -> Callable[[int], str]:
    """Deterministic trace ids for a run — position, never a clock (rule 8)."""
    return lambda index: f"{prefix}-{index:03d}"
