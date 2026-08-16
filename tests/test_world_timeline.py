"""The timeline engine — playing a policy forward, one checked movement at a time.

The engine before any product knows about it. It walks a policy from its start
date to the world's birth date, offering each proposed movement to the rulebook
and appending it only if accepted.

This file covers what the engine *accepts*: the ledger it builds, the value it
reconciles to, its determinism, and the rule seam each product plugs into. What
it refuses is `test_world_timeline_refusals.py`, because the refusals are the
phase's headline guarantee and deserve their own file rather than a section.
"""

from __future__ import annotations

from datetime import date

from src.records.models import Policy
from world import WORLD_BIRTH_DATE
from world.lifetimes.report import RefusalReport
from world.lifetimes.timeline import Movement, play

START = date(2015, 3, 1)
POLICY_NO = "HB-40000001"


def _policy(policy_no=POLICY_NO, start=START, product="horizon_bond"):
    return Policy(
        policy_no=policy_no,
        product=product,
        status="in_force",
        start_date=start.isoformat(),
        holder_party_id="PH-2001",
    )


def _opening(amount=100_000_00, on=START):
    return Movement(on=on, kind="opening", amount_pence=amount, reason="invested")


def _played(movements, policy=None, report=None, rules=()):
    """Play ``movements`` and hand back both halves of the result."""
    report = report if report is not None else RefusalReport()
    lifetime = play(policy or _policy(), movements, report=report, rules=rules)
    return lifetime, report


# ── the ledger it builds ─────────────────────────────────────────────────
def test_every_accepted_movement_reaches_the_ledger():
    # Arrange
    movements = [
        _opening(),
        Movement(on=date(2016, 3, 1), kind="investment_return",
                 amount_pence=8_000_00, reason="annual growth"),
        Movement(on=date(2016, 3, 1), kind="charge",
                 amount_pence=650_00, reason="annual management charge"),
    ]

    # Act
    lifetime, report = _played(movements)

    # Assert
    assert report.is_empty()
    assert [e.transaction.kind for e in lifetime.entries] == [
        "opening", "investment_return", "charge"]


def test_the_value_equals_the_signed_sum_of_its_movements():
    # Arrange — a bond that opened at £100,000, grew, was charged, took a bonus
    movements = [
        _opening(),
        Movement(on=date(2016, 3, 1), kind="investment_return",
                 amount_pence=20_000_00, reason="growth"),
        Movement(on=date(2017, 3, 1), kind="charge",
                 amount_pence=1_200_00, reason="AMC"),
        Movement(on=date(2018, 3, 1), kind="bonus",
                 amount_pence=500_00, reason="declared bonus"),
        Movement(on=date(2019, 3, 1), kind="investment_loss",
                 amount_pence=3_000_00, reason="a bad year"),
    ]

    # Act
    lifetime, _ = _played(movements)

    # Assert — 100,000 + 20,000 - 1,200 + 500 - 3,000
    assert lifetime.value_pence == 116_300_00
    assert lifetime.value_pence == sum(
        e.transaction.signed_pence for e in lifetime.entries)


def test_a_policy_can_open_take_a_charge_grow_and_take_a_bonus():
    """The version's headline: £100,000 in, and a value that reconciles."""
    lifetime, report = _played([
        _opening(),
        Movement(on=date(2016, 3, 1), kind="charge", amount_pence=650_00,
                 reason="annual charge"),
        Movement(on=date(2016, 3, 1), kind="investment_return",
                 amount_pence=20_650_00, reason="growth"),
        Movement(on=date(2017, 3, 1), kind="bonus", amount_pence=0,
                 reason="none declared"),
    ])
    assert report.is_empty()
    assert lifetime.value_pence == 120_000_00


def test_entries_are_numbered_from_one_in_the_order_they_happened():
    lifetime, _ = _played([
        _opening(),
        Movement(on=date(2017, 3, 1), kind="bonus", amount_pence=100, reason="b"),
    ])
    assert [e.seq for e in lifetime.entries] == [1, 2]


def test_each_entry_carries_the_balance_it_left_behind():
    lifetime, _ = _played([
        _opening(amount=1_000_00),
        Movement(on=date(2017, 3, 1), kind="charge", amount_pence=250_00,
                 reason="AMC"),
    ])
    assert [e.balance_after_pence for e in lifetime.entries] == [1_000_00, 750_00]


