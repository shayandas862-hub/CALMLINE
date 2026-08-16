"""The whole book — two hundred policies, and the proof that they reconcile.

The card's done-when, each its own test:

- running twice produces an identical book **to the penny**
- every policy's value equals **the sum of its movements**
- no movement anywhere is dated after the world's birth date
- no withdrawal ever exceeded the balance on its own day
- the report is **empty of unintended refusals**
- every partition in the bucket plan totals 200

Plus §11, which no task assigned and which the generator could not meet: sixty
of the two hundred holders carry a memorable datum. Closed here by a separately
seeded pass that leaves `data/world/people.jsonl` byte-identical, because adding
a draw inside the identity generator would shift every subsequent draw and
rebuild all 299 people.

**§8 is measured on the headline value, and that is a decision.** A partition of
all 200 by *final ledger balance* is impossible: at least 74 policies end at zero
— everything lapsed, claimed or surrendered, plus every protection-only
whole-of-life policy, which `01-WOL:3.3` gives no surrender value — while §8
allows only 58 under £25,000. §8 states its own purpose as the approval matrix,
and `05-OPS:9.9` bands claim-payment authority by value, so the figure a control
actually tests is the fund for investment-backed policies and the **sum assured**
for protection cover. A policy carrying £400,000 of cover is not an "under
£25,000" policy in any sense a control cares about.
"""

from __future__ import annotations

from datetime import date

import pytest

from world import WORLD_BIRTH_DATE
from world.lifetimes.allocation import BAND_COUNTS
from world.lifetimes.build import build_book

SEED = 11

_BOOK = None


def book():
    """Built once — two hundred policies is not free, and it is deterministic."""
    global _BOOK
    if _BOOK is None:
        _BOOK = build_book(seed=SEED, born=WORLD_BIRTH_DATE)
    return _BOOK


# ── the bands, measured on the finished book ─────────────────────────────
def test_the_value_band_partition_is_met_exactly():
    """§8 — 58 / 74 / 55 / 13, on the **built** policies rather than on the
    plan. The allocation asking for a band is not the same fact as the finished
    policy landing in it."""
    seen: dict[str, int] = {}
    for policy in book().policies:
        seen[policy.band] = seen.get(policy.band, 0) + 1
    assert seen == BAND_COUNTS
    assert sum(seen.values()) == 200


def test_thirteen_policies_require_dual_authorisation():
    """§8's whole reason for existing — a second approver above £250,000
    (`05-OPS:9.9`) is a control that is demonstrable rather than theoretical."""
    above = [p for p in book().policies
             if p.headline_value_pence >= 250_000_00]
    assert len(above) == 13


def test_fifty_eight_policies_could_fail_a_sufficient_value_check():
    """§8 — what makes "sufficient value to cover the request" a check that can
    fail on a realistic ask."""
    below = [p for p in book().policies
             if p.headline_value_pence < 25_000_00]
    assert len(below) == 58


def test_no_two_policies_are_worth_exactly_the_same():
    """Scaling every policy onto one target per band made seventy-four of them
    worth almost exactly £62,000, which is the first thing that reads as
    generated. Each now draws its own target from inside its band."""
    values = [p.headline_value_pence for p in book().policies]
    assert len(set(values)) == len(values) == 200


# ── the reconciliation ───────────────────────────────────────────────────
def test_the_report_is_empty_of_refusals():
    """The card's headline. A world that broke its own rules while being built
    would say so here, naming the policy, the day and the rule."""
    assert book().report.is_empty(), book().report.render()


def test_every_policy_reconciles_to_the_penny():
    """Value equals the sum of the movements. Not the last balance — the sum,
    so the figure is derived from the movements themselves."""
    for policy in book().policies:
        assert policy.value_pence == sum(
            e.transaction.signed_pence for e in policy.entries)


def test_no_movement_anywhere_is_dated_after_the_worlds_birth_date():
    for policy in book().policies:
        for entry in policy.entries:
            assert entry.transaction.at[:10] <= WORLD_BIRTH_DATE.isoformat()


def test_no_movement_is_dated_before_its_policy_started():
    for policy in book().policies:
        for entry in policy.entries:
            assert entry.transaction.at[:10] >= policy.start.isoformat()


def test_no_withdrawal_ever_exceeded_the_balance_on_its_own_day():
    """The ledger refuses an overdraw, so this can only fail if a policy was
    never offered to it — which is the failure worth testing for."""
    for policy in book().policies:
        for entry in policy.entries:
            assert entry.balance_after_pence >= 0


def test_no_policy_holds_a_fractional_penny():
    for policy in book().policies:
        for entry in policy.entries:
            assert isinstance(entry.transaction.amount_pence, int)


def test_every_policy_number_matches_its_product():
    for policy in book().policies:
        assert policy.policy_no[:2] == {
            "lifelong_protection": "LP", "horizon_bond": "HB",
            "retirement_account": "RA"}[policy.product]


