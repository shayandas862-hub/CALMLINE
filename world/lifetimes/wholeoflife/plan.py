"""Playing one whole-of-life policy from its first day to the day it stopped.

The composer decides *what happens*; `world.lifetimes.timeline` decides whether
it is allowed. Nothing here writes to a ledger — it proposes, and every proposal
is offered to the rulebook afterwards.

**Where the premium goes, and why the balance is not a savings pot.** A
protection policy's premium buys cover; it is not saved. `01-WOL:3.3` — a
guaranteed plan has no surrender value — so its premium is consumed by the cost
of cover in the same year and the balance returns to nothing. A unit-linked plan
splits the premium (`01-WOL:3.1`: "maximum-cover / balanced / minimum-cover
investment split"): part meets the cost of cover by unit cancellation
(`01-WOL:3.2`), the rest is invested and grows. That is why forty-two of the
seventy LP policies cannot pay cash out at all.

**Why a death claim credits before it debits.** The death benefit is the sum
assured (`01-WOL:3.3`), which for a protection policy is far more than the fund
behind it — £400,000 of cover against £46,000 of units in the specimen. The
insurer meets the difference from its own reserves, so the claim credits the
policy to the benefit amount and then pays it away. Paying £400,000 out of a
£46,000 balance would simply be refused, and rightly.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional, Sequence

from src.records.models import Policy
from src.records.products import CoverComponent, FundHolding
from world import WORLD_BIRTH_DATE
from world.lifetimes.events import LifeEvent
from world.lifetimes.markets import (
    WOL_MONTHLY_POLICY_FEE_PENCE,
    annual_charge_pence,
    anniversary,
    growth_movements,
)
from world.lifetimes.timeline import Movement
from world.lifetimes.wholeoflife.endings import (
    can_be_made_paid_up,
    claim_sequence,
    lapse_on,
)
from world.lifetimes.wholeoflife.premiums import (
    annual_premium_pence,
    month_after,
    premium_movements,
)
from world.lifetimes.wholeoflife.reviews import (
    REVIEW_OUTCOMES,
    indexation_dates,
    indexed_pence,
    review_dates,
    reviewed_terms,
)

# `01-WOL:3.1`'s three investment splits, as the share of premium consumed by
# the cost of cover. Maximum cover buys the most protection and invests least.
INVESTMENT_SPLITS = {"maximum_cover": 8_000, "balanced": 5_000,
                     "minimum_cover": 3_000}

# A protection-only plan invests nothing: the whole premium buys cover.
PROTECTION_COST_BP = 10_000

INVESTED_BASES = frozenset({"unit_linked"})


@dataclass(frozen=True)
class WholeOfLifePlan:
    """One policy's proposed history, before the rulebook has seen it."""

    policy_no: str
    movements: tuple[Movement, ...]
    events: tuple[LifeEvent, ...]
    status: str
    sum_assured_pence: int
    premium_pence: int


def _cost_of_cover_bp(basis: Sequence[str], rng: random.Random) -> int:
    if not INVESTED_BASES.intersection(basis):
        return PROTECTION_COST_BP
    return INVESTMENT_SPLITS[rng.choice(sorted(INVESTMENT_SPLITS))]