def test_the_lifetime_knows_which_policy_it_belongs_to():
    lifetime, _ = _played([_opening()])
    assert lifetime.policy_no == POLICY_NO
    assert lifetime.entries[0].transaction.policy_no == POLICY_NO


# ── determinism ──────────────────────────────────────────────────────────
def test_the_same_movements_produce_the_same_transaction_ids():
    """The world is rebuilt from a seed, not remembered. Two runs must agree."""
    movements = [_opening(), Movement(on=date(2017, 3, 1), kind="bonus",
                                      amount_pence=100, reason="b")]
    first, _ = _played(movements)
    second, _ = _played(movements)
    assert [e.transaction.txn_id for e in first.entries] == \
           [e.transaction.txn_id for e in second.entries]


def test_transaction_ids_are_unique_within_a_policy():
    lifetime, _ = _played([_opening()] + [
        Movement(on=date(2016 + i, 3, 1), kind="bonus", amount_pence=100,
                 reason="b") for i in range(5)])
    ids = [e.transaction.txn_id for e in lifetime.entries]
    assert len(set(ids)) == len(ids)


def test_two_policies_never_share_a_transaction_id():
    first, _ = _played([_opening()])
    second, _ = _played([_opening()], policy=_policy(policy_no="HB-40000002"))
    assert first.entries[0].transaction.txn_id != \
           second.entries[0].transaction.txn_id


def test_nothing_reads_the_wall_clock_the_movement_carries_its_own_time():
    lifetime, _ = _played([_opening(on=date(1999, 3, 1))],
                          policy=_policy(start=date(1999, 3, 1)))
    assert lifetime.entries[0].transaction.at.startswith("1999-03-01")


# ── point-in-time value ──────────────────────────────────────────────────
def test_a_past_valuation_excludes_movements_that_had_not_happened_yet():
    # Arrange
    lifetime, _ = _played([
        _opening(),
        Movement(on=date(2020, 6, 1), kind="bonus", amount_pence=5_000_00,
                 reason="declared"),
    ])

    # Act / Assert — the bonus is in the future on the day before it was declared
    assert lifetime.value_at(date(2020, 5, 31)) == 100_000_00
    assert lifetime.value_at(date(2020, 6, 1)) == 105_000_00


def test_a_valuation_before_the_policy_started_is_nothing():
    lifetime, _ = _played([_opening()])
    assert lifetime.value_at(date(2014, 1, 1)) == 0


# ── the rule seam the products plug into ─────────────────────────────────
def test_a_product_rule_is_offered_every_movement_before_it_is_applied():
    """The seam's whole point: the rule sees the movement *and the balance it
    would be applied to*, before the ledger has it."""
    # Arrange
    seen = []

    def watching(policy, movement, balance_pence):
        seen.append((movement.kind, balance_pence))
        return None

    # Act
    _played([
        _opening(amount=1_000_00),
        Movement(on=date(2016, 3, 1), kind="bonus", amount_pence=500_00,
                 reason="b"),
    ], rules=(watching,))

    # Assert — the balance offered is the one *before* that movement
    assert seen == [("opening", 0), ("bonus", 1_000_00)]


def test_a_rule_is_told_which_policy_it_is_judging():
    seen = []
    _played([_opening()], rules=(lambda p, m, b: seen.append(p.policy_no),))
    assert seen == [POLICY_NO]


def test_every_rule_is_asked_not_only_the_first():
    asked = []
    rules = (lambda p, m, b: asked.append("first"),
             lambda p, m, b: asked.append("second"))
    _played([_opening()], rules=rules)
    assert asked == ["first", "second"]


def test_the_world_is_born_on_the_date_the_engine_stops_at():
    """One named constant, never the wall clock, and this is it."""
    assert WORLD_BIRTH_DATE == date(2026, 7, 28)


def test_an_empty_timeline_is_a_policy_with_no_movements_not_a_refusal():
    lifetime, report = _played([])
    assert report.is_empty()
    assert lifetime.entries == ()
    assert lifetime.value_pence == 0
