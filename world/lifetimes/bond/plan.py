"""Playing one Horizon Bond from the day the money went in.

A single-premium contract: it opens once, grows, is charged, may pay regular
withdrawals, and ends by surrender or by death. **It cannot lapse and is never
made paid up** — there is no premium to miss, which is why the bucket plan
leaves both cells empty for this product.

The two tax mechanics that make a bond a bond both live here:

- **The 5% allowance** (`02-BOND:4.2`), tracked across policy years in
  `allowance.py`, with an excess **tested at policy-year end** (`02-BOND:4.3`)
  rather than on the day of the withdrawal.
- **Segments** (`02-BOND:3.1`), reduced only by whole-segment surrenders, which
  `02-BOND:4.9` insists are a different event from a partial withdrawal.

`02-BOND:3.4` gives the death benefit — 101% of bond value on death of the last
life assured — and unlike whole of life that is payable from the fund itself, so
no reserve credit is needed for the sum assured. Only the 1% uplift is.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence

from src.records.models import Policy
from src.records.products import FundHolding
from world import WORLD_BIRTH_DATE
from world.lifetimes.bond.allowance import excess_pence, policy_year_of
from world.lifetimes.bond.segments import (
    DEFAULT_SEGMENTS,
    segment_value_pence,
    segments_for_amount,
)
from world.lifetimes.events import LifeEvent
from world.lifetimes.markets import (
    annual_charge_pence,
    charge_movements,
    growth_movements,
    statement_dates,
)
from world.lifetimes.timeline import Movement
from world.lifetimes.wholeoflife.endings import claim_sequence

# `02-BOND:3.4` — 101% of bond value on death of the last life assured.
DEATH_UPLIFT_BP = 10_100

CREDIT_GROWTH = frozenset({"investment_return", "bonus"})


@dataclass(frozen=True)
class BondPlan:
    """One bond's proposed history, before the rulebook has seen it."""

    policy_no: str
    movements: tuple[Movement, ...]
    events: tuple[LifeEvent, ...]
    status: str
    invested_pence: int
    allowance_used_pence: int
    segments_total: int
    segments_remaining: int


