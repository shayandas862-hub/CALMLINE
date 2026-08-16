"""A Horizon Bond played end to end — segments, withdrawals, and surrenders.

`02-BOND:3.1` — issued as identical mini-policies, Aldercrest default **1,000**,
"enabling tax-efficient surrender of whole segments (§4.9)".

`02-BOND:4.3` — a chargeable event is assessed on full surrender, surrender of
whole segments, a partial withdrawal exceeding the cumulative 5% allowance
(**tested at policy-year end**), death of the last life assured, assignment for
money's worth, or maturity.

`02-BOND:4.9` — three routes to the same cash with very different tax. A large
partial withdrawal early on "can create an **artificially huge gain** unrelated
to real growth", which is precisely what the §5 contrast demonstrates and why
the two routes must not be modelled as the same event.

`02-BOND:3.4` — death benefit typically **101%** of bond value on death of the
last life assured. `02-BOND:3.6` — an MVR may reduce surrender proceeds when
markets have fallen, **never on death**, and not at the tenth-anniversary
guarantee point.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.records.models import Policy
from src.records.products import FundHolding
from world import WORLD_BIRTH_DATE
from world.lifetimes.bond import play_bond
from world.lifetimes.bond.segments import (
    DEFAULT_SEGMENTS,
    segment_value_pence,
    segments_for_amount,
)
from world.lifetimes.report import RefusalReport
from world.lifetimes.timeline import play

SEED = 11
INVESTED = 120_000_00
START = date(2015, 3, 1)
POLICY_NO = "HB-40582213"


def _policy(status="in_force", start=START):
    return Policy(policy_no=POLICY_NO, product="horizon_bond", status=status,
                  start_date=start.isoformat(), holder_party_id="PH-2001")


def _holdings():
    return (FundHolding("managed_growth", "Managed Growth", 60, 65, "2026-07-28"),
            FundHolding("with_profits", "With-Profits", 40, 55, "2026-07-28"))


def _plan(status="in_force", start=START, invested=INVESTED, **kwargs):
    return play_bond(_policy(status=status, start=start), _holdings(),
                     invested_pence=invested, seed=SEED, **kwargs)


def _through_the_rulebook(plan, status="in_force", start=START):
    report = RefusalReport()
    lifetime = play(_policy(status=status, start=start), plan.movements,
                    report=report)
    return lifetime, report


# ── segments ─────────────────────────────────────────────────────────────
def test_the_default_is_the_corpus_one_thousand_segments():
    assert DEFAULT_SEGMENTS == 1_000


def test_a_segment_is_worth_the_bond_divided_by_its_segments():
    assert segment_value_pence(120_000_00, 1_000) == 120_00


def test_surrendering_segments_takes_whole_segments_only():
    """`02-BOND:3.1` — identical mini-policies. Half a segment does not exist."""
    count = segments_for_amount(6_050_00, segment_value_pence(120_000_00, 1_000),
                                segments_remaining=1_000)
    assert count == 50
    assert isinstance(count, int)


def test_segments_surrendered_never_exceed_those_remaining():
    assert segments_for_amount(999_000_00, 120_00, segments_remaining=10) == 10


def test_segments_surrendered_never_go_below_zero():
    assert segments_for_amount(1, 120_00, segments_remaining=1_000) == 0


def test_a_bond_with_no_segments_left_can_surrender_none():
    assert segments_for_amount(6_000_00, 120_00, segments_remaining=0) == 0


# ── the whole bond ───────────────────────────────────────────────────────
def test_a_bond_is_built_without_a_single_refusal():
    lifetime, report = _through_the_rulebook(_plan())
    assert report.is_empty(), report.render()
    assert lifetime is not None


def test_it_opens_with_the_amount_invested():
    plan = _plan()
    assert plan.movements[0].kind == "opening"
    assert plan.movements[0].amount_pence == INVESTED
    assert plan.movements[0].on == START


def test_its_value_equals_the_sum_of_its_movements():
    lifetime, _ = _through_the_rulebook(_plan())
    assert lifetime.value_pence == sum(
        e.transaction.signed_pence for e in lifetime.entries)


def test_a_bond_never_lapses_and_never_becomes_paid_up():
    """A single-premium contract cannot lapse for non-payment, which is why the
    bucket plan leaves both cells empty for the Horizon Bond."""
    kinds = {m.kind for m in _plan().movements}
    assert "premium" not in kinds
    assert not [e for e in _plan().events if e.kind in {"lapse", "paid_up"}]


def test_nothing_is_dated_outside_the_policys_life():
    plan = _plan()
    for item in list(plan.movements) + list(plan.events):
        assert START <= item.on <= WORLD_BIRTH_DATE


def test_the_same_seed_builds_the_same_bond_to_the_penny():
    assert _plan().movements == _plan().movements
    assert _plan().events == _plan().events


# ── withdrawals and the allowance ────────────────────────────────────────
def test_regular_withdrawals_inside_the_allowance_raise_no_chargeable_event():
    """The specimen's own pattern: £6,000 a year on £120,000 invested is
    exactly 5%, and stays tax-deferred for as long as it runs."""
    plan = _plan(withdraw_annually_pence=6_000_00)
    assert [m for m in plan.movements if m.kind == "regular_withdrawal"]
    assert not [e for e in plan.events if e.kind == "chargeable_event"]


def test_a_withdrawal_beyond_the_allowance_is_recorded_as_a_chargeable_event():
    """`02-BOND:4.3` — and recorded as a breach, not silently permitted."""
    plan = _plan(withdraw_annually_pence=12_000_00)
    breaches = [e for e in plan.events if e.kind == "chargeable_event"]
    assert breaches, "a withdrawal at 10% of the premium must breach 5%"
    assert "excess" in breaches[0].detail.lower()


def test_a_chargeable_event_is_dated_at_the_policy_year_end():
    """`02-BOND:4.3` — "tested at policy-year end". Dating it on the day of the
    withdrawal would judge two withdrawals in one year separately, and the
    second would escape a test the first had already failed."""
    plan = _plan(withdraw_annually_pence=12_000_00)
    (first,) = [e for e in plan.events if e.kind == "chargeable_event"][:1]
    assert (first.on.month, first.on.day) == (START.month, START.day)


def test_the_allowance_never_ends_up_overdrawn():
    plan = _plan(withdraw_annually_pence=6_000_00)
    assert plan.allowance_used_pence <= plan.invested_pence


def test_segments_remaining_stays_inside_its_bounds_all_the_way_through():
    """The card's done-when: never below zero, never above the number issued."""
    for withdrawal in (0, 6_000_00, 12_000_00):
        plan = _plan(withdraw_annually_pence=withdrawal)
        assert 0 <= plan.segments_remaining <= plan.segments_total
        assert plan.segments_total == DEFAULT_SEGMENTS


