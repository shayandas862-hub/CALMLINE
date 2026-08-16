"""The world may not contradict itself, and may not contradict the rulebook.

Phase 4 found one fault with four limbs while writing prose against the book —
**an operational attribute drawn without consulting the thing it describes** —
plus one outright rulebook breach. Phase 3 fixed the same fault for start dates
against the holder's date of birth; these lock the rest:

- case evidence asserted parties the policy does not have (112 of 473)
- `adviser_portal` carried contacts on policies with no adviser mandate
  (240 of 301)
- every guaranteed-plan lapse claimed a 30-day grace period its own date
  contradicted (12 of 14)
- pension benefits were taken at 33 and 46 against `03-PEN:9`'s normal minimum
  pension age of 55
- the three claimed Retirement Accounts had no death, no claim, still held
  money, and took contributions to the end of the world
- contribution rows claimed "gross of relief at source" past the 75th birthday,
  against `03-PEN`'s relief-to-75 rule

Everything here is asserted over the **whole generated book**, so a future
change that reintroduces any of it fails loudly.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

NMPA = 55  # `03-PEN:9` — normal minimum pension age, 55 throughout the world's life
RELIEF_CEILING = 75  # `03-PEN:2` — tax-relieved contributions stop at 75

TRUST_YES = ("trustee signatures obtained",)
LOA_YES = ("adviser authority checked against the FCA Register",)
TRUST_NO = ("all trustees must instruct and one did not",)
TRUST_UNEXECUTED = ("the trust was never properly executed",)
LOA_NO = ("an LOA cannot change the customer's bank details",
          "instruction fell outside the verified adviser scope")
ATTORNEY_NO = ("the power of attorney is not yet registered with the OPG",)


@pytest.fixture(scope="module")
def dobs():
    path = Path("data/world/people.jsonl")
    return {p["party_id"]: date.fromisoformat(p["dob"])
            for p in map(json.loads, path.read_text().splitlines())
            if "party_id" in p and "dob" in p}


def _age(dob: date, on: date) -> float:
    return (on - dob).days / 365.25


# ── evidence names only parties the policy has ───────────────────────────
def test_no_evidence_asserts_a_party_the_policy_does_not_have(world_book):
    for policy_no, ops in world_book.operations.items():
        has_trust = policy_no in world_book.trusts
        has_loa = policy_no in world_book.adviser_mandates
        has_attorney = any(a.type in ("LPA", "EPA") for a in
                           world_book.authorities.get(policy_no, ()))
        for case in ops.cases:
            for item in case.evidence:
                need = item.requirement
                if need in TRUST_YES + TRUST_NO + TRUST_UNEXECUTED:
                    assert has_trust, f"{policy_no} {case.cw_ref}: {need!r}, no trust"
                if need in LOA_YES + LOA_NO:
                    assert has_loa, f"{policy_no} {case.cw_ref}: {need!r}, no mandate"
                if need in ATTORNEY_NO:
                    assert has_attorney, \
                        f"{policy_no} {case.cw_ref}: {need!r}, no attorney"


def test_an_unexecuted_trust_refusal_needs_an_unexecuted_trust(world_book):
    """'The trust was never properly executed' on an executed trust is a
    refusal that contradicts the record it refuses on."""
    for policy_no, ops in world_book.operations.items():
        for case in ops.cases:
            for item in case.evidence:
                if item.requirement in TRUST_UNEXECUTED:
                    trust = world_book.trusts[policy_no]
                    assert trust.executed == "no", \
                        f"{policy_no} {case.cw_ref}: trust is executed"


# ── the adviser portal implies an adviser ────────────────────────────────
def test_the_adviser_portal_is_only_used_where_a_mandate_exists(world_book):
    for policy_no, ops in world_book.operations.items():
        if policy_no in world_book.adviser_mandates:
            continue
        for contact in ops.contacts:
            assert contact.channel != "adviser_portal", \
                f"{policy_no} {contact.cn_ref}: adviser_portal, no mandate"
        for case in ops.cases:
            for item in case.evidence:
                assert item.received_via != "adviser_portal", \
                    f"{policy_no} {case.cw_ref}: evidence via portal, no mandate"


def test_evidence_arrives_by_the_channel_its_contact_used(world_book):
    """`received_via` was copied from the contact at generation; the remap must
    keep them in step or the case contradicts the call it came from. The one
    exception is the death certificate — `05-OPS:9.2`'s documentary evidence
    arrives by post however the death was phoned in."""
    for ops in world_book.operations.values():
        channels = {c.cn_ref: c.channel for c in ops.contacts}
        for case in ops.cases:
            for item in case.evidence:
                if "death certificate" in item.requirement:
                    assert item.received_via == "post"
                else:
                    assert item.received_via == channels[case.cn_ref]


# ── a lapse agrees with its own dates ────────────────────────────────────
def test_every_lapse_that_names_a_due_date_lapses_on_grace_arithmetic(world_book):
    """`01-WOL:3.10`: grace is 30 days from the missed premium. The event text
    names the due date; the event date must be that plus the grace — plus the
    stated months of unit-cancellation where the fund carried the cover."""
    checked = 0
    for policy in world_book.policies:
        for event in policy.events:
            if event.kind != "lapse" or "premium due" not in event.detail:
                continue
            checked += 1
            due = date.fromisoformat(
                re.search(r"premium due (\d{4}-\d{2}-\d{2})", event.detail)[1])
            months = re.search(r"further (\d+) month", event.detail)
            expected = due + timedelta(days=30 + 30 * int(months[1] if months else 0))
            assert event.on == expected, \
                f"{policy.policy_no}: lapse {event.on}, due {due} says {expected}"
            assert not any(
                e.transaction.kind in ("premium", "contribution")
                and e.transaction.at[:10] >= due.isoformat()
                for e in policy.entries), \
                f"{policy.policy_no}: money collected on or after the missed due"
    assert checked >= 12, "the guaranteed-lapse population went missing"


# ── pension benefits obey the minimum age ────────────────────────────────
def test_no_pension_benefit_is_taken_below_the_minimum_age(world_book, dobs):
    for policy in world_book.policies:
        for event in policy.events:
            if event.kind == "benefit_taken":
                age = _age(dobs[policy.holder_party_id], event.on)
                assert age >= NMPA, \
                    f"{policy.policy_no}: benefit at {age:.1f}, NMPA is {NMPA}"


def test_every_holder_was_an_adult_when_their_policy_started(world_book, dobs):
    """Phase 3's guarantee, re-asserted so the swaps cannot degrade it."""
    for policy in world_book.policies:
        assert _age(dobs[policy.holder_party_id], policy.start) >= 18


