"""The human-gated approval — the only place a proposal reaches the ledger.

``approve_case`` is a human action. It re-checks server-side that the case is
still pending and that the pre-check recommended ``proceed``; then, if the case
carries a proposed movement, it commits that movement to the ledger and records
the audit. A ``do_not_proceed`` case is refused. Nothing here runs automatically
— the AI proposes, a named human commits.

**v4 phase 3** adds the two controls `07-RUNBOOK:4.3` keeps deliberately apart:

* **four-eyes** — the maker cannot be the checker (E39). It tests *correctness*:
  a second pair of eyes re-performs the control.
* **dual authorisation** — above £250,000 a second, distinct approver is
  required (`05-OPS:14`). It tests *authority*, not correctness, which is why
  it stacks on top of four-eyes rather than replacing it.

Plus the band ceiling: a session may only approve movements its level covers
(`src/authority/matrix.py`). Both new checks are only meaningful because the
session now names an actor rather than a role alone (D-CL-045).

There is still exactly one ledger write in this file, and it is still the only
one in the system.
"""

from __future__ import annotations

from typing import Any

from src.authority.matrix import (
    band_for,
    may_approve,
    requires_second_approver,
    transaction_for,
)
from src.casework.models import Case
from src.casework.queue import CaseQueue
from src.records.models import format_gbp


class ApprovalError(RuntimeError):
    """Raised when a case may not be approved (wrong state, band, or approver)."""


def approve_case(queue: CaseQueue, record_store: Any, case_id: str, *,
                 reviewer: str, at: str, txn_id: str,
                 role: str = "back_office") -> Case:
    """Approve a case: commit its proposed movement (if any) and complete it.

    ``role`` is the approving session's role or level. It defaults to
    ``back_office`` because that is the only role this console issues that can
    approve anything at all.
    """
    case = queue.get(case_id)

    if case.status != "pending_review":
        raise ApprovalError(f"case {case_id} is {case.status}, not pending_review")
    if case.recommendation != "proceed":
        raise ApprovalError(
            f"case {case_id} recommends {case.recommendation!r} — it cannot be approved"
        )

    if case.proposed is not None:
        held = _authorise_movement(case, record_store, reviewer=reviewer,
                                   role=role, at=at)
        if held is not None:
            return held               # awaiting a second approver; nothing moves

    case.audit.append({"event": "approved", "at": at, "actor": reviewer})

    if case.proposed is not None:
        txn = case.proposed.to_transaction(txn_id)
        record_store.apply_transaction(case.policy_no, txn)  # the one ledger write
        case.audit.append({"event": "committed_to_ledger", "at": at,
                           "actor": reviewer, "txn_id": txn_id})

    case.status = "completed"
    case.human_decision = "approved"
    return case


def _authorise_movement(case: Case, record_store: Any, *, reviewer: str,
                        role: str, at: str):
    """Run four-eyes, the band ceiling and dual authorisation.

    Returns the case when it is *held* awaiting a second approver, and ``None``
    when the movement may proceed. Raises ``ApprovalError`` when it may not.
    """
    proposal = case.proposed
    policy = record_store.get_policy(case.policy_no)
    product = getattr(policy, "product", "")
    transaction = transaction_for(proposal.kind, product)
    amount = proposal.amount_pence

    # Four-eyes first: who is asking matters before how much (07-RUNBOOK:4.3).
    if proposal.actor == reviewer:
        raise ApprovalError(
            f"case {case.case_id}: {reviewer} is the maker of this proposal and "
            f"cannot also be the checker (07-RUNBOOK:4.3)")

    if not may_approve(role, transaction, amount):
        band = band_for(transaction, amount)
        raise ApprovalError(
            f"case {case.case_id}: a {transaction} of {format_gbp(amount)} needs "
            f"{band.approver} approval ({band.source}); this session is {role}")

    if not requires_second_approver(transaction, amount):
        case.maker_id = proposal.actor
        case.checker_id = reviewer
        return None

    # Above the dual-authorisation threshold.
    if case.checker_id is None:
        case.requires_second_approver = True
        case.maker_id = proposal.actor
        case.checker_id = reviewer
        case.audit.append({"event": "first_approval", "at": at, "actor": reviewer,
                           "note": "awaiting a second, distinct approver "
                                   f"({format_gbp(amount)}, 05-OPS:14)"})
        return case

    if reviewer == case.checker_id:
        raise ApprovalError(
            f"case {case.case_id} needs a second, distinct approver — "
            f"{reviewer} has already approved it (05-OPS:14)")

    case.second_approver_id = reviewer
    return None
