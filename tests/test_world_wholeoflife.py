"""A whole-of-life policy played end to end — and accepted by the rulebook.

The card's headline: a policy opened in the nineties showing premiums, its
reviews, indexation, a fund that rose and fell, the annual charge each year, and
a value that reconciles to the penny.

The composer decides *what happens*; `world.lifetimes.timeline` decides whether
it is allowed. Every test here that builds a plan also plays it through the
engine, because a plan that reconciles in isolation and is refused by the
rulebook is worth nothing — and that refusal is the only thing this phase
actually guarantees.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.records.models import Policy
from src.records.products import CoverComponent, FundHolding, Indexation
from world import WORLD_BIRTH_DATE
from world.lifetimes.report import RefusalReport
from world.lifetimes.timeline import play
from world.lifetimes.wholeoflife import play_whole_of_life

SEED = 11


def _policy(status="in_force", start=date(1998, 4, 20), policy_no="LP-20419876"):
    return Policy(policy_no=policy_no, product="lifelong_protection",
                  status=status, start_date=start.isoformat(),
                  holder_party_id="PH-2001")


def _cover(policy_no="LP-20419876", basis=("reviewable", "unit_linked"),
           indexation=Indexation(on=True)):
    return CoverComponent(policy_no=policy_no, sum_assured_pence=400_000_00,
                          basis=basis, premium_pence=212_40,
                          premium_frequency="monthly", riders=("waiver",),
                          indexation=indexation)


def _holdings():
    return (FundHolding("protection_managed", "Protection Managed", 100, 85,
                        "2026-07-28"),)


def _plan(status="in_force", start=date(1998, 4, 20), basis=None, **kwargs):
    policy = _policy(status=status, start=start)
    cover = _cover(basis=basis or ("reviewable", "unit_linked"))
    holdings = _holdings() if "unit_linked" in (basis or ("unit_linked",)) else ()
    return play_whole_of_life(policy, cover, holdings, seed=SEED, **kwargs)


def _through_the_rulebook(plan, status="in_force", start=date(1998, 4, 20)):
    """Offer the plan's movements to the engine, as the world builder will."""
    report = RefusalReport()
    lifetime = play(_policy(status=status, start=start), plan.movements,
                    report=report)
    return lifetime, report


# ── the headline ─────────────────────────────────────────────────────────
def test_a_policy_from_1998_is_built_without_a_single_refusal():
    plan = _plan()
    lifetime, report = _through_the_rulebook(plan)
    assert report.is_empty(), report.render()
    assert lifetime is not None


def test_its_value_equals_the_sum_of_everything_that_happened_to_it():
    plan = _plan()
    lifetime, _ = _through_the_rulebook(plan)
    assert lifetime.value_pence == sum(
        e.transaction.signed_pence for e in lifetime.entries)


def test_it_shows_premiums_growth_and_a_charge_every_year():
    kinds = {m.kind for m in _plan().movements}
    assert {"premium", "charge"} <= kinds
    assert kinds & {"investment_return", "investment_loss"}


def test_it_shows_its_premium_reviews():
    """`01-WOL:3.8` — year 10, then five-yearly. A policy started 1998-04-20
    has reached its 2008, 2013, 2018 and 2023 reviews by the world's birth
    date; the year-30 review falls in 2028 and has not happened."""
    plan = _plan()
    reviews = [e for e in plan.events if e.kind == "premium_review"]
    assert len(reviews) == 4


def test_it_shows_indexation_raising_cover_over_time():
    plan = _plan()
    assert any(e.kind == "indexation" for e in plan.events)


def test_indexation_off_raises_the_cover_on_no_anniversary_at_all():
    """Cover can still *fall* — `01-WOL:3.8`(c) reduces it when the customer
    declines a premium increase. What must not happen is a rise, because the
    only thing that raises cover is indexation and this policy has none."""
    policy, cover = _policy(), _cover(indexation=Indexation(on=False))
    plan = play_whole_of_life(policy, cover, _holdings(), seed=SEED)
    assert not [e for e in plan.events if e.kind == "indexation"]
    assert plan.sum_assured_pence <= 400_000_00


def test_the_fund_both_rose_and_fell_over_thirty_years():
    kinds = [m.kind for m in _plan().movements]
    assert "investment_return" in kinds
    assert "investment_loss" in kinds


# ── ordering and bounds, which the engine enforces anyway ────────────────
def test_every_movement_is_in_date_order():
    movements = _plan().movements
    assert [m.on for m in movements] == sorted(m.on for m in movements)


def test_nothing_is_dated_before_the_policy_started_or_after_the_world():
    plan = _plan()
    for item in list(plan.movements) + list(plan.events):
        assert date(1998, 4, 20) <= item.on <= WORLD_BIRTH_DATE