# ── a claimed policy carries its claim ───────────────────────────────────
def test_every_claimed_policy_shows_the_full_claim_sequence(world_book):
    """`05-OPS:9.1` — notification is not claim; pay only a verified claimant.
    Death, registration, payment, in order, and the money actually left."""
    claimed = [p for p in world_book.policies if p.status == "claimed"]
    assert len(claimed) == 10
    for policy in claimed:
        when = {e.kind: e.on for e in policy.events}
        assert {"death", "claim_registered", "claim_paid"} <= set(when), \
            f"{policy.policy_no} is claimed and never says how"
        assert when["death"] <= when["claim_registered"] <= when["claim_paid"]

        assert policy.entries[-1].balance_after_pence == 0, \
            f"{policy.policy_no}: claimed but still holding money"
        assert policy.entries[-1].transaction.kind == "claim_payment"
        paid = when["claim_paid"].isoformat()
        assert not any(e.transaction.at[:10] > paid for e in policy.entries), \
            f"{policy.policy_no}: money moved after the claim was paid"

        ops = world_book.operations[policy.policy_no]
        assert any(c.intent == "bereavement_notification"
                   and when["death"] <= c.on <= when["claim_paid"]
                   for c in ops.contacts), \
            f"{policy.policy_no}: a claim was paid and nobody ever notified it"


def test_the_case_behind_a_claim_payment_is_claim_work(world_book):
    """A death claim is claim work, not servicing — `cases.type` has carried
    `claim_linked` since the schema was written and the world never used it."""
    linked = 0
    for policy in world_book.policies:
        paid_on = {e.transaction.at[:10] for e in policy.entries
                   if e.transaction.kind == "claim_payment"}
        if not paid_on:
            continue
        cases = [k for k in world_book.operations[policy.policy_no].cases
                 if k.authorised_movement_on
                 and k.authorised_movement_on.isoformat() in paid_on]
        assert cases, f"{policy.policy_no}: a claim was paid with no case behind it"
        for case in cases:
            assert case.type == "claim_linked", \
                f"{policy.policy_no} {case.cw_ref}: claim money, {case.type} case"
            linked += 1
    assert linked == 10


# ── tax relief stops at 75 ───────────────────────────────────────────────
def test_no_contribution_claims_relief_past_the_seventy_fifth_birthday(
        world_book, dobs):
    """`03-PEN:2` — tax relief to 75. A summary year that straddles the
    birthday says so; a year wholly past it claims no relief at all."""
    for policy in world_book.policies:
        dob = dobs[policy.holder_party_id]
        try:
            birthday = dob.replace(year=dob.year + RELIEF_CEILING)
        except ValueError:  # the leap-day birthday
            birthday = dob.replace(year=dob.year + RELIEF_CEILING, day=28)
        for entry in policy.entries:
            if entry.transaction.kind != "contribution":
                continue
            if "gross of relief at source" in entry.transaction.reason:
                assert date.fromisoformat(entry.transaction.at[:10]) <= birthday, \
                    f"{policy.policy_no}: relief claimed at " \
                    f"{entry.transaction.at[:10]}, past 75"
