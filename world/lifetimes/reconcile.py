"""Reconciling the played book with the rulebook — holders, relief, claim work.

Three corrections, all pure functions of data already drawn, all consuming no
RNG — a redraw would renumber histories that prose has already been written
against. Each exists because phase 4 measured a rulebook breach in the
committed world:

- **two pension benefits were taken at 33 and 46**, against `03-PEN:9`'s normal
  minimum pension age of 55 with no ill-health or protected age recorded. The
  benefit cannot move (the holder would be 55 after the world ends) and cannot
  be dropped (the bucket plan's MPAA demonstrations need it), so the **holders
  swap**: each offending policy exchanges holders with one whose holder was old
  enough all along, chosen deterministically.
- **36 contribution rows claimed "gross of relief at source" past the holder's
  75th birthday**, against `03-PEN:2`'s relief-to-75. The amounts are settled;
  the **wording** is corrected to what the money actually was.
- the case behind every claim payment was typed `servicing`. A death claim is
  **claim work** — `cases.type` has carried `claim_linked` since the schema was
  written and the world never used it once.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Mapping

NMPA_YEARS = 55        # `03-PEN:9` — normal minimum pension age
RELIEF_CEILING = 75    # `03-PEN:2` — tax relief stops at the 75th birthday
ADULT_AT_START = 23    # phase 3's achieved floor; a swap may not degrade it

STRADDLE = "12 monthly contributions, relief at source until the 75th birthday"
UNRELIEVED = "12 monthly contributions, no tax relief — contributor over 75"


def _birthday(dob: date, years: int) -> date:
    try:
        return dob.replace(year=dob.year + years)
    except ValueError:                       # the leap-day birthday
        return dob.replace(year=dob.year + years, day=28)


# ── the minimum pension age ──────────────────────────────────────────────

def swap_for_minimum_age(policies: tuple, dobs: Mapping[str, date]) -> tuple:
    """Benefits before 55 keep their dates; the holders exchange instead.

    The donor search is deterministic and both-directional: the donor must
    have been 55 by the first benefit, an adult of phase 3's standard at the
    policy's start, and under 75 at its every contribution — and the displaced
    holder must satisfy the same tests on the donor's policy. Earliest date of
    birth wins, ties broken by policy number, and a world with no eligible
    donor refuses to build rather than shipping the breach.
    """
    book = {p.policy_no: p for p in policies}
    for policy in sorted(policies, key=lambda p: p.policy_no):
        benefit = _first_benefit(policy)
        if benefit is None or _age(dobs, policy.holder_party_id,
                                   benefit) >= NMPA_YEARS:
            continue
        donor = _donor_for(book[policy.policy_no], book, dobs)
        a, b = book[policy.policy_no], donor
        book[a.policy_no] = replace(a, holder_party_id=b.holder_party_id)
        book[b.policy_no] = replace(b, holder_party_id=a.holder_party_id)
    return tuple(book[p.policy_no] for p in policies)


def _donor_for(target, book: Mapping, dobs: Mapping[str, date]):
    candidates = [
        p for p in book.values()
        if p.product == target.product and p.status == "in_force"
        and _first_benefit(p) is None
        and p.holder_party_id != target.holder_party_id
        and _fits(dobs[p.holder_party_id], target)
        and _fits(dobs[target.holder_party_id], p)]
    if not candidates:
        raise ValueError(
            f"{target.policy_no}: a benefit was taken below age {NMPA_YEARS} "
            f"and no eligible holder exists to swap with")
    return min(candidates,
               key=lambda p: (dobs[p.holder_party_id], p.policy_no))


def _fits(dob: date, policy) -> bool:
    """Could this person have lived this policy's whole recorded life?"""
    if (policy.start - _birthday(dob, ADULT_AT_START)).days < 0:
        return False
    benefit = _first_benefit(policy)
    if benefit is not None and (benefit - _birthday(dob, NMPA_YEARS)).days < 0:
        return False
    ceiling = _birthday(dob, RELIEF_CEILING)
    return all(entry.transaction.at[:10] <= ceiling.isoformat()
               for entry in policy.entries
               if entry.transaction.kind == "contribution")


def _first_benefit(policy):
    return min((e.on for e in policy.events if e.kind == "benefit_taken"),
               default=None)


