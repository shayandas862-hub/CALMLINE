"""How a whole-of-life policy stops — lapse, paid up, and death.

`01-WOL:3.10` gives lapse exactly:

> **Grace period 30 days** from a missed premium — cover continues […]
> Guaranteed plans **lapse without value** after the grace period. Unit-linked
> plans first continue by cancelling units to meet the cost of cover until the
> fund is exhausted, then lapse.

`01-WOL:3.3` gives the death benefit: "the greater of the sum assured and
(unit-linked) the bid value of units (often 101% of fund value)".

`05-OPS:9.9` gives the claim timetable, in business days: acknowledge
notification **1**, issue requirements **3**, assess **5** from full documents,
pay **5** from assessment. And `05-OPS:9.1`: "**Notification ≠ claim**; pay only
a verified claimant" — which is why death, claim and payment are three dated
events rather than one.

**Paid up is the corpus's own gap.** `paid-up` appears once in the whole
corpus — in the data dictionary's list of permitted statuses (`05-OPS:19`) — and
no document says what makes a policy paid up, for any product. The mechanic used
here is a recorded decision rather than an assumption made in silence.
"""

from __future__ import annotations

from datetime import date

import pytest

from world.lifetimes.wholeoflife.endings import (
    CLAIM_WORKING_DAYS,
    GRACE_PERIOD_DAYS,
    can_be_made_paid_up,
    claim_sequence,
    lapse_on,
)

# The MISSED premium's due date — `01-WOL:3.10` runs the grace from the missed
# premium, not from the last one paid. The first version of `lapse_on` took the
# last-paid date, and the caller's clamp then put every guaranteed lapse a year
# adrift of its own stated 30-day grace.
MISSED_DUE = date(2019, 3, 1)


# ── lapse ────────────────────────────────────────────────────────────────
def test_the_grace_period_is_the_corpus_thirty_days():
    assert GRACE_PERIOD_DAYS == 30


def test_a_guaranteed_plan_lapses_the_day_the_grace_period_ends():
    """`01-WOL:3.10` — guaranteed plans lapse without value after the grace
    period, thirty days from the missed premium. The reason names the due date
    so the arithmetic is checkable from the event alone."""
    on, reason = lapse_on(MISSED_DUE, basis=("guaranteed",),
                          fund_value_pence=0, monthly_cost_pence=50_00)
    assert on == date(2019, 3, 31)
    assert "grace" in reason.lower()


def test_a_guaranteed_plan_lapses_without_value_even_holding_money():
    """A guaranteed plan has no unit fund by definition (`01-WOL:3.3`), so a
    balance behind one cannot keep cover going — it is not units to cancel."""
    on, _ = lapse_on(MISSED_DUE, basis=("guaranteed",),
                     fund_value_pence=10_000_00, monthly_cost_pence=50_00)
    assert on == date(2019, 3, 31)


def test_a_unit_linked_plan_survives_on_its_fund_before_lapsing():
    """`01-WOL:3.10` — units are cancelled to meet the cost of cover until the
    fund is exhausted. £600 of fund at £50 a month buys twelve more months."""
    on, reason = lapse_on(MISSED_DUE, basis=("reviewable", "unit_linked"),
                          fund_value_pence=600_00, monthly_cost_pence=50_00)
    assert on > date(2019, 3, 31)
    assert "fund" in reason.lower()


def test_a_bigger_fund_keeps_a_unit_linked_plan_alive_longer():
    small, _ = lapse_on(MISSED_DUE, basis=("unit_linked",),
                        fund_value_pence=600_00, monthly_cost_pence=50_00)
    large, _ = lapse_on(MISSED_DUE, basis=("unit_linked",),
                        fund_value_pence=6_000_00, monthly_cost_pence=50_00)
    assert large > small


def test_a_unit_linked_plan_with_no_fund_lapses_like_a_guaranteed_one():
    on, _ = lapse_on(MISSED_DUE, basis=("unit_linked",),
                     fund_value_pence=0, monthly_cost_pence=50_00)
    assert on == date(2019, 3, 31)


def test_a_lapse_always_carries_a_date_and_a_reason():
    on, reason = lapse_on(MISSED_DUE, basis=("guaranteed",),
                          fund_value_pence=0, monthly_cost_pence=50_00)
    assert isinstance(on, date)
    assert reason.strip()


def test_a_lapse_is_never_dated_before_the_missed_due():
    on, _ = lapse_on(MISSED_DUE, basis=("guaranteed",),
                     fund_value_pence=0, monthly_cost_pence=50_00)
    assert on > MISSED_DUE


