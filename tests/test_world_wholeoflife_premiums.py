"""Whole-of-life premiums — a year at a time, until the year something happened.

`01-WOL:3.1` — "Premiums: monthly or annual Direct Debit". A thirty-two-year
policy collecting monthly is 384 ledger rows, and the assistant has to *read* a
policy's history to answer a question about it. So a clean year posts as one
summary line.

**A year containing a missed payment is itemised in full**, because the gap is
the event. Summarising it would erase the only thing anybody would ring about,
and "eleven premiums were collected" is not an answer to "which one did I miss?"

`01-WOL:3.10` gives the arrears mechanics: a **30-day grace period** from a
missed premium, cover continuing throughout.
"""

from __future__ import annotations

from datetime import date

import pytest

from world.lifetimes.wholeoflife.premiums import (
    MONTHS_IN_YEAR,
    annual_premium_pence,
    premium_movements,
)

YEAR_START = date(2016, 5, 1)
MONTHLY = 212_40  # the `01-WOL` specimen's own premium: £212.40/month


def _movements(missed=(), premium_pence=MONTHLY, frequency="monthly"):
    return premium_movements(YEAR_START, premium_pence=premium_pence,
                             frequency=frequency, missed_months=missed)


# ── what a year costs ────────────────────────────────────────────────────
def test_a_monthly_premium_costs_twelve_of_itself_over_a_year():
    assert annual_premium_pence(MONTHLY, "monthly") == MONTHLY * MONTHS_IN_YEAR


def test_a_yearly_premium_costs_itself():
    assert annual_premium_pence(2_548_80, "yearly") == 2_548_80


def test_an_unknown_frequency_raises_rather_than_assuming_monthly():
    """`01-WOL:3.1` offers two. A third would be a policy nobody sold."""
    with pytest.raises(ValueError):
        annual_premium_pence(MONTHLY, "weekly")


# ── the clean year ───────────────────────────────────────────────────────
def test_a_clean_year_posts_as_one_summary_line():
    movements = _movements()
    assert len(movements) == 1
    assert movements[0].kind == "premium"
    assert movements[0].amount_pence == MONTHLY * 12
    assert movements[0].on == YEAR_START


def test_a_summary_line_says_how_many_premiums_it_stands_for():
    """A single £2,548.80 row with no explanation is unreadable a decade later."""
    (movement,) = _movements()
    assert "12" in movement.reason


def test_a_yearly_payer_posts_one_line_that_is_not_a_summary_of_twelve():
    (movement,) = _movements(premium_pence=2_548_80, frequency="yearly")
    assert movement.amount_pence == 2_548_80


# ── the year with a gap ──────────────────────────────────────────────────
def test_a_year_with_a_missed_payment_is_itemised_in_full():
    """The gap is the event, so every month in that year posts individually."""
    movements = _movements(missed=(6,))
    assert len(movements) == MONTHS_IN_YEAR - 1
    assert all(m.amount_pence == MONTHLY for m in movements)


def test_the_missed_month_is_visible_as_an_absence():
    # Arrange / Act — the seventh month of the policy year is missed
    movements = _movements(missed=(6,))

    # Assert — November 2016 is the month that never posted
    assert date(2016, 11, 1) not in [m.on for m in movements]
    assert date(2016, 10, 1) in [m.on for m in movements]
    assert date(2016, 12, 1) in [m.on for m in movements]


def test_each_itemised_month_falls_on_its_own_collection_date():
    movements = _movements(missed=(0,))
    assert [m.on for m in movements] == [
        date(2016, 6, 1), date(2016, 7, 1), date(2016, 8, 1),
        date(2016, 9, 1), date(2016, 10, 1), date(2016, 11, 1),
        date(2016, 12, 1), date(2017, 1, 1), date(2017, 2, 1),
        date(2017, 3, 1), date(2017, 4, 1),
    ]


def test_several_missed_months_all_leave_gaps():
    movements = _movements(missed=(2, 5, 9))
    assert len(movements) == MONTHS_IN_YEAR - 3


def test_a_year_where_every_payment_was_missed_posts_nothing():
    """Nothing was collected, so nothing is a premium. What happens next is
    lapse (`01-WOL:3.10`), and that is not this module's job."""
    assert _movements(missed=tuple(range(12))) == ()


def test_a_missed_month_out_of_range_is_refused_rather_than_ignored():
    """A silently ignored index would produce a policy whose history is wrong
    in a way nothing downstream could detect."""
    with pytest.raises(ValueError):
        _movements(missed=(12,))


def test_a_yearly_payer_who_missed_the_one_payment_posts_nothing():
    assert _movements(missed=(0,), premium_pence=2_548_80,
                      frequency="yearly") == ()


# ── exactness ────────────────────────────────────────────────────────────
def test_every_premium_is_a_whole_number_of_pence():
    for movement in _movements(missed=(3,)):
        assert isinstance(movement.amount_pence, int)


def test_the_summary_equals_the_sum_of_the_months_it_replaces():
    """The two representations must agree to the penny, or a year with a gap
    and a year without would not be comparable."""
    clean = _movements()
    itemised = premium_movements(YEAR_START, premium_pence=MONTHLY,
                                 frequency="monthly", missed_months=(0,))
    assert clean[0].amount_pence == sum(
        m.amount_pence for m in itemised) + MONTHLY


def test_the_same_year_always_produces_the_same_movements():
    assert _movements(missed=(4,)) == _movements(missed=(4,))