def _age(dobs: Mapping[str, date], party_id: str, on: date) -> float:
    return (on - dobs[party_id]).days / 365.25


# ── relief stops at 75 ───────────────────────────────────────────────────

def reword_relief(policies: tuple, dobs: Mapping[str, date]) -> tuple:
    """Contribution rows past the 75th birthday stop claiming relief.

    The amounts are settled and the balances hold; what changes is the claim
    the row makes about the money. A summary year the birthday falls inside is
    relieved up to it and says so; a year wholly past it had no relief at all.
    """
    corrected = []
    for policy in policies:
        ceiling = _birthday(dobs[policy.holder_party_id], RELIEF_CEILING)
        entries, changed = [], False
        for entry in policy.entries:
            txn = entry.transaction
            when = date.fromisoformat(txn.at[:10])
            if (txn.kind == "contribution" and when > ceiling
                    and "gross of relief at source" in txn.reason):
                reason = (STRADDLE if when - timedelta(days=365) < ceiling
                          else UNRELIEVED)
                entry = replace(entry, transaction=replace(txn, reason=reason))
                changed = True
            entries.append(entry)
        corrected.append(replace(policy, entries=tuple(entries))
                         if changed else policy)
    return tuple(corrected)


# ── a death is notified after it happens ─────────────────────────────────

def notify_after_death(policies: tuple, operations: dict) -> dict:
    """The notification call behind a claim may not precede the death.

    The skeleton dates a claim's contact at ``paid − 14..40 days``, and where
    the claim settled quickly that lands **before the death being notified** —
    `LP-20007946`'s bereavement call was three days ahead of the death it
    reports. The contact slides to just before registration, its case dates
    follow, and the money still moves only after the case closes.
    """
    from world.lifetimes.workingdays import add_working_days

    for policy in policies:
        when = {e.kind: e.on for e in policy.events}
        if "death" not in when:
            continue
        paid = {e.transaction.at[:10] for e in policy.entries
                if e.transaction.kind == "claim_payment"}
        ops = operations[policy.policy_no]
        claim_refs = {k.cn_ref for k in ops.cases
                      if k.authorised_movement_on
                      and k.authorised_movement_on.isoformat() in paid}

        moved = {}
        for contact in ops.contacts:
            if (contact.cn_ref in claim_refs
                    and contact.intent == "bereavement_notification"
                    and contact.on < when["death"]):
                moved[contact.cn_ref] = max(
                    when["death"] + timedelta(days=1),
                    when["claim_registered"] - timedelta(days=2))
        if not moved:
            continue

        contacts = tuple(sorted(
            (replace(c, on=moved[c.cn_ref]) if c.cn_ref in moved else c
             for c in ops.contacts), key=lambda c: (c.on, c.cn_ref)))
        cases = []
        for case in ops.cases:
            if case.cn_ref not in moved:
                cases.append(case)
                continue
            opened = add_working_days(moved[case.cn_ref], 1)
            closed = add_working_days(opened, 3)
            assert case.authorised_movement_on is not None \
                and closed < case.authorised_movement_on, \
                f"{policy.policy_no} {case.cw_ref}: the moved case cannot " \
                f"close before its money"
            cases.append(replace(
                case, opened_on=opened, closed_on=closed,
                evidence=tuple(replace(item, received_on=opened)
                               for item in case.evidence)))
        operations[policy.policy_no] = replace(
            ops, contacts=contacts,
            cases=tuple(sorted(cases, key=lambda k: (k.opened_on, k.cw_ref))))
    return operations


# ── a claim's case is claim work ─────────────────────────────────────────

def retype_claim_cases(policies: tuple, operations: dict) -> dict:
    """Any case that authorised a claim payment is `claim_linked`."""
    for policy in policies:
        paid = {e.transaction.at[:10] for e in policy.entries
                if e.transaction.kind == "claim_payment"}
        if not paid:
            continue
        ops = operations[policy.policy_no]
        operations[policy.policy_no] = replace(ops, cases=tuple(
            replace(case, type="claim_linked")
            if (case.authorised_movement_on is not None
                and case.authorised_movement_on.isoformat() in paid)
            else case
            for case in ops.cases))
    return operations
