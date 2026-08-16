"""The back-office Case, its evidence, and the priority / SLA helpers.

A ``Case`` is mutable — the queue and the approval step transition its status.
SLA time is always measured against an injected ``now`` (an ISO timestamp), so
the maths is deterministic and never depends on the wall clock.

Cases are referenced by the KB's own grammar, `CW-` + 9 (`05-OPS:1.4`), rather
than the repo-native sequential ids they replaced.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from src.agent.tools.money_tools import ProposedTransaction

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}

CW_REF_RE = re.compile(r"^CW-\d{9}$")
CASE_TYPES = frozenset({"servicing", "DSAR", "transfer", "review", "claim_linked"})
EVIDENCE_CHANNELS = frozenset({"phone", "portal", "email", "post", "adviser_portal"})
EVIDENCE_VERDICTS = frozenset({"yes", "no", "unverifiable"})


@dataclass(frozen=True)
class EvidenceItem:
    """One thing the customer has sent in (§3.2 step 8).

    **Not a ledger row** — recording what arrived moves no money, which is why
    this shape carries no amount. ``requirement_source`` is the chunk id of the
    KB rule that demanded it, so "why did we ask for this" is answerable.
    """

    evidence_id: str
    cw_ref: str
    policy_no: str
    requirement: str
    requirement_source: str
    description: str = ""
    received_via: str = "post"
    received_at: str = ""
    taken_by: str = ""
    satisfies: str = "unverifiable"

    def __post_init__(self) -> None:
        if self.received_via not in EVIDENCE_CHANNELS:
            raise ValueError(
                f"{self.evidence_id}: unknown channel {self.received_via!r} "
                f"(expected one of {sorted(EVIDENCE_CHANNELS)})")
        if self.satisfies not in EVIDENCE_VERDICTS:
            raise ValueError(
                f"{self.evidence_id}: unknown verdict {self.satisfies!r} "
                f"(expected one of {sorted(EVIDENCE_VERDICTS)})")


@dataclass
class Case:
    case_id: str
    policy_no: str
    request: str
    # The KB's grammar, minted by the queue. A case may exist before it has one.
    cw_ref: Optional[str] = None
    # The contact this came off, and the verification that permitted reading
    # the record to raise it (v4 phase 3). A case with neither was raised
    # against data nobody was cleared to see.
    cn_ref: Optional[str] = None
    verification_id: Optional[str] = None
    type: str = "servicing"
    authority_level_required: Optional[str] = None
    priority: str = "medium"
    status: str = "pending_review"  # pending_review | completed | blocked | held_for_review
    recommendation: Optional[str] = None  # proceed | do_not_proceed
    checklist: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)
    proposed: Optional[ProposedTransaction] = None
    sla_due: Optional[str] = None  # ISO timestamp
    human_decision: Optional[str] = None
    created_at: Optional[str] = None
    audit: list[dict[str, Any]] = field(default_factory=list)
    # Four-eyes (`07-RUNBOOK:4.3`): "sign-off is recorded with maker_id and
    # checker_id on the case". The maker proposed the movement; the checker
    # approved it; they may never be the same person.
    maker_id: Optional[str] = None
    checker_id: Optional[str] = None
    # Dual authorisation (`05-OPS:14`) — a separate, additional control above
    # £250,000. Set on the first approval, cleared by a second DISTINCT
    # approver. Four-eyes tests correctness; this tests authority.
    requires_second_approver: bool = False
    second_approver_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.cw_ref is not None and not CW_REF_RE.match(self.cw_ref):
            raise ValueError(
                f"cw_ref {self.cw_ref!r} is not CW- plus nine digits")
        if self.type not in CASE_TYPES:
            raise ValueError(
                f"unknown case type {self.type!r} (expected one of {sorted(CASE_TYPES)})")


def priority_rank(case: Case) -> int:
    """Lower is more urgent: high=0, medium=1, low=2 (unknown sorts last)."""
    return _PRIORITY_RANK.get(case.priority, 99)


def sla_seconds_left(case: Case, now: str) -> Optional[int]:
    """Seconds until the SLA is due (negative = overdue); ``None`` if no SLA."""
    if not case.sla_due:
        return None
    delta = datetime.fromisoformat(case.sla_due) - datetime.fromisoformat(now)
    return int(delta.total_seconds())