def test_no_two_policies_share_a_number():
    numbers = [p.policy_no for p in book().policies]
    assert len(set(numbers)) == len(numbers) == 200


# ── determinism ──────────────────────────────────────────────────────────
def test_building_twice_produces_an_identical_book_to_the_penny():
    """The card's done-when. The world is rebuilt from a seed, not remembered."""
    first = build_book(seed=SEED, born=WORLD_BIRTH_DATE)
    second = build_book(seed=SEED, born=WORLD_BIRTH_DATE)
    assert [p.policy_no for p in first.policies] == \
        [p.policy_no for p in second.policies]
    assert [p.value_pence for p in first.policies] == \
        [p.value_pence for p in second.policies]
    for left, right in zip(first.policies, second.policies):
        assert left.entries == right.entries


def test_a_different_seed_produces_a_different_book():
    other = build_book(seed=12, born=WORLD_BIRTH_DATE)
    assert [p.value_pence for p in other.policies] != \
        [p.value_pence for p in book().policies]


# ── §11, which no task assigned ──────────────────────────────────────────
def test_sixty_holders_carry_a_memorable_datum():
    """§11 — four askable checks for 60, three for the other 140. The identity
    generator emits none, and a draw added there would rebuild all 299 people,
    so this is a separate pass over the committed file.

    **Sixty distinct people, not sixty entries.** Counting the list alone passed
    while five people were selected twice, because the pass was drawn from one
    entry per *policy* — two hundred of them, but only 162 distinct holders,
    since some people hold two or three. The world reported sixty and gave four
    askable checks to fifty-five.
    """
    memorable = book().memorable_holders
    assert len(memorable) == 60
    assert len(set(memorable)) == 60


def test_the_memorable_pass_leaves_the_people_file_untouched():
    """It selects party ids; it does not rewrite anybody."""
    from pathlib import Path
    people = Path("data/world/people.jsonl").read_bytes()
    build_book(seed=SEED, born=WORLD_BIRTH_DATE)
    assert Path("data/world/people.jsonl").read_bytes() == people


def test_the_memorable_selection_is_deterministic():
    assert build_book(seed=SEED, born=WORLD_BIRTH_DATE).memorable_holders == \
        build_book(seed=SEED, born=WORLD_BIRTH_DATE).memorable_holders


def test_every_memorable_holder_is_one_of_the_two_hundred_policyholders():
    """§11 partitions **the 200 policyholders**, which is why 60 + 140 = 200.

    That set is not the same as "everyone holding a policy": 162 people hold at
    least one and the other 38 appear only as the second life on a joint-life
    policy (§1). A second life is still a policyholder, still on the telephone,
    and still verified against `05-OPS:3.2` — so the memorable datum is drawn
    across all 200. Restricting it to the 162 would leave the partition totalling
    162, which §11 does not say.
    """
    from world.lifetimes.build import load_people

    policyholders = {p["party_id"] for p in load_people()
                     if p["role"] == "policyholder"}
    assert len(policyholders) == 200
    assert set(book().memorable_holders) <= policyholders


# ── the fraud pattern, end to end ────────────────────────────────────────
def test_a_bank_change_precedes_a_withdrawal_on_at_least_three_policies():
    """Task 5's done-when, provable only now that the movements exist.
    `05-OPS:3.4` — the pattern is a change *followed by* a withdrawal, so the
    order is the whole fact."""
    found = 0
    for policy in book().policies:
        mandate = book().bank_mandates.get(policy.policy_no)
        if not mandate or not mandate.change_history:
            continue
        changed = date.fromisoformat(mandate.change_history[-1].at[:10])
        after = [e for e in policy.entries
                 if e.transaction.kind in {"withdrawal", "regular_withdrawal",
                                           "surrender", "segment_surrender",
                                           "payout", "ufpls_payment"}
                 and e.transaction.at[:10] > changed.isoformat()]
        if after:
            found += 1
    assert found >= 3


# ── the shape of the whole thing ─────────────────────────────────────────
def test_every_policy_has_a_bank_position():
    assert len(book().bank_mandates) == 200


def test_the_book_carries_its_operations_and_every_contact_has_a_note_slot():
    contacts = [c for ops in book().operations.values() for c in ops.contacts]
    assert contacts
    assert all(c.note_slot == "" for c in contacts)


def test_no_historical_case_anywhere_is_left_open():
    for ops in book().operations.values():
        for case in ops.cases:
            assert case.status == "completed"


def test_the_book_is_not_two_hundred_near_copies():
    """The whole reason the bucket plan exists."""
    values = {p.value_pence for p in book().policies}
    assert len(values) > 100


def test_a_book_built_for_a_day_before_any_policy_started_is_refused():
    with pytest.raises(ValueError):
        build_book(seed=SEED, born=date(1990, 1, 1))