# ── paid up ──────────────────────────────────────────────────────────────
def test_only_a_unit_linked_plan_can_be_made_paid_up():
    """The corpus never defines paid up. The mechanic adopted — premiums cease
    by agreement and the existing fund carries the cost of reduced cover —
    needs a fund, and `01-WOL:3.3` says guaranteed plans have none."""
    assert can_be_made_paid_up(("unit_linked",), fund_value_pence=5_000_00)
    assert not can_be_made_paid_up(("guaranteed",), fund_value_pence=5_000_00)


def test_a_reviewable_plan_without_units_cannot_be_made_paid_up():
    """Reviewable is a *premium* basis, not an investment one. Without units
    there is nothing to sustain cover once premiums stop."""
    assert not can_be_made_paid_up(("reviewable",), fund_value_pence=5_000_00)


def test_a_unit_linked_plan_with_an_empty_fund_cannot_be_made_paid_up():
    """Nothing left to sustain cover is a lapse (`01-WOL:3.10`), not paid up."""
    assert not can_be_made_paid_up(("unit_linked",), fund_value_pence=0)


# ── death, claim, payment ────────────────────────────────────────────────
def test_the_claim_timetable_is_the_corpus_business_days():
    """`05-OPS:9.9` — 1 + 3 + 5 + 5."""
    assert CLAIM_WORKING_DAYS == (1, 3, 5, 5)


def test_death_then_claim_then_payment_in_that_order():
    """The card's done-when, and `05-OPS:9.1`: notification is not a claim."""
    events, movements = claim_sequence(
        date(2024, 3, 11), sum_assured_pence=400_000_00,
        fund_value_pence=46_210_00, notified_after_days=9)

    assert [e.kind for e in events] == ["death", "claim_registered",
                                        "claim_paid"]
    assert events[0].on < events[1].on < events[2].on
    assert [m.kind for m in movements] == ["claim_payment"]


def test_nothing_is_dated_after_the_payment():
    events, movements = claim_sequence(
        date(2024, 3, 11), sum_assured_pence=400_000_00,
        fund_value_pence=0, notified_after_days=9)
    paid_on = events[-1].on
    assert all(e.on <= paid_on for e in events)
    assert all(m.on <= paid_on for m in movements)


def test_the_payment_is_dated_the_day_the_claim_was_paid():
    events, movements = claim_sequence(
        date(2024, 3, 11), sum_assured_pence=400_000_00,
        fund_value_pence=0, notified_after_days=9)
    assert movements[0].on == events[-1].on


def test_the_death_benefit_is_the_greater_of_cover_and_the_fund():
    """`01-WOL:3.3` — "the greater of the sum assured and (unit-linked) the bid
    value of units (often 101% of fund value)". A large fund beats small cover."""
    _, small_fund = claim_sequence(date(2024, 3, 11),
                                   sum_assured_pence=400_000_00,
                                   fund_value_pence=1_000_00,
                                   notified_after_days=9)
    assert small_fund[0].amount_pence == 400_000_00

    _, large_fund = claim_sequence(date(2024, 3, 11),
                                   sum_assured_pence=10_000_00,
                                   fund_value_pence=100_000_00,
                                   notified_after_days=9)
    assert large_fund[0].amount_pence == 101_000_00  # 101% of the fund


def test_the_claim_payment_is_always_whole_pence():
    _, movements = claim_sequence(date(2024, 3, 11), sum_assured_pence=1,
                                  fund_value_pence=99_999,
                                  notified_after_days=3)
    assert isinstance(movements[0].amount_pence, int)


def test_a_claim_is_never_paid_on_a_weekend():
    """`05-OPS:9.9` counts business days, so the arithmetic has to as well."""
    for offset in range(0, 21):
        events, _ = claim_sequence(date(2024, 3, 4), sum_assured_pence=1_00,
                                   fund_value_pence=0,
                                   notified_after_days=offset)
        assert events[-1].on.weekday() < 5


def test_a_notification_before_the_death_is_refused():
    with pytest.raises(ValueError):
        claim_sequence(date(2024, 3, 11), sum_assured_pence=1_00,
                       fund_value_pence=0, notified_after_days=-1)


def test_the_same_death_always_produces_the_same_sequence():
    args = dict(sum_assured_pence=400_000_00, fund_value_pence=46_210_00,
                notified_after_days=9)
    assert claim_sequence(date(2024, 3, 11), **args) == \
           claim_sequence(date(2024, 3, 11), **args)