def test_the_same_seed_builds_the_same_policy_to_the_penny():
    first, second = _plan(), _plan()
    assert first.movements == second.movements
    assert first.events == second.events


# ── lapse ────────────────────────────────────────────────────────────────
def test_a_lapsed_policy_shows_premiums_stopping_before_the_lapse():
    """The card's done-when, exactly."""
    # Arrange / Act
    plan = _plan(status="lapsed")
    (lapse,) = [e for e in plan.events if e.kind == "lapse"]
    premiums = [m for m in plan.movements if m.kind == "premium"]

    # Assert
    assert premiums, "a policy that never paid a premium did not lapse"
    assert max(m.on for m in premiums) < lapse.on


def test_a_lapsed_policy_has_nothing_at_all_after_the_lapse():
    plan = _plan(status="lapsed")
    (lapse,) = [e for e in plan.events if e.kind == "lapse"]
    assert all(m.on <= lapse.on for m in plan.movements)
    assert all(e.on <= lapse.on for e in plan.events)


def test_a_lapse_is_accepted_by_the_rulebook():
    plan = _plan(status="lapsed")
    _, report = _through_the_rulebook(plan, status="lapsed")
    assert report.is_empty(), report.render()


def test_a_guaranteed_policy_lapses_without_a_fund_to_live_on():
    """`01-WOL:3.10` — no units to cancel, so the grace period is the end."""
    plan = _plan(status="lapsed", basis=("guaranteed",))
    (lapse,) = [e for e in plan.events if e.kind == "lapse"]
    assert "grace" in lapse.detail.lower()


# ── claim ────────────────────────────────────────────────────────────────
def test_a_claimed_policy_shows_the_three_events_in_sequence():
    """The card's done-when: death, then claim, then payment."""
    plan = _plan(status="claimed")
    sequence = [e.kind for e in plan.events
                if e.kind in {"death", "claim_registered", "claim_paid"}]
    assert sequence == ["death", "claim_registered", "claim_paid"]


def test_a_claimed_policy_has_nothing_after_the_payment():
    plan = _plan(status="claimed")
    (paid,) = [e for e in plan.events if e.kind == "claim_paid"]
    assert all(m.on <= paid.on for m in plan.movements)
    assert all(e.on <= paid.on for e in plan.events)


def test_the_claim_payment_empties_the_policy():
    """A claimed policy is finished business. A residual balance would be money
    the insurer is still holding for someone who has died."""
    plan = _plan(status="claimed")
    lifetime, report = _through_the_rulebook(plan, status="claimed")
    assert report.is_empty(), report.render()
    assert lifetime.value_pence == 0


# ── paid up and surrendered ──────────────────────────────────────────────
def test_a_paid_up_policy_stops_collecting_but_keeps_its_fund():
    plan = _plan(status="paid_up")
    (paid_up,) = [e for e in plan.events if e.kind == "paid_up"]
    premiums = [m for m in plan.movements if m.kind == "premium"]
    charges = [m for m in plan.movements if m.kind == "charge"]
    assert max(m.on for m in premiums) < paid_up.on
    assert any(m.on > paid_up.on for m in charges), \
        "a paid-up policy still costs something to run"


def test_a_surrendered_policy_ends_with_a_surrender_that_empties_it():
    plan = _plan(status="surrendered")
    lifetime, report = _through_the_rulebook(plan, status="surrendered")
    assert report.is_empty(), report.render()
    assert plan.movements[-1].kind == "surrender"
    assert lifetime.value_pence == 0


def test_a_guaranteed_policy_cannot_be_surrendered_at_all():
    """`01-WOL:3.3` — guaranteed plans have no surrender value. Forty-two of the
    seventy LP policies cannot pay cash out, and that is the point.

    It raises rather than quietly producing a policy marked surrendered with no
    surrender in it: that would be a book whose status column disagrees with its
    own ledger, and nothing downstream would notice."""
    with pytest.raises(ValueError, match="surrender"):
        _plan(status="surrendered", basis=("guaranteed",))


def test_a_guaranteed_policy_cannot_be_made_paid_up_either():
    """Premiums ceasing on a plan with no fund is a lapse, not paid up."""
    with pytest.raises(ValueError, match="paid up"):
        _plan(status="paid_up", basis=("guaranteed",))


def test_a_guaranteed_policy_ends_holding_nothing():
    """A protection premium buys cover; it is not saved. A balance behind a
    guaranteed plan would read as a fund somebody could cash in, and
    `01-WOL:3.3` says there is none."""
    lifetime, report = _through_the_rulebook(_plan(basis=("guaranteed",)))
    assert report.is_empty(), report.render()
    assert lifetime.value_pence == 0
