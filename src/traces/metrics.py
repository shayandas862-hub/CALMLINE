"""The five KB metrics (`06-RAGOPS:4.2`), each a pure fold over stored traces.

Nothing here reads a clock, a database or a config. A metric takes records and
returns a number, so any figure on the ops screen can be reproduced by handing
the same records back. Windowing belongs to the store's ``query(since=, until=)``
— keeping the clock in one place is what makes these folds deterministic.

Three things this module is deliberate about:

**A rate over nothing is not zero.** Every ``Metric`` carries the ``basis`` it
folded over, and a rate with no basis is ``None``, not ``0.0``. A tile that
renders 0% on an empty store is a tile that looks best on the day it knows
least.

**Model slicing is honest about where it does not apply.** Four of the five take
a ``model_id`` filter (D-CL-061): an operator swaps models to compare them on
the same questions, and an unsliced average over a mixed run describes no model
that actually ran — the fabricated-number rule broken by averaging rather than
by invention. An unfiltered metric therefore names every model behind it rather
than picking one. **Gate-bypass takes no filter at all**: the identity gate runs
at the endpoint, before any model is reached, so a disclosure without a
verification is a property of the gate. Accepting a ``model_id`` there and
ignoring it would be a worse lie than not offering it.

**Targets are facts about a metric, not configuration.** ``containment`` carries
``target=None`` and ``tracked_never_targeted=True`` structurally, because E43
answers "should the AI aim to contain more contacts?" with a flat no — the
absence is the KB's position, not a value someone forgot to set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence

from src.traces.schema import TraceRecord

_ADVICE_BOUNDARY = "advice-boundary"


@dataclass(frozen=True)
class Metric:
    """One number, and everything needed to read it honestly."""

    name: str
    value: Optional[float]
    #: ``"count"`` or ``"rate"``. Stated rather than inferred: a rate of 0.0 and
    #: a count of 0 are the same float, and a renderer guessing between them
    #: shows "0" where it means "0%". The metric knows which it is; nothing
    #: downstream should have to work it out.
    unit: str = "count"
    #: What the KB requires. ``None`` means no target EXISTS — see
    #: ``tracked_never_targeted`` to tell that apart from one not yet set.
    target: Optional[float] = None
    #: How many things were folded. A rate with basis 0 has value ``None``.
    basis: int = 0
    #: The model this describes, when filtered to one.
    model_id: Optional[str] = None
    #: Every model behind the number when it is NOT filtered — so a mixed
    #: average can never be read as one model's result.
    models: tuple[str, ...] = ()
    #: True only where the KB says a target must not exist (E43).
    tracked_never_targeted: bool = False


def _sliced(traces: Iterable[TraceRecord],
            model_id: Optional[str]) -> list[TraceRecord]:
    """The traces this metric describes — all of them, or one model's."""
    records = list(traces)
    if model_id is None:
        return records
    return [t for t in records if t.model_id == model_id]


def _models_behind(traces: Sequence[TraceRecord]) -> tuple[str, ...]:
    """Every model named by these traces, sorted.

    The keyword path names none, so it contributes nothing here rather than an
    empty string — an absence, not a model called "".
    """
    return tuple(sorted({t.model_id for t in traces if t.model_id}))


def _rate(name: str, hits: int, basis: int, *, target: Optional[float],
          model_id: Optional[str], traces: Sequence[TraceRecord],
          **extra: Any) -> Metric:
    """A share, or ``None`` when there was nothing to take a share of."""
    return Metric(name=name,
                  value=(hits / basis) if basis else None,
                  unit="rate",
                  target=target, basis=basis, model_id=model_id,
                  models=_models_behind(traces), **extra)


# ── 1 · gate bypass ────────────────────────────────────────────────────

def gate_bypass_count(events: Any) -> Metric:
    """Disclosures with no in-scope passed verification behind them. Target 0.

    Delegates the join to ``GateEventLog.disclosures_without_pass``, which
    already decides the hard part: scope is ``(cn_ref, policy_no)`` and order
    matters, so a pass recorded *after* the disclosure is a bypass with tidy
    paperwork. Re-deriving that here would give the ops screen a second opinion
    about the same events, and two opinions is one too many.

    Takes no ``model_id``: the gate runs before any model, so there is nothing
    to attribute (see the module docstring).
    """
    return Metric(name="gate_bypass_count",
                  value=float(events.bypass_count()),
                  target=0,
                  basis=len(events.events()))


