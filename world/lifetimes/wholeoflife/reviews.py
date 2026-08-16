"""Premium reviews and indexation — the two things that change what is charged.

`01-WOL:3.8`, quoted rather than paraphrased because the outcomes are easy to
get backwards:

> At year 10 and 5-yearly after, Aldercrest tests whether the unit fund plus
> current premiums can sustain the cost of cover to age 100 on the review basis.
> Outcomes: (a) premiums unchanged; (b) premium increase required; (c) if the
> customer declines an increase, the **sum assured is reduced** to the
> supportable level; (d) on later reviews a plan can become unsustainable […]
> **No new underwriting at review.**

The trap is (c). The customer who says no to an increase keeps paying what they
paid and gets *less cover* — not a smaller premium.

Indexation is `01-WOL:3.1` — "increasing/indexed (RPI or fixed % p.a.)" — with
an annual accept/decline (`01-WOL:5`, servicing). The `01-WOL` specimen declined
2024 and 2025, which is what `Indexation.declined_years` is for.
"""

from __future__ import annotations

from datetime import date

from src.records.products import Indexation
from world.lifetimes.markets import anniversary

FIRST_REVIEW_YEAR = 10
REVIEW_INTERVAL_YEARS = 5

REVIEW_OUTCOMES = frozenset({
    "unchanged",          # `01-WOL:3.8`(a)
    "premium_increased",  # (b)
    "cover_reduced",      # (c) — the customer declined the increase
    "unsustainable",      # (d)
})

# How much each outcome moves the terms. Aldercrest's own review basis is not
# published in the corpus, so these are this build's figures, chosen to be
# visible in a history without being alarming.
PREMIUM_INCREASE_BP = 1_800      # +18% at a review that needs more premium
COVER_REDUCTION_BP = 2_500       # -25% where the customer declined
UNSUSTAINABLE_REDUCTION_BP = 4_500

# The default indexation rate. `01-WOL:3.1` offers "RPI or fixed % p.a." and
# names no figure; 3% is the fixed-rate option this build uses throughout.
DEFAULT_INDEXATION_BP = 300


def review_dates(start: date, *, born: date) -> tuple[date, ...]:
    """Every premium review this policy has had, oldest first."""
    dates = []
    year = FIRST_REVIEW_YEAR
    while True:
        due = anniversary(start, start.year + year)
        if due > born:
            return tuple(dates)
        dates.append(due)
        year += REVIEW_INTERVAL_YEARS


def reviewed_terms(premium_pence: int, sum_assured_pence: int, *,
                   outcome: str) -> tuple[int, int]:
    """The premium and sum assured after a review, in that order."""
    if outcome not in REVIEW_OUTCOMES:
        raise ValueError(
            f"unknown review outcome {outcome!r} — `01-WOL:3.8` names "
            f"{sorted(REVIEW_OUTCOMES)}")
    if outcome == "unchanged":
        return premium_pence, sum_assured_pence
    if outcome == "premium_increased":
        return (premium_pence + premium_pence * PREMIUM_INCREASE_BP // 10_000,
                sum_assured_pence)
    reduction = (COVER_REDUCTION_BP if outcome == "cover_reduced"
                 else UNSUSTAINABLE_REDUCTION_BP)
    reduced = sum_assured_pence - sum_assured_pence * reduction // 10_000
    return premium_pence, max(0, reduced)


def indexation_dates(start: date, *, born: date,
                     indexation: Indexation) -> tuple[date, ...]:
    """Every anniversary this policy's cover was indexed on.

    A declined year raises nothing and the policy carries on — the option is an
    annual accept/decline, not a switch that turns indexation off for good.
    """
    if not indexation.on:
        return ()
    declined = set(indexation.declined_years)
    return tuple(
        due for year in range(start.year + 1, born.year + 1)
        if (due := anniversary(start, year)) <= born and due.year not in declined
    )


def indexed_pence(amount_pence: int, *, rate_bp: int = DEFAULT_INDEXATION_BP) -> int:
    """``amount_pence`` raised by ``rate_bp`` basis points, in whole pence.

    Rounds **up** on the fraction, unlike a charge: this raises a sum assured
    and a premium together, and rounding the cover down while rounding the
    premium up would quietly make the policy worse value every single year.
    """
    if amount_pence <= 0 or rate_bp <= 0:
        return amount_pence
    increase = -(-amount_pence * rate_bp // 10_000)
    return amount_pence + increase
