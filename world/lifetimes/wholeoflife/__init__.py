"""Lifelong Protection — premiums, reviews, indexation, lapse, and claim.

Four mechanics, four modules, because each one grows into a file of its own if
allowed to share:

- `premiums` — a year at a time, until the year something happened
- `reviews`  — `01-WOL:3.8`'s four outcomes, and indexation
- `endings`  — lapse, paid up, and death → claim → payment
- `plan`     — the walker that composes them into one policy's history
"""

from __future__ import annotations

from world.lifetimes.wholeoflife.endings import (
    CLAIM_WORKING_DAYS,
    GRACE_PERIOD_DAYS,
    can_be_made_paid_up,
    claim_sequence,
    death_benefit_pence,
    lapse_on,
)
from world.lifetimes.wholeoflife.plan import WholeOfLifePlan, play_whole_of_life
from world.lifetimes.wholeoflife.premiums import (
    annual_premium_pence,
    premium_movements,
)
from world.lifetimes.wholeoflife.reviews import (
    REVIEW_OUTCOMES,
    indexation_dates,
    indexed_pence,
    review_dates,
    reviewed_terms,
)

__all__ = [
    "CLAIM_WORKING_DAYS", "GRACE_PERIOD_DAYS", "REVIEW_OUTCOMES",
    "WholeOfLifePlan", "annual_premium_pence", "can_be_made_paid_up",
    "claim_sequence", "death_benefit_pence", "indexation_dates",
    "indexed_pence", "lapse_on", "play_whole_of_life", "premium_movements",
    "review_dates", "reviewed_terms",
]
