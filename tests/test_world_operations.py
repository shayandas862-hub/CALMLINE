"""The operational skeleton — where calls and cases sit in time, with no words.

Which months had contact, which of those raised a case, which case completed and
which was refused, what evidence arrived against which requirement, and **an
empty note slot per contact for phase 4 to fill**. No prose is generated here;
that is phase 4's work and it is written by hand into a committed file.

Two properties the card insists on, and both are about ordering rather than
content:

- **Everything historical is finished business.** No open cases, nothing
  half-done. A queue of thirty-year-old work in progress is not a book anybody
  would recognise.
- **A case that authorised money is dated before the money moved.** Approval is
  the only path that moves money, so a payment with no prior case, or with a
  case dated after it, is a control that never operated.

**One gap in the schema, worked around rather than papered over.** `cases.status`
(`0001_init.sql:313`) offers `pending_review`, `completed`, `blocked` and
`held_for_review` — there is **no terminal refusal**. That missing exit is
already logged as v4.5's own architectural finding. Until it exists, a refused
historical case is `completed` carrying a `human_decision` that says so, which
uses only the vocabulary the schema actually has.
"""

from __future__ import annotations

from datetime import date

import pytest

from world import WORLD_BIRTH_DATE
from world.lifetimes.timeline import Movement
from world.operations import (
    MONEY_OUT_KINDS,
    contact_distribution,
    plan_operations,
)

SEED = 11
START = date(2015, 3, 1)
POLICY_NO = "HB-40582213"


def _movements():
    return (
        Movement(on=START, kind="opening", amount_pence=120_000_00,
                 reason="invested"),
        Movement(on=date(2018, 3, 1), kind="investment_return",
                 amount_pence=8_000_00, reason="growth"),
        Movement(on=date(2020, 6, 15), kind="regular_withdrawal",
                 amount_pence=6_000_00, reason="regular withdrawal"),
        Movement(on=date(2023, 9, 4), kind="segment_surrender",
                 amount_pence=12_000_00, reason="segments surrendered"),
    )


def _plan(policy_no=POLICY_NO, movements=None, start=START):
    return plan_operations(policy_no, movements or _movements(), start=start,
                           seed=SEED, born=WORLD_BIRTH_DATE)


# ── the money-out rule ───────────────────────────────────────────────────
def test_the_money_out_kinds_are_the_ones_that_take_money_from_a_policy():
    assert "regular_withdrawal" in MONEY_OUT_KINDS
    assert "claim_payment" in MONEY_OUT_KINDS
    assert "ufpls_payment" in MONEY_OUT_KINDS
    assert "charge" not in MONEY_OUT_KINDS, "a charge is not a customer request"
    assert "investment_loss" not in MONEY_OUT_KINDS


def test_every_movement_that_took_money_out_has_a_case_behind_it():
    plan = _plan()
    paid = [m for m in _movements() if m.kind in MONEY_OUT_KINDS]
    authorising = [c for c in plan.cases if c.authorised_movement_on]
    assert len(authorising) == len(paid) == 2


def test_a_case_that_authorised_money_is_dated_before_the_money_moved():
    """The card's done-when. Approval is the only path that moves money, so a
    case dated after its payment is a control that never operated."""
    for case in _plan().cases:
        if case.authorised_movement_on:
            assert case.opened_on < case.authorised_movement_on
            assert case.closed_on <= case.authorised_movement_on


def test_the_contact_that_raised_a_case_comes_before_the_case():
    plan = _plan()
    contacts = {c.cn_ref: c for c in plan.contacts}
    for case in plan.cases:
        assert case.cn_ref in contacts
        assert contacts[case.cn_ref].on <= case.opened_on


def test_a_policy_with_no_money_out_still_builds():
    plan = _plan(movements=(Movement(on=START, kind="opening",
                                     amount_pence=1_000_00, reason="in"),))
    assert not [c for c in plan.cases if c.authorised_movement_on]


# ── finished business ────────────────────────────────────────────────────
def test_no_historical_case_is_left_open():
    """The card's done-when."""
    for case in _plan().cases:
        assert case.status == "completed"
        assert case.closed_on is not None


def test_every_case_records_what_was_decided():
    for case in _plan().cases:
        assert case.human_decision in {"proceed", "refused"}


def _book_plans(count=200):
    return [plan_operations(f"HB-{40_000_000 + i}", _movements(), start=START,
                            seed=SEED, born=WORLD_BIRTH_DATE)
            for i in range(count)]


def test_some_cases_across_the_book_were_refused():
    """The card asks which case completed **and which was refused**. A queue
    where everything proceeded is a queue whose refusal path has never been
    exercised, and the bucket plan's governing rule wants at least three."""
    refused = [case for plan in _book_plans() for case in plan.cases
               if case.human_decision == "refused"]
    assert len(refused) >= 3


