"""Business days, because the operations manual counts in them.

`05-OPS:9.9` sets the claim timetable in business days — acknowledge 1, issue
requirements 3, assess 5, pay 5 — and the SLA table (`05-OPS:18`) does the same
for every other kind of work. Counting them as calendar days would date a claim
payment to a Sunday.

**Bank holidays are not modelled**, and that is a stated simplification rather
than an oversight: the UK's eight vary by nation and by year, a table of them
back to 1994 would be a third of this file, and the only consequence is that a
handful of dates across two hundred policies fall a day earlier than a real
operations team would have managed.
"""

from __future__ import annotations

from datetime import date, timedelta

SATURDAY = 5


def is_working_day(day: date) -> bool:
    """Monday to Friday."""
    return day.weekday() < SATURDAY


def next_working_day(day: date) -> date:
    """``day`` itself if it is one, otherwise the next Monday."""
    while not is_working_day(day):
        day += timedelta(days=1)
    return day


def add_working_days(start: date, days: int) -> date:
    """``days`` business days after ``start``.

    Zero lands on ``start`` if it is a working day, and on the next one if it
    is not — "nothing happens at the weekend" rather than "nothing happens".
    """
    if days < 0:
        raise ValueError(f"cannot count {days} working days backwards")
    day = next_working_day(start)
    for _ in range(days):
        day = next_working_day(day + timedelta(days=1))
    return day