def play_bond(policy: Policy, holdings: Sequence[FundHolding], *,
              invested_pence: int, seed: int,
              withdraw_annually_pence: int = 0,
              surrender_segments_pence: int = 0,
              born: date = WORLD_BIRTH_DATE) -> BondPlan:
    """Play ``policy`` forward to ``born``, or to the day it ended."""
    if policy.status in {"lapsed", "paid_up"}:
        raise ValueError(
            f"a Horizon Bond cannot {policy.status.replace('_', ' ')}: it is a "
            "single-premium contract with no premium to miss, which is why the "
            "bucket plan leaves both cells empty for this product")

    start = date.fromisoformat(policy.start_date)
    rng = random.Random(f"{seed}:bond:{policy.policy_no}")

    movements: list[Movement] = [
        Movement(on=start, kind="opening", amount_pence=invested_pence,
                 reason="single premium invested")]
    events: list[LifeEvent] = []
    balance = invested_pence
    allowance_used = 0
    segments_total = segments_remaining = DEFAULT_SEGMENTS
    drawn_this_year = 0
    current_year = 1

    statements = statement_dates("horizon_bond", start, born=born)
    ends_at = None
    if policy.status in {"surrendered", "claimed"} and statements:
        # Was `len(statements) > 2`, which silently skipped the ending on any
        # bond too young to have three — `HB-20007535` opened in 2024, was
        # marked surrendered, and went on taking regular withdrawals in 2026.
        ends_at = statements[rng.randint(0, len(statements) - 1)]
    # A one-off part surrender by segments, on an anniversary of its own.
    segments_at = (statements[rng.randrange(len(statements))]
                   if surrender_segments_pence and statements else None)

    for on in statements:
        # The year that has just ended: growth, then what it cost to run.
        for movement in growth_movements(balance, on, holdings, seed=seed):
            movements.append(movement)
            balance += (movement.amount_pence if movement.kind in CREDIT_GROWTH
                        else -movement.amount_pence)
        for movement in charge_movements(balance, on, holdings):
            movements.append(movement)
            balance -= movement.amount_pence

        # `02-BOND:4.3` — the excess is tested at policy-year end, so a year's
        # withdrawals are judged together rather than one at a time.
        year = policy_year_of(start, on) - 1
        if drawn_this_year:
            excess = excess_pence(drawn_this_year, invested_pence,
                                  policy_year=year, used_pence=allowance_used)
            allowance_used += drawn_this_year - excess
            if excess:
                events.append(LifeEvent(
                    on=on, kind="chargeable_event",
                    detail=(f"partial withdrawals of {drawn_this_year}p in "
                            f"policy year {year} exceeded the cumulative 5% "
                            f"allowance by {excess}p (excess assessed at "
                            f"policy-year end)")))
            drawn_this_year = 0
        current_year = year + 1

        if ends_at is not None and on == ends_at:
            _close(policy.status, on, rng, movements, events, balance)
            segments_remaining = 0
            return BondPlan(policy.policy_no, tuple(movements), tuple(events),
                            policy.status, invested_pence, allowance_used,
                            segments_total, segments_remaining)

        # A part surrender by whole segments — `02-BOND:4.9` route (b). It is
        # deliberately NOT charged against the 5% allowance: that allowance is
        # a partial-withdrawal mechanic, and conflating the two routes is the
        # exact error the corpus spends a section warning about.
        if segments_at is not None and on == segments_at and balance > 0:
            unit = segment_value_pence(balance, segments_remaining)
            count = segments_for_amount(surrender_segments_pence, unit,
                                        segments_remaining=segments_remaining)
            if count and count < segments_remaining:
                proceeds = unit * count
                movements.append(Movement(
                    on=on, kind="segment_surrender", amount_pence=proceeds,
                    reason=f"surrender of {count} whole segments"))
                balance -= proceeds
                segments_remaining -= count
                events.append(LifeEvent(
                    on=on, kind="chargeable_event",
                    detail=(f"surrender of {count} whole segments — a "
                            "chargeable event under `02-BOND:4.3`, gain per "
                            "segment being proceeds less its premium share, "
                            "and outside the 5% allowance entirely")))

        # The coming year's regular withdrawal, taken the day the year opens.
        if withdraw_annually_pence and balance > withdraw_annually_pence:
            movements.append(Movement(
                on=on, kind="regular_withdrawal",
                amount_pence=withdraw_annually_pence,
                reason="regular withdrawal across all segments"))
            balance -= withdraw_annually_pence
            drawn_this_year += withdraw_annually_pence

    # A part-year's withdrawals still count, at the world's birth date.
    if drawn_this_year:
        excess = excess_pence(drawn_this_year, invested_pence,
                              policy_year=current_year,
                              used_pence=allowance_used)
        allowance_used += drawn_this_year - excess

    return BondPlan(policy.policy_no, tuple(movements), tuple(events),
                    policy.status, invested_pence, allowance_used,
                    segments_total, segments_remaining)


def _close(status: str, on: date, rng: random.Random,
           movements: list[Movement], events: list[LifeEvent],
           balance: int) -> None:
    """Full surrender, or death — both empty the bond."""
    if status == "surrendered":
        movements.append(Movement(
            on=on, kind="surrender", amount_pence=balance,
            reason="full surrender of all remaining segments"))
        events.append(LifeEvent(
            on=on, kind="chargeable_event",
            detail="full surrender — a chargeable event under `02-BOND:4.3`, "
                   "gain assessed on proceeds less the amount invested"))
        events.append(LifeEvent(on=on, kind="surrender",
                                detail="bond surrendered in full"))
        return

    # `02-BOND:3.4` — 101% of bond value, paid from the fund plus a 1% uplift
    # the insurer meets. `02-BOND:3.6`: no MVR is ever applied on death.
    died_on = min(on + timedelta(days=rng.randrange(1, 300)), on + timedelta(days=300))
    benefit = balance * DEATH_UPLIFT_BP // 10_000
    claim_events, claim_movements = claim_sequence(
        died_on, sum_assured_pence=benefit, fund_value_pence=0,
        notified_after_days=rng.randrange(2, 22))
    paid_on = claim_movements[0].on
    if benefit > balance:
        movements.append(Movement(
            on=paid_on, kind="credit_adjustment", amount_pence=benefit - balance,
            reason="101% death benefit uplift met by the insurer "
                   "(no MVR on death)"))
    movements.extend(claim_movements)
    events.append(LifeEvent(
        on=died_on, kind="chargeable_event",
        detail="death of the last life assured — a chargeable event under "
               "`02-BOND:4.3`"))
    events.extend(claim_events)
