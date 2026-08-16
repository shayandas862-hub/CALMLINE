"""The three ops lenses — read-models over the traces, the gate log and the book.

The v3 screen answered *"how is the queue doing"*. This one answers **"is the AI
behaving"**, which is a different question with different failure modes. Two
lenses were replaced; Operations survived, because the queue and ledger numbers
were honest and the reconciliation self-check is the one figure that checks the
store against itself.

Every number is a fold over real state — stored traces, phase 3's gate events,
the ledgers, the cases. Nothing is invented, and ``now`` is injected, never the
wall clock.

**Each lens names the model(s) behind its numbers, and can be filtered to one.**
An operator swaps models to compare them on the same questions (D-CL-061), so a
screen that silently mixes two is the fabricated-number rule broken by averaging
rather than by invention. An unfiltered lens therefore reports every model it
folded over rather than picking one to name.

A rate with nothing behind it reports ``None`` and its basis, never ``0.0``. The
tile that reads perfectly on an empty store is the one that misleads hardest.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping, Optional

from src.casework.models import Case, priority_rank, sla_seconds_left
from src.traces.metrics import (
    Metric,
    abstention_rate,
    advice_boundary_violations,
    containment,
    correct_routing_rate,
    gate_bypass_count,
    stale_citation_rate,
)

_PRIORITIES = ("high", "medium", "low")


def _has_event(case: Case, event: str) -> bool:
    return any(a.get("event") == event for a in case.audit)


def _is_overdue(case: Case, now: str) -> bool:
    left = sla_seconds_left(case, now)
    return left is not None and left < 0


def _tile(metric: Metric) -> dict[str, Any]:
    """A metric as the screen reads it — value, target, and what it folded over.

    ``basis`` travels with every tile so a renderer can tell "0% stale" from
    "nothing cited yet". ``tracked_never_targeted`` distinguishes a metric that
    must have no target (E43) from one whose target nobody has set.
    """
    return {"name": metric.name, "value": metric.value, "target": metric.target,
            "basis": metric.basis, "unit": metric.unit,
            "tracked_never_targeted": metric.tracked_never_targeted}


def _slice(traces: Any, model_id: Optional[str]) -> list[Any]:
    records = list(traces.all() if hasattr(traces, "all") else traces)
    return records if model_id is None else [
        t for t in records if t.model_id == model_id]


def _attribution(records: Iterable[Any], model_id: Optional[str]) -> dict[str, Any]:
    """Which model(s) these numbers describe. Never guessed, never averaged away."""
    return {"model_id": model_id,
            "models": tuple(sorted({t.model_id for t in records if t.model_id}))}


# ── LENS 1 · safety & gates ────────────────────────────────────────────────
def safety_lens(traces: Any, gate_events: Any, *,
                model_id: Optional[str] = None) -> dict[str, Any]:
    """Is the AI staying inside its boundaries, and did anything slip the gate?

    ``gate_bypass`` carries the **join that proves it**: how many events were
    examined and exactly which ones offended. A zero nobody can audit is a zero
    nobody should believe, so the screen shows the working rather than the
    headline alone.

    Gate-bypass is deliberately **not** sliced by model even when the rest of
    the lens is: the identity gate runs at the endpoint, before any model is
    reached, so attributing a bypass to whichever model answered afterwards
    would be a fabricated attribution.
    """
    records = _slice(traces, model_id)
    bypass = gate_bypass_count(gate_events)
    offenders = gate_events.disclosures_without_pass()

    styles: Counter = Counter()
    for trace in records:
        for event in trace.guardrail_events:
            styles[event.split(":", 1)[0].strip()] += 1

    return {
        **_attribution(records, model_id),
        "gate_bypass": {**_tile(bypass),
                        "events_examined": len(gate_events.events()),
                        "offenders": [
                            {"seq": e.seq, "policy_no": e.policy_no,
                             "cn_ref": e.cn_ref, "actor": e.actor, "at": e.at}
                            for e in offenders]},
        "advice_boundary": _tile(advice_boundary_violations(records)),
        "guardrail_events_by_type": dict(styles),
        "abstention": _tile(abstention_rate(records)),
        "correct_routing": _tile(correct_routing_rate(records)),
        "containment": _tile(containment(records)),
        "queries": len(records),
    }


# ── LENS 2 · grounding & freshness ─────────────────────────────────────────
def grounding_lens(traces: Any, *, current_versions: Mapping[str, int],
                   citation_styles: Mapping[str, str], kb_version: str,
                   corpus_clauses: int, tombstoned: Optional[Any] = None,
                   model_id: Optional[str] = None) -> dict[str, Any]:
    """Are answers resting on the corpus, and is the corpus they rest on current?

    ``citations_by_style`` reads the style from the **corpus**, not from the
    trace: after task 0 the loop backfills what retrieval said, and asking the
    corpus again here means the count cannot drift from the provenance rule it
    is reporting on.

    ``filter_hit_rate`` is the share of queries that narrowed before ranking —
    retrieval is filter-then-search, and a filter that stops being applied is
    how audience-restricted material reaches the wrong desk.
    """
    records = _slice(traces, model_id)
    cited = [c for t in records for c in t.cited]

    styles: Counter = Counter()
    for citation in cited:
        style = citation_styles.get(citation.chunk_id)
        styles[style or "unknown"] += 1

    filtered = sum(1 for t in records if t.filters_applied.aud or t.filters_applied.doc)
    return {
        **_attribution(records, model_id),
        "stale_citations": _tile(stale_citation_rate(
            records, current_versions=current_versions, tombstoned=tombstoned)),
        "citations_by_style": dict(styles),
        "citations_total": len(cited),
        # Built through Metric like every other tile rather than hand-rolled as
        # a dict — a hand-rolled one is how this tile lost its `unit` and
        # rendered a 0% share as a bare "0".
        "filter_hit_rate": _tile(Metric(
            name="filter_hit_rate", unit="rate", basis=len(records),
            value=(filtered / len(records)) if records else None)),
        "kb_version": kb_version,
        "corpus_clauses": corpus_clauses,
    }


# ── LENS 3 · operations & throughput (kept from v3) ────────────────────────
def operations_lens(cases: list[Case], now: str, *,
                    book: Any = None) -> dict[str, Any]:
    """Is work flowing — what's open, what's done, what's most urgent?

    Carried over from v3 unchanged in spirit, because these numbers were always
    honest. The **ledger reconciliation self-check** moved here from the retired
    system-health lens: every balance recomputed from its own history is the one
    figure that checks the store against itself, and it had no other home.
    """
    open_cases = [c for c in cases if c.status == "pending_review"]
    ranked = sorted(
        open_cases,
        key=lambda c: (priority_rank(c),
                       float("inf") if sla_seconds_left(c, now) is None
                       else sla_seconds_left(c, now)),
    )
    times = [t for t in (sla_seconds_left(c, now) for c in open_cases)
             if t is not None]

    lens: dict[str, Any] = {
        "open": len(open_cases),
        "completed": sum(1 for c in cases if c.status == "completed"),
        "blocked": sum(1 for c in cases if c.status == "blocked"),
        "human_approved": sum(1 for c in cases if _has_event(c, "committed_to_ledger")),
        "by_priority": {p: sum(1 for c in open_cases if c.priority == p)
                        for p in _PRIORITIES},
        "overdue": sum(1 for c in open_cases if _is_overdue(c, now)),
        "soonest_sla_seconds": min(times) if times else None,
        "next_up": ranked[0].case_id if ranked else None,
        "queue": [
            {"case_id": c.case_id, "policy_no": c.policy_no,
             "priority": c.priority, "request": c.request,
             "recommendation": c.recommendation,
             "sla_seconds_left": sla_seconds_left(c, now)}
            for c in ranked
        ],
    }
    lens.update(_book_health(book) if book is not None else {})
    return lens


def _book_health(book: Any) -> dict[str, Any]:
    """The ledger totals and the self-check, recomputed from the histories."""
    policies = book.list_policies()
    reconciled = sum(
        1 for p in policies
        if sum(e.transaction.signed_pence for e in book.history(p.policy_no))
        == book.current_value(p.policy_no))
    return {
        "policies": len(policies),
        "holders": len({p.holder_party_id for p in policies}),
        "funds_under_admin_pence": sum(book.current_value(p.policy_no)
                                       for p in policies),
        "transactions_recorded": sum(len(book.history(p.policy_no))
                                     for p in policies),
        "ledgers_reconciled": reconciled,
        "ledgers_total": len(policies),
    }


# ── the composed snapshot the endpoint serves ──────────────────────────────
def ops_snapshot(book: Any, cases: list[Case], now: str, *, traces: Any,
                 gate_events: Any, corpus_clauses: int, kb_version: str,
                 current_versions: Mapping[str, int],
                 citation_styles: Mapping[str, str],
                 tool_names: Iterable[str], mode: str,
                 tombstoned: Optional[Any] = None,
                 model_id: Optional[str] = None) -> dict[str, Any]:
    """All three lenses in one payload; the screen switches between them.

    ``model_id`` threads through every lens, so a filtered board is filtered
    everywhere or nowhere — a screen half-sliced is worse than one not sliced
    at all, because only half of it is wrong.
    """
    return {
        "now": now,
        "mode": mode,
        "tools_available": list(tool_names),
        "model_id": model_id,
        "safety": safety_lens(traces, gate_events, model_id=model_id),
        "grounding": grounding_lens(traces, current_versions=current_versions,
                                    citation_styles=citation_styles,
                                    kb_version=kb_version,
                                    corpus_clauses=corpus_clauses,
                                    tombstoned=tombstoned, model_id=model_id),
        "operations": operations_lens(cases, now, book=book),
    }
