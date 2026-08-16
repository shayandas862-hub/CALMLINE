"""How a whole-of-life policy stops — lapse, paid up, and death.

`01-WOL:3.10` gives lapse exactly:

> **Grace period 30 days** from a missed premium — cover continues […]
> Guaranteed plans **lapse without value** after the grace period. Unit-linked
> plans first continue by cancelling units to meet the cost of cover until the
> fund is exhausted, then lapse.

`01-WOL:3.3` gives the death benefit: "the greater of the sum assured and
(unit-linked) the bid value of units (often 101% of fund value)".

`05-OPS:9.9` gives the claim timetable in business days, and `05-OPS:9.1` gives
the reason it is three dated events rather than one: "**Notification ≠ claim**;
pay only a verified claimant."

**Paid up is the corpus's own gap.** `paid-up` appears exactly once in the whole
corpus — in the data dictionary's list of permitted statuses (`05-OPS:19`) — and
nothing anywhere says what makes a policy paid up. The mechanic adopted here is
the ordinary UK one: premiums cease **by agreement**, and the existing fund
carries the cost of reduced cover. That needs a fund, which is what distinguishes
it from lapse — where premiums stop *without* agreement and the policy dies.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Sequence

from world.lifetimes.events import LifeEvent
from world.lifetimes.timeline import Movement
from world.lifetimes.workingdays import add_working_days

GRACE_PERIOD_DAYS = 30

# `05-OPS:9.9` — acknowledge notification, issue requirements, assess from full
# documents, pay from assessment.
CLAIM_WORKING_DAYS = (1, 3, 5, 5)

# `01-WOL:3.3` — the unit-linked death benefit is "often 101% of fund value".
UNIT_LINKED_DEATH_UPLIFT_BP = 10_100

# Only a unit-linked plan holds units to cancel. Reviewable is a *premium*
# basis, not an investment one, so it has no fund behind it either.
INVESTED_BASES = frozenset({"unit_linked"})


def _has_units(basis: Sequence[str]) -> bool:
    return bool(INVESTED_BASES.intersection(basis))


def lapse_on(due_on: date, *, basis: Sequence[str],
             fund_value_pence: int, monthly_cost_pence: int) -> tuple[date, str]:
    """When this policy lapses, and why — `01-WOL:3.10`.

    ``due_on`` is **the missed premium's due date**, because that is what the
    corpus runs the grace from: "Grace period 30 days *from a missed premium*."
    The first version of this took the last *paid* date instead, and the caller
    then clamped the result up to the closing anniversary — so every guaranteed
    lapse in the book claimed a 30-day grace its own date contradicted by a
    year. The text now names the due date so the arithmetic is checkable from
    the event alone.
    """
    grace_ends = due_on + timedelta(days=GRACE_PERIOD_DAYS)
    if not _has_units(basis) or fund_value_pence <= 0 or monthly_cost_pence <= 0:
        return grace_ends, (
            f"the premium due {due_on.isoformat()} was not paid; lapsed "
            f"without value at the end of the {GRACE_PERIOD_DAYS}-day grace "
            f"period")
    months = fund_value_pence // monthly_cost_pence
    return (grace_ends + timedelta(days=30 * months), (
        f"the premium due {due_on.isoformat()} was not paid; units were "
        f"cancelled to meet the cost of cover for a further {months} month(s) "
        f"beyond the {GRACE_PERIOD_DAYS}-day grace period until the fund was "
        f"exhausted"))


def can_be_made_paid_up(basis: Sequence[str], *, fund_value_pence: int) -> bool:
    """Whether premiums can cease by agreement with cover continuing.

    Needs units to carry the cost. Without them, premiums stopping is a lapse.
    """
    return _has_units(basis) and fund_value_pence > 0


def death_benefit_pence(sum_assured_pence: int, fund_value_pence: int) -> int:
    """`01-WOL:3.3` — the greater of the cover and 101% of the fund."""
    uplifted = fund_value_pence * UNIT_LINKED_DEATH_UPLIFT_BP // 10_000
    return max(sum_assured_pence, uplifted)


def claim_sequence(died_on: date, *, sum_assured_pence: int,
                   fund_value_pence: int,
                   notified_after_days: int) -> tuple[tuple[LifeEvent, ...],
                                                      tuple[Movement, ...]]:
    """Death, claim, payment — three dated events and one movement.

    Separate because `05-OPS:9.1` makes them separate: somebody dies, somebody
    later tells the insurer, and the insurer later still pays a claimant it has
    verified. Collapsing them would lose the gap every bereavement conversation
    in the book happens inside.
    """
    if notified_after_days < 0:
        raise ValueError(
            "a death cannot be notified before it happened "
            f"({notified_after_days} days)")
    notified_on = date.fromordinal(died_on.toordinal() + notified_after_days)
    paid_on = notified_on
    for stage in CLAIM_WORKING_DAYS:
        paid_on = add_working_days(paid_on, stage)

    amount = death_benefit_pence(sum_assured_pence, fund_value_pence)
    events = (
        LifeEvent(on=died_on, kind="death", detail="death of the life assured"),
        LifeEvent(on=notified_on, kind="claim_registered",
                  detail="death notified; claim registered and requirements issued"),
        LifeEvent(on=paid_on, kind="claim_paid",
                  detail="claim assessed and paid to the verified claimant"),
    )
    movements = (Movement(on=paid_on, kind="claim_payment", amount_pence=amount,
                          reason="death benefit paid"),)
    return events, movements
