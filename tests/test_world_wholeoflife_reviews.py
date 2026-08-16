"""Premium reviews and indexation — the two things that change what is charged.

`01-WOL:3.8` is unusually specific and is quoted rather than paraphrased:

> At year 10 and 5-yearly after, Aldercrest tests whether the unit fund plus
> current premiums can sustain the cost of cover to age 100 on the review basis.
> Outcomes: (a) premiums unchanged; (b) premium increase required; (c) if the
> customer declines an increase, the **sum assured is reduced** to the
> supportable level; (d) on later reviews a plan can become unsustainable — the
> customer may pay more, reduce cover, or let the plan run until the fund is
> exhausted (it then lapses without value). **No new underwriting at review.**

The `01-WOL` specimen confirms the schedule: started 2016-05-01, next review
2026-05-01, labelled "year-10".

Indexation is `01-WOL:3.1` — "increasing/indexed (RPI or fixed % p.a.)" — with
an **annual accept/decline** (§5, servicing). The specimen declined 2024 and
2025, which is why `Indexation.declined_years` exists.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.records.products import Indexation
from world.lifetimes.wholeoflife.reviews import (
    FIRST_REVIEW_YEAR,
    REVIEW_INTERVAL_YEARS,
    REVIEW_OUTCOMES,
    indexation_dates,
    indexed_pence,
    review_dates,
    reviewed_terms,
)

START = date(2016, 5, 1)


# ── the review schedule ──────────────────────────────────────────────────
def test_the_first_review_is_at_year_ten():
    """`01-WOL:3.8`, and the specimen: start 2016-05-01 → review 2026-05-01."""
    assert FIRST_REVIEW_YEAR == 10
    assert review_dates(START, born=date(2026, 7, 28))[0] == date(2026, 5, 1)


def test_reviews_run_five_yearly_after_the_tenth():
    assert REVIEW_INTERVAL_YEARS == 5
    dates = review_dates(date(1994, 6, 15), born=date(2026, 7, 28))
    assert dates == (date(2004, 6, 15), date(2009, 6, 15), date(2014, 6, 15),
                     date(2019, 6, 15), date(2024, 6, 15))


def test_a_policy_younger_than_ten_years_has_never_been_reviewed():
    assert review_dates(date(2020, 1, 1), born=date(2026, 7, 28)) == ()


def test_no_review_is_dated_after_the_worlds_birth_date():
    dates = review_dates(date(1994, 6, 15), born=date(2026, 7, 28))
    assert all(d <= date(2026, 7, 28) for d in dates)


def test_a_thirty_two_year_policy_has_had_five_reviews():
    """The card's own example: a policy opened in the nineties showing its
    reviews. Five is what `01-WOL:3.8` produces, not a number chosen here."""
    assert len(review_dates(date(1994, 6, 15), born=date(2026, 7, 28))) == 5


# ── what a review does ───────────────────────────────────────────────────
def test_the_four_outcomes_are_the_four_the_corpus_names():
    assert REVIEW_OUTCOMES == frozenset({
        "unchanged", "premium_increased", "cover_reduced", "unsustainable"})


def test_an_unchanged_review_changes_nothing():
    premium, sum_assured = reviewed_terms(
        212_40, 400_000_00, outcome="unchanged")
    assert (premium, sum_assured) == (212_40, 400_000_00)


def test_a_premium_increase_raises_the_premium_and_leaves_cover_alone():
    """`01-WOL:3.8`(b) — the customer pays more for the same cover."""
    premium, sum_assured = reviewed_terms(
        212_40, 400_000_00, outcome="premium_increased")
    assert premium > 212_40
    assert sum_assured == 400_000_00


def test_declining_an_increase_reduces_the_cover_not_the_premium():
    """`01-WOL:3.8`(c) — "the sum assured is reduced to the supportable level".
    Getting this backwards would be the classic error: the customer who says no
    keeps paying what they paid, and gets less."""
    premium, sum_assured = reviewed_terms(
        212_40, 400_000_00, outcome="cover_reduced")
    assert premium == 212_40
    assert sum_assured < 400_000_00


def test_an_unsustainable_review_reduces_cover_further_than_a_declined_one():
    """`01-WOL:3.8`(d) — the plan can no longer be sustained as it stands."""
    _, declined = reviewed_terms(212_40, 400_000_00, outcome="cover_reduced")
    _, unsustainable = reviewed_terms(212_40, 400_000_00,
                                      outcome="unsustainable")
    assert unsustainable < declined


def test_no_review_outcome_ever_reduces_cover_below_nothing():
    for outcome in REVIEW_OUTCOMES:
        _, sum_assured = reviewed_terms(212_40, 1_00, outcome=outcome)
        assert sum_assured >= 0


def test_a_review_result_is_always_whole_pence():
    for outcome in REVIEW_OUTCOMES:
        premium, sum_assured = reviewed_terms(212_43, 399_999_99,
                                              outcome=outcome)
        assert isinstance(premium, int) and isinstance(sum_assured, int)


def test_an_unknown_outcome_raises_rather_than_leaving_terms_untouched():
    with pytest.raises(ValueError):
        reviewed_terms(212_40, 400_000_00, outcome="renegotiated")


# ── indexation ───────────────────────────────────────────────────────────
def test_indexation_off_means_no_indexation_dates_at_all():
    assert indexation_dates(START, born=date(2026, 7, 28),
                            indexation=Indexation(on=False)) == ()


def test_indexation_falls_on_every_policy_anniversary():
    dates = indexation_dates(date(2020, 3, 1), born=date(2024, 6, 1),
                             indexation=Indexation(on=True))
    assert dates == (date(2021, 3, 1), date(2022, 3, 1), date(2023, 3, 1),
                     date(2024, 3, 1))


def test_a_declined_year_is_skipped():
    """The specimen declined 2024 and 2025 — an annual accept/decline, so a
    declined year raises nothing and the policy carries on."""
    dates = indexation_dates(date(2020, 3, 1), born=date(2026, 7, 28),
                             indexation=Indexation(on=True,
                                                   declined_years=(2024, 2025)))
    assert date(2024, 3, 1) not in dates
    assert date(2025, 3, 1) not in dates
    assert date(2026, 3, 1) in dates


def test_indexation_raises_an_amount_by_whole_pence():
    """5% of £400,000 is £20,000 exactly — and integer basis points keep it so."""
    assert indexed_pence(400_000_00, rate_bp=500) == 420_000_00


def test_indexation_never_introduces_a_fractional_penny():
    for amount in (1, 7, 99, 212_40, 399_999_99):
        raised = indexed_pence(amount, rate_bp=317)
        assert isinstance(raised, int)
        assert raised >= amount


def test_indexation_raises_both_the_cover_and_the_premium():
    """`01-WOL:3.1` — an indexed plan increases cover, and the premium follows.
    Raising cover without the premium would be a free increase every year."""
    assert indexed_pence(400_000_00, rate_bp=500) > 400_000_00
    assert indexed_pence(212_40, rate_bp=500) > 212_40
