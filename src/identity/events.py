"""The gate event log — what the gate did, in the order it did it.

Five kinds. ``presented`` when the questions go to the caller, ``passed`` /
``failed`` when the handler confirms an outcome, ``disclosure`` every time
personal data actually leaves the server, and ``bypass_attempt`` when something
reached for that data without a live verification behind it.

Append-only **by absence** — no delete, update, edit or clear exists to call.
This mirrors `src/records/changelog.py`, and for the same reason: a log that
can be edited is not evidence of anything.

Deliberately narrow. Phase 5's TraceStore subsumes this seam, so it holds five
kinds and answers one question rather than growing into a framework first.

That question is ``disclosures_without_pass()``: did anything get disclosed
without a passed verification *before* it, on the same interaction and the same
policy? It is the gate-bypass count phase 5 reports, and the number this phase
is judged on. Order matters — a pass recorded after the disclosure is a bypass
with tidy paperwork, and is counted as one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.records.models import require_in

GATE_EVENT_KINDS = frozenset(
    {"presented", "passed", "failed", "disclosure", "bypass_attempt"})


@dataclass(frozen=True)
class GateEvent:
    """One thing the gate did.

    ``cn_ref`` is optional because the event most worth catching — a reach for
    the data with no interaction open at all — has no interaction to name.
    """

    seq: int
    kind: str
    policy_no: str
    actor: str
    at: str
    cn_ref: Optional[str] = None

    def __post_init__(self) -> None:
        require_in(f"gate event {self.seq}", "kind", self.kind, GATE_EVENT_KINDS)


class GateEventLog:
    """The events, in the order they were recorded."""

    def __init__(self) -> None:
        self._events: list[GateEvent] = []
        self._seq = 0

    def record(self, *, kind: str, policy_no: str, actor: str, at: str,
               cn_ref: Optional[str] = None) -> GateEvent:
        """Append one event and return it."""
        self._seq += 1
        event = GateEvent(seq=self._seq, kind=kind, policy_no=policy_no,
                          actor=actor, at=at, cn_ref=cn_ref)
        self._events.append(event)
        return event

    # ── reading ──────────────────────────────────────────────────────────
    def events(self) -> tuple[GateEvent, ...]:
        """An immutable snapshot — mutating it cannot reach the log."""
        return tuple(self._events)

    def for_interaction(self, cn_ref: str) -> tuple[GateEvent, ...]:
        return tuple(e for e in self._events if e.cn_ref == cn_ref)

    def for_policy(self, policy_no: str) -> tuple[GateEvent, ...]:
        return tuple(e for e in self._events if e.policy_no == policy_no)

    def of_kind(self, kind: str) -> tuple[GateEvent, ...]:
        return tuple(e for e in self._events if e.kind == kind)

    # ── the gate-bypass question ─────────────────────────────────────────
    def disclosures_without_pass(self) -> tuple[GateEvent, ...]:
        """Every disclosure with no passed verification before it, in scope.

        Walks the log once in order, remembering which ``(cn_ref, policy_no)``
        pairs have passed so far. A disclosure whose pair is not yet in that set
        is a bypass — including one covered only by a pass that arrives later,
        or by a pass on a different policy or a different interaction.
        """
        passed: set[tuple[Optional[str], str]] = set()
        offenders: list[GateEvent] = []
        for event in self._events:
            scope = (event.cn_ref, event.policy_no)
            if event.kind == "passed":
                passed.add(scope)
            elif event.kind == "disclosure" and scope not in passed:
                offenders.append(event)
        return tuple(offenders)

    def bypass_count(self) -> int:
        """The headline number: disclosures with nothing behind them. Target 0."""
        return len(self.disclosures_without_pass())
