"""Things that happened to a policy without money moving.

A premium review, an indexation increase, a lapse, a death, a claim registered.
None of these is a ledger row — no money moves — but every one of them is the
reason a ledger row later looks the way it does, and a history that shows the
money without the reasons cannot answer "why did my premium go up?"

These become the change journal (`record_changes`) when the world is loaded. The
ledger journals money; this journals everything else.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Closed on purpose. An event kind that is not in this set is a term nobody has
# defined, and inventing one quietly is how two names for one thing appear.
EVENT_KINDS = frozenset({
    "premium_review",     # `01-WOL:3.8`
    "indexation",         # `01-WOL:3.1`
    "lapse",              # `01-WOL:3.10`
    "paid_up",
    "death",
    "claim_registered",   # `05-OPS:9.1` — notification is not a claim
    "claim_paid",
    "surrender",
    "segment_surrender",  # `02-BOND:4.9`
    "chargeable_event",   # `02-BOND:4.3`
    "benefit_taken",      # `03-PEN:9`
    "mpaa_triggered",     # `03-PEN:4.3`
    "bank_changed",
    "trust_created",
    "mandate_granted",
})


@dataclass(frozen=True)
class LifeEvent:
    """One dated, non-money thing that happened to a policy."""

    on: date
    kind: str
    detail: str

    def __post_init__(self) -> None:
        if self.kind not in EVENT_KINDS:
            raise ValueError(
                f"unknown event kind {self.kind!r} — expected one of "
                f"{sorted(EVENT_KINDS)}")