def test_a_refused_case_never_has_money_behind_it():
    """A case that was refused did not authorise anything, so nothing moved."""
    refused = [case for plan in _book_plans() for case in plan.cases
               if case.human_decision == "refused"]
    assert refused
    for case in refused:
        assert case.authorised_movement_on is None


def test_a_refusal_names_the_rule_that_refused_it():
    """A refusal with no clause behind it is somebody's opinion."""
    refused = [case for plan in _book_plans() for case in plan.cases
               if case.human_decision == "refused"]
    for case in refused:
        assert case.evidence
        for item in case.evidence:
            assert item.requirement_source.startswith("05-OPS:")
            assert item.satisfies == "no"


def test_a_case_closes_on_or_after_it_opened():
    for case in _plan().cases:
        assert case.closed_on >= case.opened_on


def test_nothing_is_dated_after_the_worlds_birth_date():
    plan = _plan()
    for contact in plan.contacts:
        assert START <= contact.on <= WORLD_BIRTH_DATE
    for case in plan.cases:
        assert case.closed_on <= WORLD_BIRTH_DATE


def test_nothing_is_dated_before_the_policy_started():
    for contact in _plan().contacts:
        assert contact.on >= START


# ── the note slot phase 4 fills ──────────────────────────────────────────
def test_every_contact_has_a_note_slot_waiting():
    """The card's done-when, and the reason task 6 built the table."""
    contacts = _plan().contacts
    assert contacts
    for contact in contacts:
        assert contact.note_slot == ""
        assert hasattr(contact, "note_slot")


def test_no_words_are_generated_anywhere():
    """Phase 4 writes the prose, by hand, into a committed file. Anything here
    that reads like a sentence somebody said would be story text."""
    for contact in _plan().contacts:
        assert contact.note_slot == ""


def test_a_contact_still_records_what_it_was_about():
    """An intent and an outcome are vocabulary, not prose — they are what
    `interactions` already carries."""
    for contact in _plan().contacts:
        assert contact.intent
        assert contact.channel


# ── evidence ─────────────────────────────────────────────────────────────
def test_evidence_is_attached_to_the_requirement_it_answers():
    evidence = [e for case in _plan().cases for e in case.evidence]
    assert evidence
    for item in evidence:
        assert item.requirement
        assert item.requirement_source, "a requirement with no source is an "\
            "assertion, not a rule"


def test_evidence_arrives_before_the_case_closes():
    for case in _plan().cases:
        for item in case.evidence:
            assert case.opened_on <= item.received_on <= case.closed_on


def test_evidence_says_whether_it_satisfied_the_requirement():
    for case in _plan().cases:
        for item in case.evidence:
            assert item.satisfies in {"yes", "no", "unverifiable"}


# ── references and determinism ───────────────────────────────────────────
def test_contact_references_match_the_reference_grammar():
    """`05-OPS:1.4` — `CN-` plus ten digits."""
    for contact in _plan().contacts:
        assert contact.cn_ref.startswith("CN-")
        assert len(contact.cn_ref) == 13
        assert contact.cn_ref[3:].isdigit()


def test_case_references_match_the_reference_grammar():
    """`05-OPS:1.4` — `CW-` plus nine digits."""
    for case in _plan().cases:
        assert case.cw_ref.startswith("CW-")
        assert len(case.cw_ref) == 12
        assert case.cw_ref[3:].isdigit()


def test_two_policies_never_share_a_contact_reference():
    first = _plan(policy_no="HB-40582213")
    second = _plan(policy_no="HB-40582214")
    assert not ({c.cn_ref for c in first.contacts}
                & {c.cn_ref for c in second.contacts})


def test_the_same_policy_always_produces_the_same_skeleton():
    assert _plan() == _plan()


# ── the distribution across the book ─────────────────────────────────────
def test_the_contact_distribution_is_uneven():
    """The card's done-when: some policies with none, most with a few, a
    handful with many. An even spread is what a generator produces when nobody
    thought about it, and it is the first thing that reads as synthetic."""
    counts = contact_distribution(
        [f"HB-{40_000_000 + i}" for i in range(200)], seed=SEED)
    values = sorted(counts.values())
    assert values[0] == 0, "some policies were never rung about"
    assert max(values) >= 6, "a handful of policies generate a lot of contact"
    assert sum(1 for v in values if v == 0) >= 10
    assert sum(1 for v in values if 1 <= v <= 4) > len(values) // 2


def test_the_distribution_is_deterministic():
    book = [f"HB-{40_000_000 + i}" for i in range(200)]
    assert contact_distribution(book, seed=SEED) == \
        contact_distribution(book, seed=SEED)


def test_no_policy_gets_a_negative_number_of_contacts():
    counts = contact_distribution([f"HB-{40_000_000 + i}" for i in range(200)],
                                  seed=SEED)
    assert all(v >= 0 for v in counts.values())


def test_a_policy_that_started_after_the_world_is_refused():
    with pytest.raises(ValueError):
        _plan(start=date(2027, 1, 1))