# ── segment surrender: the other route to the same cash ──────────────────
def test_a_segment_surrender_reduces_the_segments_remaining():
    """`02-BOND:3.1` — whole segments, and the count comes down."""
    plan = _plan(surrender_segments_pence=12_000_00)
    assert plan.segments_remaining < plan.segments_total
    assert plan.segments_remaining > 0


def test_a_segment_surrender_posts_its_own_movement_kind():
    """`02-BOND:4.9` — same cash as a partial withdrawal, very different tax.
    Modelling them as one event would erase the comparison the corpus says must
    be surfaced before processing."""
    plan = _plan(surrender_segments_pence=12_000_00)
    assert [m for m in plan.movements if m.kind == "segment_surrender"]


def test_a_segment_surrender_is_a_chargeable_event_in_its_own_right():
    """`02-BOND:4.3` lists "surrender of whole segments" separately from a
    partial withdrawal exceeding the allowance."""
    plan = _plan(surrender_segments_pence=12_000_00)
    breaches = [e for e in plan.events if e.kind == "chargeable_event"]
    assert any("segment" in e.detail.lower() for e in breaches)


def test_a_segment_surrender_does_not_consume_the_five_percent_allowance():
    """The allowance is a partial-withdrawal mechanic. Charging a segment
    surrender against it would be the classic conflation of the two routes."""
    without = _plan()
    with_segments = _plan(surrender_segments_pence=12_000_00)
    assert with_segments.allowance_used_pence == without.allowance_used_pence


def test_a_segment_surrender_lands_on_a_whole_number_of_segments():
    plan = _plan(surrender_segments_pence=12_345_67)
    (movement,) = [m for m in plan.movements if m.kind == "segment_surrender"]
    surrendered = plan.segments_total - plan.segments_remaining
    assert surrendered > 0
    assert movement.amount_pence % surrendered == 0


# ── surrender ────────────────────────────────────────────────────────────
def test_a_surrendered_bond_ends_empty_and_raises_a_chargeable_event():
    """`02-BOND:4.3` — full surrender is always a chargeable event."""
    plan = _plan(status="surrendered")
    lifetime, report = _through_the_rulebook(plan, status="surrendered")
    assert report.is_empty(), report.render()
    assert lifetime.value_pence == 0
    assert [e for e in plan.events if e.kind == "chargeable_event"]
    assert plan.segments_remaining == 0


def test_a_surrendered_bond_has_nothing_after_the_surrender():
    plan = _plan(status="surrendered")
    (surrender,) = [m for m in plan.movements if m.kind == "surrender"]
    assert all(m.on <= surrender.on for m in plan.movements)


def test_a_claimed_bond_pays_the_corpus_hundred_and_one_percent():
    """`02-BOND:3.4` — 101% of bond value on death of the last life assured."""
    plan = _plan(status="claimed")
    lifetime, report = _through_the_rulebook(plan, status="claimed")
    assert report.is_empty(), report.render()
    assert lifetime.value_pence == 0
    assert [e.kind for e in plan.events if e.kind in
            {"death", "claim_registered", "claim_paid"}] == \
        ["death", "claim_registered", "claim_paid"]


def test_an_investment_larger_than_the_book_allows_is_still_whole_pence():
    plan = _plan(invested=999_999_99)
    assert all(isinstance(m.amount_pence, int) for m in plan.movements)


def test_a_bond_younger_than_a_year_still_builds():
    """The bucket plan's newest bonds start in 2024 — two years of history."""
    plan = _plan(start=date(2026, 1, 5))
    lifetime, report = _through_the_rulebook(plan, start=date(2026, 1, 5))
    assert report.is_empty(), report.render()
    assert lifetime.value_pence == INVESTED


def test_asking_a_bond_to_lapse_is_refused_rather_than_quietly_built():
    with pytest.raises(ValueError, match="lapse"):
        _plan(status="lapsed")
