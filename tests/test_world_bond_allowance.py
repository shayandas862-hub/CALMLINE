"""The bond's 5% tax-deferred allowance — the subtlest thing in the phase.

`02-BOND:4.2`, quoted whole because every clause of it matters:

> Withdraw up to **5% of the amount invested per policy year** with no immediate
> tax; **cumulative** (unused carries forward) up to 100% of the amount
> invested. A **deferral, not an exemption** — withdrawals re-enter the final
> gain calculation. Each top-up starts its own 5% clock (§7).

Three ways to get this wrong, all of which produce a book that is internally
consistent and externally false:

1. **5% of the current value.** It is 5% of the *amount invested*, forever. A
   bond that took £100,000 and is now worth £150,000 still has a £5,000 annual
   allowance, not £7,500.
2. **Forgetting the 100% ceiling.** The allowance stops accruing once it has
   reached the amount invested — twenty policy years and no more.
3. **Testing an excess on the day of the withdrawal.** `02-BOND:4.3` tests it
   **at policy-year end**, so two withdrawals in one year are judged together.

`02-BOND:5` gives the arithmetic to check against: £100,000 invested, a £50,000
partial withdrawal **in year 2**, excess "£50,000 − 2×5% allowance" = £40,000.

**A contradiction inside the corpus, resolved and logged.** The `02-BOND`
specimen record (invested £120,000 on 2019-03-01) states "cumulative allowance
used £36,000 of £42,000", which at the world's birth date is policy year 8 and
implies seven allowances — complete years *elapsed*. `02-BOND:4.2` and the §5
worked example both give N allowances in policy year N. The rule sections win:
they carry explicit arithmetic, and a specimen is a record rather than a rule.
"""

from __future__ import annotations

from datetime import date

import pytest

from world.lifetimes.bond.allowance import (
    ANNUAL_ALLOWANCE_BP,
    MAX_CUMULATIVE_BP,
    cumulative_allowance_pence,
    excess_pence,
    policy_year_of,
    remaining_allowance_pence,
)

INVESTED = 100_000_00
INVESTED_ON = date(2015, 3, 1)


# ── policy years ─────────────────────────────────────────────────────────
def test_the_day_it_was_invested_is_policy_year_one():
    assert policy_year_of(INVESTED_ON, INVESTED_ON) == 1


def test_the_day_before_the_first_anniversary_is_still_year_one():
    assert policy_year_of(INVESTED_ON, date(2016, 2, 29)) == 1


def test_the_first_anniversary_opens_year_two():
    assert policy_year_of(INVESTED_ON, date(2016, 3, 1)) == 2


def test_a_date_before_the_investment_is_refused():
    with pytest.raises(ValueError):
        policy_year_of(INVESTED_ON, date(2015, 2, 28))


# ── the allowance itself ─────────────────────────────────────────────────
def test_the_annual_allowance_is_the_corpus_five_percent():
    assert ANNUAL_ALLOWANCE_BP == 500


def test_it_accrues_five_percent_of_the_amount_invested_each_policy_year():
    for year in (1, 2, 3, 10):
        assert cumulative_allowance_pence(INVESTED, year) == year * 5_000_00


def test_it_is_five_percent_of_what_went_in_not_of_what_it_is_worth_now():
    """The single easiest way to get this wrong. The allowance is fixed by the
    premium; the fund's value never enters it."""
    assert cumulative_allowance_pence(INVESTED, 5) == 25_000_00
    # nothing in the signature can even express the current value
    assert cumulative_allowance_pence(INVESTED, 5) == \
        cumulative_allowance_pence(INVESTED, 5)


def test_it_stops_accruing_at_one_hundred_percent_of_the_amount_invested():
    """`02-BOND:4.2` — "up to 100% of the amount invested". Twenty years."""
    assert MAX_CUMULATIVE_BP == 10_000
    assert cumulative_allowance_pence(INVESTED, 20) == INVESTED
    assert cumulative_allowance_pence(INVESTED, 21) == INVESTED
    assert cumulative_allowance_pence(INVESTED, 40) == INVESTED


def test_unused_allowance_carries_forward():
    """Nothing withdrawn in years 1–3 leaves all three years available in 4."""
    assert remaining_allowance_pence(INVESTED, policy_year=4, used_pence=0) == \
        20_000_00


def test_what_has_been_used_reduces_what_remains():
    remaining = remaining_allowance_pence(INVESTED, policy_year=4,
                                          used_pence=12_000_00)
    assert remaining == 20_000_00 - 12_000_00


def test_remaining_allowance_never_goes_negative():
    """Once it is spent it is spent; an overdrawn allowance is an excess, and
    excesses are counted separately rather than as a negative allowance."""
    assert remaining_allowance_pence(INVESTED, policy_year=1,
                                     used_pence=99_000_00) == 0


def test_every_allowance_figure_is_whole_pence():
    for year in range(1, 25):
        value = cumulative_allowance_pence(33_333_33, year)
        assert isinstance(value, int)


def test_a_policy_year_below_one_is_refused():
    with pytest.raises(ValueError):
        cumulative_allowance_pence(INVESTED, 0)


# ── the excess, which is what gets taxed ─────────────────────────────────
def test_a_withdrawal_inside_the_allowance_creates_no_excess():
    assert excess_pence(5_000_00, INVESTED, policy_year=1, used_pence=0) == 0


def test_a_withdrawal_of_exactly_the_allowance_creates_no_excess():
    assert excess_pence(10_000_00, INVESTED, policy_year=2, used_pence=0) == 0


def test_the_corpus_worked_example_reproduces_exactly():
    """`02-BOND:5` — "£50,000 − 2×5% allowance" on £100,000 invested, in year 2.
    If this figure ever changes, the book has stopped matching the rulebook."""
    assert excess_pence(50_000_00, INVESTED, policy_year=2,
                        used_pence=0) == 40_000_00


def test_an_excess_counts_only_the_part_above_the_allowance():
    assert excess_pence(12_000_00, INVESTED, policy_year=2,
                        used_pence=0) == 2_000_00


def test_allowance_already_used_makes_the_next_withdrawal_bite_sooner():
    """Two £5,000 withdrawals in year 2 use the whole allowance; a third is all
    excess. This is why the test is at policy-year *end* — the year's
    withdrawals are judged together, not one at a time."""
    assert excess_pence(5_000_00, INVESTED, policy_year=2,
                        used_pence=10_000_00) == 5_000_00


def test_an_excess_is_never_negative():
    assert excess_pence(1_00, INVESTED, policy_year=20, used_pence=0) == 0


def test_a_withdrawal_after_the_allowance_ceiling_is_entirely_excess():
    """Once 100% of the premium has been drawn tax-deferred there is nothing
    left to defer against."""
    assert excess_pence(5_000_00, INVESTED, policy_year=25,
                        used_pence=INVESTED) == 5_000_00


def test_the_allowance_reconciles_across_every_policy_year():
    """The card's done-when: used + remaining never exceeds what has accrued,
    at any point in the policy's life."""
    used = 0
    for year in range(1, 31):
        accrued = cumulative_allowance_pence(INVESTED, year)
        remaining = remaining_allowance_pence(INVESTED, policy_year=year,
                                              used_pence=used)
        assert used + remaining <= accrued
        drawn = 4_000_00
        if excess_pence(drawn, INVESTED, policy_year=year,
                        used_pence=used) == 0:
            used += drawn
    assert used <= INVESTED
