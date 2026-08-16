"""When growth and charges post — annually, on the date each product reckons by.

Never monthly. A thirty-two-year policy deducting a charge every month is four
hundred ledger rows nobody can read, and the assistant has to *read* a policy's
history to answer a question about it.

Which annual date differs by product, and each choice comes from the corpus
rather than from tidiness:

- **Horizon Bond** — the **policy anniversary**, because `02-BOND:4.2` runs the
  5% tax-deferred allowance on *policy years*. Any other anchor would make the
  allowance year and the charging year disagree.
- **Retirement Account** — **6 April**, the UK tax year start. The `03-PEN`
  sample record issues its annual statement on `2026-04-06`, and the annual
  allowance (`03-PEN:4.1`) is a tax-year thing.
- **Lifelong Protection** — the **policy anniversary**, because premiums,
  premium reviews and indexation all reckon from it (`01-WOL:3.1`).
"""

from __future__ import annotations

from datetime import date

import pytest

from world import WORLD_BIRTH_DATE
from world.lifetimes.markets import statement_dates


def test_a_bond_reckons_by_its_own_policy_anniversary():
    dates = statement_dates("horizon_bond", date(2019, 3, 1), born=date(2023, 6, 1))
    assert dates == (date(2020, 3, 1), date(2021, 3, 1), date(2022, 3, 1),
                     date(2023, 3, 1))


def test_a_whole_of_life_policy_reckons_by_its_own_anniversary():
    dates = statement_dates("lifelong_protection", date(1998, 11, 12),
                            born=date(2001, 12, 1))
    assert dates == (date(1999, 11, 12), date(2000, 11, 12), date(2001, 11, 12))


def test_a_pension_reckons_by_the_tax_year_not_its_own_anniversary():
    """`03-PEN` sample: annual statement issued 2026-04-06. The dates land on
    6 April regardless of when in the year the member joined."""
    dates = statement_dates("retirement_account", date(2019, 9, 30),
                            born=date(2022, 5, 1))
    assert dates == (date(2021, 4, 6), date(2022, 4, 6))


def test_the_first_pension_statement_waits_for_the_first_anniversary():
    """A statement covering three weeks is not an annual statement. A member
    joining on 1 April does not get one five days later — the first 6 April
    *after* the first anniversary is the first that reports a real year."""
    dates = statement_dates("retirement_account", date(2019, 4, 1),
                            born=date(2021, 12, 31))
    assert dates == (date(2020, 4, 6), date(2021, 4, 6))


def test_nothing_posts_on_the_day_the_policy_started():
    """Nothing has happened yet — there is no year to report on."""
    start = date(2019, 3, 1)
    assert start not in statement_dates("horizon_bond", start,
                                        born=WORLD_BIRTH_DATE)


def test_nothing_posts_after_the_worlds_birth_date():
    for product, start in (("horizon_bond", date(2015, 8, 1)),
                           ("retirement_account", date(2004, 1, 1)),
                           ("lifelong_protection", date(1994, 6, 15))):
        dates = statement_dates(product, start, born=WORLD_BIRTH_DATE)
        assert all(d <= WORLD_BIRTH_DATE for d in dates)


def test_a_statement_due_on_the_birth_date_itself_still_posts():
    dates = statement_dates("horizon_bond", date(2015, 7, 28),
                            born=WORLD_BIRTH_DATE)
    assert dates[-1] == WORLD_BIRTH_DATE


def test_the_dates_are_in_order_and_never_repeat():
    dates = statement_dates("lifelong_protection", date(1994, 6, 15),
                            born=WORLD_BIRTH_DATE)
    assert list(dates) == sorted(dates)
    assert len(set(dates)) == len(dates)


def test_one_statement_a_year_and_no_more():
    """The card's rule, asserted rather than assumed: annually, never monthly."""
    start, born = date(1994, 6, 15), date(2026, 7, 28)
    dates = statement_dates("lifelong_protection", start, born=born)
    assert len(dates) == 32
    assert len({d.year for d in dates}) == len(dates)


def test_a_policy_younger_than_a_year_has_no_statement_yet():
    assert statement_dates("horizon_bond", date(2026, 1, 1),
                           born=WORLD_BIRTH_DATE) == ()


def test_a_leap_day_anniversary_falls_back_to_the_twenty_eighth():
    """29 February exists one year in four. The other three it is 28 February,
    rather than an exception that stops the policy."""
    dates = statement_dates("horizon_bond", date(2016, 2, 29),
                            born=date(2020, 12, 31))
    assert dates == (date(2017, 2, 28), date(2018, 2, 28), date(2019, 2, 28),
                     date(2020, 2, 29))


def test_an_unknown_product_raises_rather_than_guessing_a_date():
    with pytest.raises(ValueError):
        statement_dates("something_else", date(2019, 3, 1), born=WORLD_BIRTH_DATE)


def test_the_same_inputs_always_produce_the_same_dates():
    args = ("retirement_account", date(2004, 11, 3))
    assert statement_dates(*args, born=WORLD_BIRTH_DATE) == \
           statement_dates(*args, born=WORLD_BIRTH_DATE)
