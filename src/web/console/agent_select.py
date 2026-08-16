"""Which agent answers this request — and saying which one honestly.

The console runs offline by default and live when a key is configured. Both are
legitimate; presenting one as the other is not. A keyword answer displayed as
the real agent would misrepresent the product in the one direction that
flatters it, so the choice is returned as data the endpoint reports rather than
as a silent branch.

The key is **injected**, never read through ``load_config()``. `ANTHROPIC_API_KEY`
is in `config.REQUIRED`, so the loader raises naming *every* missing variable —
a console with no `.env` would die on `SUPABASE_URL` long before reaching the
key check (D-CL-053 contradiction 4). Selection stays a pure decision over the
values it is handed: no I/O, no environment, nothing to stub in a test.

`KeywordModel` is demoted here, never deleted (D-CL-020). It is what makes the
offline demo work, and it is the honest floor the product degrades to.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

LIVE = "live"
KEYWORD = "keyword"

_LIVE_REASON = "answered by the agent"
_KEYWORD_REASON = (
    "answered by the offline keyword fallback — no Anthropic API key is configured"
)


@dataclass(frozen=True)
class AgentChoice:
    """Which path answers, and what to show the handler about it."""

    mode: str
    model: Optional[str]
    reason: str

    @property
    def live(self) -> bool:
        return self.mode == LIVE


def select_agent(*, api_key: Optional[str], model: str) -> AgentChoice:
    """Pick the live loop when a key is configured, else the keyword fallback.

    An exported-but-blank variable is the commonest way to hold "a key" that
    cannot authenticate anything, so whitespace does not count as configured.
    """
    if api_key and api_key.strip():
        return AgentChoice(mode=LIVE, model=model, reason=_LIVE_REASON)
    # No model is named on this path: naming one that never ran is the pretence
    # this module exists to prevent.
    return AgentChoice(mode=KEYWORD, model=None, reason=_KEYWORD_REASON)
