"""Whole-of-life premiums — a year at a time, until the year something happened.

`01-WOL:3.1` — "Premiums: monthly or annual Direct Debit". A thirty-two-year
policy collecting monthly is 384 ledger rows, and the assistant has to *read* a
policy's history to answer a question about it. A clean year posts as one line.

**A year containing a missed payment is itemised in full**, because the gap is
the event. Summarising it would erase the only thing anybody would ring about:
"eleven premiums were collected" is not an answer to "which one did I miss?"
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Sequence

from world.lifetimes.timeline import Movement

MONTHS_IN_YEAR = 12
PREMIUM_FREQUENCIES = frozenset({"monthly", "yearly"})


def annual_premium_pence(premium_pence: int, frequency: str) -> int:
    """What a year of this premium costs."""
    if frequency not in PREMIUM_FREQUENCIES:
        raise ValueError(
            f"unknown premium frequency {frequency!r} — `01-WOL:3.1` offers "
            f"{sorted(PREMIUM_FREQUENCIES)}")
    return premium_pence * MONTHS_IN_YEAR if frequency == "monthly" else premium_pence


def month_after(day: date) -> date:
    """The next monthly due date — one collection step on, same day-of-month.

    Public because the lapse needs it: `01-WOL:3.10` runs the grace from the
    **missed** premium, and on a monthly plan that is the month after the last
    one collected.
    """
    return _collection_date(day, 1)


def _collection_date(year_start: date, offset: int) -> date:
    """``offset`` months after ``year_start``, keeping the day of the month.

    A 31st collection date in a 30-day month collects on the last day of it,
    which is what a Direct Debit does rather than skipping the month.
    """
    month_index = year_start.month - 1 + offset
    year = year_start.year + month_index // MONTHS_IN_YEAR
    month = month_index % MONTHS_IN_YEAR + 1
    _, last_day = monthrange(year, month)
    return date(year, month, min(year_start.day, last_day))


def premium_movements(year_start: date, *, premium_pence: int, frequency: str,
                      missed_months: Sequence[int] = ()) -> tuple[Movement, ...]:
    """One policy year's premiums, starting ``year_start``.

    Clean years summarise; a year with a gap itemises. Both add to the same
    figure, so the two representations stay comparable.
    """
    collections = (MONTHS_IN_YEAR if frequency == "monthly" else 1)
    for offset in missed_months:
        if not 0 <= offset < collections:
            raise ValueError(
                f"missed payment {offset} is outside the {collections} "
                f"collection(s) in a {frequency} policy year")
    missed = set(missed_months)

    if not missed:
        total = annual_premium_pence(premium_pence, frequency)
        reason = (f"{MONTHS_IN_YEAR} monthly premiums, collected"
                  if frequency == "monthly" else "annual premium, collected")
        return (Movement(on=year_start, kind="premium", amount_pence=total,
                         reason=reason),)

    return tuple(
        Movement(on=_collection_date(year_start, offset), kind="premium",
                 amount_pence=premium_pence,
                 reason=f"premium collected ({offset + 1} of {collections})")
        for offset in range(collections)
        if offset not in missed
    )