def play_whole_of_life(policy: Policy, cover: CoverComponent,
                       holdings: Sequence[FundHolding] = (), *, seed: int,
                       born: date = WORLD_BIRTH_DATE) -> WholeOfLifePlan:
    """Play ``policy`` forward to ``born``, or to the day it stopped."""
    start = date.fromisoformat(policy.start_date)
    rng = random.Random(f"{seed}:wholeoflife:{policy.policy_no}")
    unit_linked = bool(INVESTED_BASES.intersection(cover.basis))
    cover_bp = _cost_of_cover_bp(cover.basis, rng)

    years = [a for year in range(start.year + 1, born.year + 1)
             if start < (a := anniversary(start, year)) <= born]
    reviews = set(review_dates(start, born=born))
    indexations = set(indexation_dates(start, born=born,
                                       indexation=cover.indexation))

    # Which policy year the policy stopped in. `in_force` never stops.
    ends_in: Optional[int] = None
    if policy.status != "in_force" and len(years) > 2:
        ends_in = rng.randint(1, len(years) - 1)

    movements: list[Movement] = []
    events: list[LifeEvent] = []
    balance = 0
    sum_assured = cover.sum_assured_pence
    premium = cover.premium_pence
    last_premium_on = start

    def collect(on: date, missed: Sequence[int] = ()) -> None:
        """The year's premiums, and what the cover they buy costs.

        Both land on the same date because that is what happens: `01-WOL:3.2`
        deducts the cost of cover *through* the year by unit cancellation, not
        at the end of it. For a protection-only plan the cost is the whole
        premium, so its balance returns to nothing — which is exactly what
        `01-WOL:3.3` means by "guaranteed plans typically [have] no surrender
        value". Settling at year end instead left a guaranteed policy showing a
        year's premiums as though they were a fund somebody could cash in.
        """
        nonlocal balance, last_premium_on
        collected = 0
        charged_on = on
        for movement in premium_movements(on, premium_pence=premium,
                                          frequency=cover.premium_frequency,
                                          missed_months=missed):
            # An itemised year runs eleven months past the anniversary it
            # opened on, so the last few collections of the final year fall
            # after the world's birth date. They have not happened yet.
            if movement.on > born:
                continue
            movements.append(movement)
            balance += movement.amount_pence
            collected += movement.amount_pence
            last_premium_on = max(last_premium_on, movement.on)
            # A year with a missed payment itemises, so its last collection can
            # fall eleven months after the year opened. The cover charge has to
            # follow it, or the history goes backwards and is refused.
            charged_on = max(charged_on, movement.on)
        if collected <= 0:
            return
        due = min(collected * cover_bp // 10_000
                  + 12 * WOL_MONTHLY_POLICY_FEE_PENCE, balance)
        if due > 0:
            movements.append(Movement(
                on=charged_on, kind="charge", amount_pence=due,
                reason="cost of cover and policy fee for the year"))
            balance -= due

    def settle_year(on: date) -> None:
        """What the fund did over the year, and what the fund itself cost."""
        nonlocal balance
        if not unit_linked:
            return
        for movement in growth_movements(balance, on, holdings, seed=seed):
            movements.append(movement)
            balance += (movement.amount_pence
                        if movement.kind in ("investment_return", "bonus")
                        else -movement.amount_pence)
        due = annual_charge_pence(balance, holdings, product_charge_bp=0)
        if due > 0:
            movements.append(Movement(
                on=on, kind="charge", amount_pence=due,
                reason="annual management charge on the fund"))
            balance -= due

    collect(start, missed=())

    for index, on in enumerate(years, start=1):
        settle_year(on)

        if ends_in is not None and index == ends_in:
            _close(policy.status, on, rng, movements, events, balance,
                   cover.basis, sum_assured, premium, cover.premium_frequency,
                   last_premium_on, born)
            return WholeOfLifePlan(policy.policy_no, tuple(movements),
                                   tuple(events), policy.status, sum_assured,
                                   premium)

        if on in reviews:
            outcome = rng.choice(sorted(REVIEW_OUTCOMES))
            premium, sum_assured = reviewed_terms(premium, sum_assured,
                                                  outcome=outcome)
            events.append(LifeEvent(on=on, kind="premium_review",
                                    detail=f"year-{index} review: {outcome}"))
        if on in indexations:
            sum_assured = indexed_pence(sum_assured)
            premium = indexed_pence(premium)
            events.append(LifeEvent(on=on, kind="indexation",
                                    detail="cover and premium indexed"))
        collect(on, missed=_missed_months(rng, cover.premium_frequency))

    return WholeOfLifePlan(policy.policy_no, tuple(movements), tuple(events),
                           policy.status, sum_assured, premium)