# ── 2 · advice-boundary violations ─────────────────────────────────────

def advice_boundary_violations(traces: Iterable[TraceRecord], *,
                               model_id: Optional[str] = None) -> Metric:
    """Guardrail events where the agent crossed into advice. Target 0.

    Counts *events*, not traces: one answer that gave advice twice broke the
    boundary twice, and collapsing that to "one bad answer" would understate it.
    """
    records = _sliced(traces, model_id)
    hits = sum(1 for t in records for e in t.guardrail_events
               if _ADVICE_BOUNDARY in e)
    return Metric(name="advice_boundary_violations", value=float(hits),
                  target=0, basis=len(records), model_id=model_id,
                  models=_models_behind(records))


# ── 3 · stale citations ────────────────────────────────────────────────

def stale_citation_rate(traces: Iterable[TraceRecord], *,
                        current_versions: Mapping[str, int],
                        tombstoned: Optional[Any] = None,
                        model_id: Optional[str] = None) -> Metric:
    """Share of citations that no longer point at what they claimed. Target 0.

    Computable only because task 0 carries ``version`` from ``KbChunk`` through
    to the citation; before that there was nothing to compare.

    A citation is stale when any of these hold, and the reasoning for each is
    the same — can a reader still follow it to what the answer relied on?

    * its chunk has been **tombstoned** (superseded), however current the
      version it names;
    * its chunk has been **re-embedded since** — the wording moved on and the
      answer did not;
    * it **states no version at all**, so it cannot be shown to be current.
      Counting that as fresh would report 0% stale on exactly the traces that
      lost their provenance;
    * the corpus **no longer holds the chunk**, which is a citation nobody can
      follow at all.

    The rate is over **citations**, not traces: one answer citing four clauses
    can be three-quarters stale, and per-trace counting cannot say that.
    """
    records = _sliced(traces, model_id)
    dead = set(tombstoned or ())
    cited = [c for t in records for c in t.cited]
    stale = sum(1 for c in cited if _is_stale(c, current_versions, dead))
    return _rate("stale_citation_rate", stale, len(cited), target=0,
                 model_id=model_id, traces=records)


def _is_stale(citation: Any, current: Mapping[str, int], dead: set) -> bool:
    if citation.chunk_id in dead:
        return True
    if citation.version is None:
        return True
    live = current.get(citation.chunk_id)
    return live is None or citation.version < live


# ── 4 · abstention, and whether it went anywhere ───────────────────────

def abstention_rate(traces: Iterable[TraceRecord], *,
                    model_id: Optional[str] = None) -> Metric:
    """Share of answers the agent declined to give.

    No target. A high rate is not automatically bad and a low one is not
    automatically good — abstention is a success state (CONTEXT.md), and what
    makes it good is ``correct_routing_rate`` alongside it.
    """
    records = _sliced(traces, model_id)
    declined = sum(1 for t in records if t.abstained.flag)
    return _rate("abstention_rate", declined, len(records), target=None,
                 model_id=model_id, traces=records)


def correct_routing_rate(traces: Iterable[TraceRecord], *,
                         model_id: Optional[str] = None) -> Metric:
    """Of the answers that abstained, the share that were handed somewhere.

    Folded over abstentions only — an answer that never abstained had nothing
    to route, and counting it as correctly routed would inflate the number with
    traffic that never faced the decision (07-RUNBOOK:8.5–8.6).
    """
    records = _sliced(traces, model_id)
    declined = [t for t in records if t.abstained.flag]
    routed = sum(1 for t in declined if t.handoff and t.handoff != "none")
    return _rate("correct_routing_rate", routed, len(declined), target=None,
                 model_id=model_id, traces=records)


# ── 5 · containment ────────────────────────────────────────────────────

def containment(traces: Iterable[TraceRecord], *,
                model_id: Optional[str] = None) -> Metric:
    """Share of queries the agent handled without handing off.

    **Tracked, never targeted.** E43 asks "should the AI aim to contain more
    contacts?" and answers no — measure routing and quality instead. The missing
    target is the KB's position, carried structurally so a screen cannot render
    it as a goal that nobody configured.
    """
    records = _sliced(traces, model_id)
    kept = sum(1 for t in records
               if not (t.handoff and t.handoff != "none") and not t.abstained.flag)
    return _rate("containment", kept, len(records), target=None,
                 model_id=model_id, traces=records,
                 tracked_never_targeted=True)
