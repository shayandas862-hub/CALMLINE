"""The CaseQueue — the back office's work list.

Opens cases (it is the sink the phase-2 ``raise_case`` tool hands to), ranks
them by priority then time-to-SLA, and attaches a pre-check result to a case.
In-memory now; the same shape is backed by the database at the gate.
"""

from __future__ import annotations

from typing import Any, Optional

from src.agent.tools.money_tools import ProposedTransaction
from src.casework.models import Case, priority_rank, sla_seconds_left


class QueueError(RuntimeError):
    """Raised when a case id is not in the queue."""


# `CW-` + 9 (KB `05-OPS:1.4`). The base keeps minted references the same shape
# as the one the corpus itself quotes (`CW-300218754`).
CW_REF_BASE = 300_000_000


class CaseQueue:
    def __init__(self) -> None:
        self._cases: dict[str, Case] = {}
        self._seq = 0

    def open(self, request: dict[str, Any], *, sla_due: Optional[str] = None) -> Case:
        """Create a case from a raise-case request and store it.

        The `CW-` reference is minted here and doubles as the case id, so there
        is one identifier for a piece of work rather than an internal id and a
        customer-facing reference that can drift apart.
        """
        self._seq += 1
        cw_ref = f"CW-{CW_REF_BASE + self._seq:09d}"
        case = Case(
            case_id=cw_ref,
            cw_ref=cw_ref,
            policy_no=request["policy_no"],
            request=request["request"],
            type=request.get("type", "servicing"),
            authority_level_required=request.get("authority_level_required"),
            priority=request.get("priority", "medium"),
            status=request.get("status", "pending_review"),
            sla_due=sla_due,
            # Which contact this came off, and which verification permitted it
            # — so a case can always be traced back to a gate that opened.
            cn_ref=request.get("cn_ref"),
            verification_id=request.get("verification_id"),
        )
        self._cases[case.case_id] = case
        return case

    def admit(self, case: Case) -> Case:
        """Take in a case that already owns its identity.

        The dataset's live queue arrives with policy-derived `CW-` references
        minted by the world (v4.5 phase 5); re-minting here would break "the
        same cases are in the database after a reload". Adds only — a
        reference already present is refused, because one reference names
        exactly one piece of work.
        """
        if case.case_id in self._cases:
            raise QueueError(f"{case.case_id} is already in the queue")
        self._cases[case.case_id] = case
        return case

    def get(self, case_id: str) -> Case:
        if case_id not in self._cases:
            raise QueueError(f"unknown case {case_id!r}")
        return self._cases[case_id]

    def all(self) -> list[Case]:
        return list(self._cases.values())

    def list_ranked(self, now: str) -> list[Case]:
        """Most urgent first: by priority, then least SLA time left (no SLA last)."""
        def key(case: Case) -> tuple[int, float]:
            left = sla_seconds_left(case, now)
            return (priority_rank(case), float("inf") if left is None else left)

        return sorted(self._cases.values(), key=key)

    def attach_precheck(self, case_id: str, *, checklist: list[dict[str, Any]],
                        recommendation: str, proposed: Optional[ProposedTransaction] = None) -> Case:
        """Record the compliance pre-check (and any proposed movement) on a case."""
        case = self.get(case_id)
        case.checklist = list(checklist)
        case.recommendation = recommendation
        case.proposed = proposed
        return case