def _missed_months(rng: random.Random, frequency: str) -> tuple[int, ...]:
    """Roughly one year in twelve contains a missed payment."""
    if frequency != "monthly" or rng.random() >= 0.08:
        return ()
    return (rng.randrange(12),)


def _close(status, on, rng, movements, events, balance, basis, sum_assured,
           premium, frequency, last_premium_on, born) -> None:
    """Whatever ends the policy, and nothing dated after it."""
    if status == "lapsed":
        # `_close` runs before this year's collection, so the premium that was
        # missed is the one due at `on` for annual plans, and the month after
        # the last collected one for monthly plans. The grace runs from that
        # due date — `01-WOL:3.10`, "30 days from a missed premium". The first
        # version ran it from the last *paid* date and then clamped up to the
        # anniversary, which put every guaranteed lapse a year adrift of its
        # own stated 30-day grace.
        due_on = (month_after(last_premium_on)
                  if frequency == "monthly" else on)
        lapsed_on, reason = lapse_on(
            due_on, basis=basis, fund_value_pence=balance,
            monthly_cost_pence=max(1, premium))
        lapsed_on = min(lapsed_on, born)
        if balance > 0:
            movements.append(Movement(
                on=lapsed_on, kind="charge", amount_pence=balance,
                reason="units cancelled to meet the cost of cover until the "
                       "fund was exhausted"))
        events.append(LifeEvent(on=lapsed_on, kind="lapse", detail=reason))
        return

    if status == "paid_up":
        if not can_be_made_paid_up(basis, fund_value_pence=balance):
            raise ValueError(
                f"a {'/'.join(basis)} policy cannot be made paid up: premiums "
                "ceasing by agreement needs a fund to carry the cost of cover, "
                "and `01-WOL:3.3` gives it none. Premiums stopping on a plan "
                "with no fund is a lapse.")
        events.append(LifeEvent(
            on=on, kind="paid_up",
            detail="premiums ceased by agreement; the existing fund carries "
                   "the cost of the reduced cover"))
        # A paid-up policy is still running, so it still costs something.
        for year in range(on.year + 1, born.year + 1):
            due_on = anniversary(on, year)
            if due_on > born or balance <= 0:
                break
            due = min(annual_charge_pence(balance, (), policy_fee_months=12,
                                          product_charge_bp=0), balance)
            if due > 0:
                movements.append(Movement(
                    on=due_on, kind="charge", amount_pence=due,
                    reason="policy fee and cost of cover, premiums ceased"))
                balance -= due
        return

    if status == "claimed":
        died_on = min(on + timedelta(days=rng.randrange(1, 300)), born)
        claim_events, claim_movements = claim_sequence(
            died_on, sum_assured_pence=sum_assured, fund_value_pence=balance,
            notified_after_days=rng.randrange(2, 22))
        benefit = claim_movements[0].amount_pence
        if benefit > balance:
            movements.append(Movement(
                on=claim_movements[0].on, kind="credit_adjustment",
                amount_pence=benefit - balance,
                reason="sum assured met from the insurer's reserves"))
        movements.extend(claim_movements)
        events.extend(claim_events)
        return

    if status == "surrendered":
        if not INVESTED_BASES.intersection(basis) or balance <= 0:
            raise ValueError(
                f"a {'/'.join(basis)} policy has nothing to surrender: "
                "`01-WOL:3.3` gives guaranteed plans no surrender value, and "
                "forty-two of the seventy Lifelong Protection policies cannot "
                "pay cash out at all. Only a unit-linked plan has a fund.")
        movements.append(Movement(on=on, kind="surrender", amount_pence=balance,
                                  reason="full surrender, fund value paid"))
        events.append(LifeEvent(on=on, kind="surrender",
                                detail="policy surrendered in full"))
