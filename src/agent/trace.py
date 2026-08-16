"""The decision trace — an ordered record of everything the agent did.

Each tool call, its result summary, and the final verdict append in order.
This is the per-case decision log the demo renders and the audit trail stores.

``to_trace_record`` at the bottom is the bridge to the persisted
`06-RAGOPS:4.1` shape. It takes **two** inputs, because neither alone is
enough: the trace knows what the agent *did*, the reply knows what it *said*.
Everything belonging to neither — who asked, when, on which interaction, at
what latency — is passed explicitly rather than grown onto ``DecisionTrace``,
which the eval path in ``loop.py`` also writes and which phase 5 does not own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass
class DecisionTrace:
    steps: list[dict[str, Any]] = field(default_factory=list)

    def thinking(self, text: str) -> None:
        self.steps.append({"kind": "thinking", "text": text})

    def tool_call(self, tool: str, args: dict[str, Any]) -> None:
        self.steps.append({"kind": "tool_call", "tool": tool, "args": args})

    def tool_result(self, tool: str, summary: str, refs: list[str] | None = None,
                    ranked: list[dict[str, Any]] | None = None) -> None:
        step: dict[str, Any] = {"kind": "tool_result", "tool": tool, "summary": summary}
        if refs is not None:
            step["refs"] = list(refs)  # the clause ids retrieval returned (grounding check, R6)
        if ranked is not None:
            # Where this call placed each of them. Recorded ALONGSIDE `refs`
            # rather than replacing it: `refs` is a list of ids read by the eval
            # scorer and pinned by four tests, and reshaping it would break both
            # for no gain the ranking does not already give.
            step["ranked"] = [dict(entry) for entry in ranked]
        self.steps.append(step)

    def verdict(self, summary: str) -> None:
        self.steps.append({"kind": "verdict", "summary": summary})

    def as_list(self) -> list[dict[str, Any]]:
        """A shallow copy — callers can snapshot without later mutation leaking in."""
        return list(self.steps)

    def retrieved_refs(self) -> list[str]:
        """Every chunk id retrieval returned, in order, de-duplicated.

        The trace is the only record of this. The reply cannot be asked — what
        the model says it saw is exactly what the grounding check exists to
        distrust.
        """
        seen: dict[str, None] = {}
        for step in self.steps:
            for ref in step.get("refs") or ():
                seen.setdefault(ref, None)
        return list(seen)

    def retrieved_ranked(self) -> list[dict[str, Any]]:
        """Where retrieval placed each chunk, best placement first.

        ``retrieved_refs`` cannot answer this: it merges every tool call's ids
        into one insertion-ordered set, and a set is not a ranking. ``recall@5``
        asks whether the expected chunk was in the **top five retrieval
        returned**, so the rank is recorded per call, in the searcher's own
        order, and folded here.

        A chunk two calls both returned keeps the **best** rank it earned.
        Retrieval found it in the top five if any query put it there; taking the
        last call's rank would report a miss for a chunk that was found, and
        taking the first would report one for a chunk a later query found better.
        """
        best: dict[str, dict[str, Any]] = {}
        for step in self.steps:
            for entry in step.get("ranked") or ():
                chunk_id = entry.get("chunk_id")
                prior, rank = best.get(chunk_id), entry.get("rank")
                if prior is None or _outranks(rank, prior.get("rank")):
                    best[chunk_id] = dict(entry)
        # Stable: ranked chunks in rank order, unranked last, ties by first seen.
        return sorted(best.values(),
                      key=lambda e: (e.get("rank") is None, e.get("rank") or 0))


def _outranks(candidate: Optional[int], incumbent: Optional[int]) -> bool:
    """Is ``candidate`` a better placement than ``incumbent``? Unranked never is."""
    if candidate is None:
        return False
    return incumbent is None or candidate < incumbent


def to_trace_record(
    trace: "DecisionTrace",
    reply: Any,
    *,
    trace_id: str,
    ts: str,
    user_role: str,
    mode: str,
    cn_ref: Optional[str] = None,
    model_id: Optional[str] = None,
    channel: str = "console",
    filters: Optional[Mapping[str, Any]] = None,
    latency_ms: Optional[Mapping[str, Any]] = None,
    kb_version: Optional[str] = None,
    handoff: Optional[str] = None,
    versions: Optional[Mapping[str, Any]] = None,
) -> Any:
    """Fold a finished run into the persisted `06-RAGOPS:4.1` record.

    ``versions`` is the loop's chunk-id → provenance map, the same one it uses
    to backfill citations. Given it, ``retrieved[]`` states the version each
    chunk was read at; without it those versions stay ``None`` rather than being
    invented — ``cited[]`` carries real versions either way, since the reply's
    citations were themselves backfilled from retrieval.

    ``rank`` and ``score`` come from the trace instead, because they are facts
    about **one call** where the version is a fact about the chunk: the map is
    merged across every tool call and a merged map has no ranking left in it.
    A path that records no ranking (the keyword path builds its own trace) still
    lists what it retrieved, with a null rank rather than an invented one.

    ``resolved_intent`` and ``feedback`` are deliberately absent: nothing in the
    codebase produces them, and a null is honest where a guess would not be.
    """
    from src.traces.schema import TraceRecord  # local: keeps agent -> traces one-way

    provenance = versions or {}
    placed = {entry["chunk_id"]: entry for entry in trace.retrieved_ranked()}
    return TraceRecord(
        trace_id=trace_id,
        cn_ref=cn_ref,
        ts=ts,
        channel=channel,
        user_role=user_role,
        filters_applied=dict(filters or {}),
        retrieved=[{"chunk_id": ref,
                    "version": (provenance.get(ref) or {}).get("version"),
                    "rank": (placed.get(ref) or {}).get("rank"),
                    "score": (placed.get(ref) or {}).get("score")}
                   for ref in trace.retrieved_refs()],
        cited=[{"chunk_id": c.chunk_id, "version": c.version}
               for c in getattr(reply, "citations", [])],
        answer_text=getattr(reply, "answer_text", "") or "",
        abstained={"flag": bool(getattr(reply, "abstained", False)),
                   "reason": getattr(reply, "abstention_reason", None)},
        guardrail_events=list(getattr(reply, "guardrail_events", []) or []),
        handoff=handoff,
        latency_ms=dict(latency_ms or {}),
        model_id=model_id,
        mode=mode,
        kb_version=kb_version,
    )
