"""``TraceRecord`` — the `06-RAGOPS:4.1` per-query trace.

One record per agent query, and the only thing the five metrics fold over. What
this type **refuses** to hold matters as much as what it holds: every metric is
a pure fold, so a field that can quietly be wrong is a dashboard that quietly
lies, and the fold has no way to notice.

Three constraints are enforced here rather than left to the caller:

* **mode and model_id agree.** The keyword path names no model, because naming
  one that never ran is the pretence the field exists to prevent; and a live
  answer must name the model that produced it, because an operator switches
  models to compare them and every metric takes a ``model_id`` filter
  (D-CL-061). An unsliced average over a mixed run describes no model that
  actually ran — the fabricated-number rule broken by averaging.
* **An abstention states its reason.** An unexplained abstention inflates
  ``abstention_rate`` with nothing behind it.
* **The reference grammars are the ones the records layer already defines.**
  Imported rather than restated, so there is one definition of what a ``CW-``
  looks like.

Three fields have **no producer anywhere in the codebase** and are left null
rather than given an invented source: ``resolved_intent`` (the KB points at a
Doc 5 §20 intent taxonomy CalmLine never built), ``feedback``, and ``handoff``
except where a case was actually raised.

``user_role`` carries CalmLine's own role strings rather than the KB's
[customer|agent|ops]: the repo wins on facts, and the session holds
`front_office` / `back_office` / `ops`.
"""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

# The routes a query can hand off to. `CW-` is a case the queue really minted;
# the rest are the KB's routes, kept as a vocabulary even though only `CW-` has
# a producer today (05-OPS:1.4 grammars, restated by CONTEXT.md).
_HANDOFF_RE = re.compile(r"^(none|CW-\d{9}|FC-\d{7}|CMP-\d{8}|VULN)$")

Mode = Literal["live", "keyword"]
UserRole = Literal["front_office", "back_office", "ops"]


class ChunkRef(BaseModel):
    """A chunk a trace names, and the version of it that was read.

    The pair is what ``stale_citation_rate`` folds over: a cited chunk whose
    version has since been bumped is a stale citation, and one that states no
    version cannot be judged either way.
    """

    chunk_id: str
    version: Optional[int] = None


class RetrievedChunk(ChunkRef):
    """A chunk retrieval returned, with where it placed."""

    score: Optional[float] = None
    rank: Optional[int] = None


class FiltersApplied(BaseModel):
    """What narrowed the search before ranking — retrieval is filter-then-search."""

    aud: Optional[str] = None
    doc: Optional[str] = None


class Abstained(BaseModel):
    """Whether the agent declined, and why.

    A success state, not an error (CONTEXT.md). The reason is required when the
    flag is set: ``abstention_rate`` is only meaningful alongside *why*, and
    ``correct_routing_rate`` asks whether the handoff that followed was right.
    """

    flag: bool = False
    reason: Optional[str] = None

    @model_validator(mode="after")
    def _an_abstention_states_its_reason(self) -> "Abstained":
        if self.flag and not (self.reason or "").strip():
            raise ValueError(
                "an abstention must state its reason — an unexplained one "
                "inflates abstention_rate with nothing behind it")
        return self


class LatencyMs(BaseModel):
    """Split, because the two halves fail differently and are fixed differently."""

    retrieve: Optional[int] = None
    generate: Optional[int] = None


class TraceRecord(BaseModel):
    """One agent query, as `06-RAGOPS:4.1` describes it."""

    trace_id: str
    # Every trace belongs to an interaction. Present from the start rather than
    # retrofitted, because AD-CL-037 scopes the conversation to the `CN-` and a
    # trace that could not name its interaction could not be queried by it.
    cn_ref: Optional[str] = None
    ts: str
    channel: str = "console"
    user_role: UserRole

    resolved_intent: Optional[str] = None
    filters_applied: FiltersApplied = Field(default_factory=FiltersApplied)
    retrieved: list[RetrievedChunk] = Field(default_factory=list)
    reranked: list[RetrievedChunk] = Field(default_factory=list)
    cited: list[ChunkRef] = Field(default_factory=list)

    answer_text: str = ""
    abstained: Abstained = Field(default_factory=Abstained)
    guardrail_events: list[str] = Field(default_factory=list)
    handoff: Optional[str] = None

    latency_ms: LatencyMs = Field(default_factory=LatencyMs)
    model_id: Optional[str] = None
    mode: Mode
    kb_version: Optional[str] = None
    feedback: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def _mode_and_model_agree(self) -> "TraceRecord":
        if self.mode == "keyword" and self.model_id:
            raise ValueError(
                f"the keyword path named {self.model_id!r}, but no model ran — "
                "naming one that did not is the pretence `mode` exists to prevent")
        if self.mode == "live" and not (self.model_id or "").strip():
            raise ValueError(
                "a live answer must name the model that produced it, or it "
                "cannot be told apart from another model's in the same store")
        return self

    @model_validator(mode="after")
    def _handoff_is_a_route(self) -> "TraceRecord":
        if self.handoff is not None and not _HANDOFF_RE.match(self.handoff):
            raise ValueError(
                f"handoff {self.handoff!r} is not a route: expected none, a "
                "CW-/FC-/CMP- reference, or VULN")
        return self
