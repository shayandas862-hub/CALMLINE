"""The Retirement Account's death claim — the ending the pension never had.

Phase 4 found the gap by measuring: **all three claimed Retirement Accounts had
no death, no claim, still held money — one held £63,542.02 — and took
contributions to the end of the world.** The whole-of-life and bond players own
their claim sequences; the pension player had no cease path for `claimed`, and
phase 3's closed-policy fix keyed on events that were never emitted.

The claim is **grafted after play rather than planned during it**, and every
date is pure arithmetic off the ledger's own last movement. Planning it inside
the player would consume RNG draws before the operations planner runs, which
renumbers every contact on the policy — and prose has already been written
against those histories.

The shape mirrors the seven correct LP/HB claims exactly: death, then
`claim_registered` when somebody rings it in, then `claim_paid` to verified
beneficiaries — `05-OPS:9.1`, "Notification ≠ claim". The uncrystallised pot is
paid in full and the ledger closes at zero. Requirements follow `05-OPS:9.2`:
the certificate always, and for a Retirement Account the nominated
beneficiaries verified.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

from src.records.models import LedgerEntry, Transaction
from world.lifetimes.events import LifeEvent
from world.lifetimes.workingdays import add_working_days
from world.operations.shapes import (
    PlannedCase,
    PlannedContact,
    PlannedEvidence,
    PolicyOperations,
)

# `05-OPS:9.9` — acknowledge, issue requirements, assess, pay: the same claim
# timetable the whole-of-life player uses, in working days.
CLAIM_STAGES = (1, 3, 5, 5)

# Reference index for grafted items: far above the planner's proceed range
# (1–n) and its refused range (+500), so nothing can collide.
GRAFT_INDEX = 901

DEATH_CERTIFICATE = ("certified death certificate received; nominated "
                     "beneficiaries verified", "05-OPS:9.2")


def _serial(policy_no: str) -> int:
    return int("".join(c for c in policy_no if c.isdigit()) or "0")


def graft_pension_claims(policies: tuple, operations: dict, *,
                         born: date) -> tuple[tuple, dict]:
    """Every claimed Retirement Account gains its death, its claim, its
    notification call and its claim case. Everything else passes through."""
    grafted = []
    for policy in policies:
        if (policy.product != "retirement_account"
                or policy.status != "claimed"
                or any(e.kind == "claim_paid" for e in policy.events)):
            grafted.append(policy)
            continue
        policy, operations[policy.policy_no] = _graft(
            policy, operations[policy.policy_no], born=born)
        grafted.append(policy)
    return tuple(grafted), operations


def _graft(policy, ops: PolicyOperations, *, born: date):
    last_moved = date.fromisoformat(policy.entries[-1].transaction.at[:10])
    serial = _serial(policy.policy_no)

    died = last_moved + timedelta(days=14 + serial % 21)
    notified = died + timedelta(days=8 + serial % 12)
    paid = notified
    for stage in CLAIM_STAGES:
        paid = add_working_days(paid, stage)
    if paid > born:
        raise ValueError(
            f"{policy.policy_no}: the claim would pay {paid.isoformat()}, "
            f"after the world's birth date — the graft has nowhere to stand")

    pot = policy.entries[-1].balance_after_pence
    seq = policy.entries[-1].seq + 1
    entry = LedgerEntry(
        seq=seq,
        transaction=Transaction(
            txn_id=f"{policy.policy_no}-{seq:04d}",
            policy_no=policy.policy_no, kind="claim_payment",
            amount_pence=pot,
            reason="death benefit paid to the nominated beneficiaries",
            actor="world-builder", at=f"{paid.isoformat()}T00:00:00"),
        balance_after_pence=0)

    events = policy.events + (
        LifeEvent(on=died, kind="death", detail="death of the member"),
        LifeEvent(on=notified, kind="claim_registered",
                  detail="death notified; claim registered and requirements "
                         "issued"),
        LifeEvent(on=paid, kind="claim_paid",
                  detail="claim assessed and paid to the verified nominated "
                         "beneficiaries"),
    )

    contact = PlannedContact(
        cn_ref=_reference("CN", 10, policy.policy_no),
        policy_no=policy.policy_no, on=notified, channel="phone",
        intent="bereavement_notification", outcome="case_raised")
    opened = add_working_days(notified, 1)
    case = PlannedCase(
        cw_ref=_reference("CW", 9, policy.policy_no),
        policy_no=policy.policy_no, cn_ref=contact.cn_ref,
        opened_on=opened, closed_on=add_working_days(opened, 4),
        request=f"bereavement_notification — {pot}p",
        type="claim_linked", status="completed", human_decision="proceed",
        evidence=(PlannedEvidence(
            evidence_id=_reference("EVD", 9, policy.policy_no),
            requirement=DEATH_CERTIFICATE[0],
            requirement_source=DEATH_CERTIFICATE[1],
            received_on=opened, satisfies="yes", received_via="post"),),
        authorised_movement_on=paid)

    return (replace(policy, entries=policy.entries + (entry,), events=events),
            PolicyOperations(
                policy.policy_no,
                tuple(sorted(ops.contacts + (contact,),
                             key=lambda c: (c.on, c.cn_ref))),
                tuple(sorted(ops.cases + (case,),
                             key=lambda k: (k.opened_on, k.cw_ref)))))


def _reference(prefix: str, digits: int, policy_no: str) -> str:
    """The planner's own reference grammar, at the graft's reserved index."""
    from world.operations.skeleton import _reference as mint

    return mint(prefix, digits, policy_no, GRAFT_INDEX)
