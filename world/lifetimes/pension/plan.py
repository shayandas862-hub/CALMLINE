"""Playing one Retirement Account — contributions in, benefits out, nothing else.

Money in is a contribution or a transfer in; money out is a benefit route or it
does not happen. The refusal is not written here: it is
`refuse_non_benefit_money_out`, a rule on the timeline's seam that asks the
**shipped** `can_pay_cash_out` (`products.py:239`). Two copies of that rule is
how they end up disagreeing, and this is the one product whose whole identity is
that rule.

`03-PEN:3.4` — relief at source: the member pays 80% and Aldercrest reclaims 20%
from HMRC, so £80 net becomes £100 gross. The ledger records what arrives in the
pot, which is the gross figure.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

from src.records.models import Policy
from src.records.products import FundHolding, can_pay_cash_out
from world import WORLD_BIRTH_DATE
from world.lifetimes.events import LifeEvent
from world.lifetimes.markets import charge_movements, growth_movements, statement_dates
from world.lifetimes.pension.benefits import (
    MPAA_ANNUAL_CAP_PENCE,
    is_small_pot,
    movement_kind_for,
    old_enough_for_benefits,
    pcls_pence,
    triggers_mpaa,
    ufpls_split,
)
from world.lifetimes.timeline import Movement

# A Retirement Account cannot be surrendered, but contributions can stop — by
# agreement (`paid_up`) or by simply ceasing (`lapsed`). Both leave the pot
# invested and still paying charges; neither takes another penny in.
CEASED_STATUSES = {"paid_up": "paid_up", "lapsed": "lapse"}
CEASED_DETAIL = {
    "paid_up": ("contributions ceased by agreement; the pot stays invested and "
                "continues to bear its charges"),
    "lapsed": ("regular contributions stopped and were not reinstated; the pot "
               "stays invested and continues to bear its charges"),
}

CREDIT_GROWTH = frozenset({"investment_return", "bonus"})
MONEY_IN = frozenset({"opening", "contribution", "transfer_in",
                      "credit_adjustment", "investment_return", "bonus"})

# The charges a pension carries but that are not a payment to the member.
NOT_A_PAYMENT = frozenset({"charge", "investment_loss"})


def refuse_non_benefit_money_out(policy: Policy, movement, balance_pence: int):
    """A rule for the timeline's seam: nothing leaves a pension except through
    a benefit route.

    Asks `can_pay_cash_out` — the shipped rulebook — rather than restating it.
    """
    if policy.product != "retirement_account":
        return None
    if movement.kind in MONEY_IN or movement.kind in NOT_A_PAYMENT:
        return None
    if movement.kind == "ufpls_payment" or movement.kind == "payout":
        return None
    if can_pay_cash_out(policy, route=movement.kind):
        return None
    return (f"a retirement account pays out only through a benefit route; "
            f"{movement.kind!r} is not one (`03-PEN:9`)")


@dataclass(frozen=True)
class PensionPlan:
    """One pension's proposed history, before the rulebook has seen it."""

    policy_no: str
    movements: tuple[Movement, ...]
    events: tuple[LifeEvent, ...]
    status: str
    mpaa_triggered_on: Optional[date]
    benefit_route: Optional[str]


def play_pension(policy: Policy, holdings: Sequence[FundHolding], *,
                 member_dob: date, seed: int,
                 monthly_contribution_pence: int = 600_00,
                 transfer_in_pence: int = 0,
                 benefit_route: Optional[str] = None,
                 born: date = WORLD_BIRTH_DATE) -> PensionPlan:
    """Play ``policy`` forward to ``born``."""
    if policy.status == "surrendered":
        raise ValueError(
            "a Retirement Account is never surrendered: money leaves only "
            "through a benefit route, which is the whole of `03-PEN:9`")

    start = date.fromisoformat(policy.start_date)
    rng = random.Random(f"{seed}:pension:{policy.policy_no}")

    movements: list[Movement] = []
    events: list[LifeEvent] = []
    balance = 0
    mpaa_on: Optional[date] = None
    lsa_used = 0
    ceased = False

    def contribute(on: date) -> None:
        """A year of contributions, gross of relief at source (`03-PEN:3.4`)."""
        nonlocal balance
        yearly = monthly_contribution_pence * 12
        if mpaa_on is not None:
            # `03-PEN:4.3` — capped at £10,000/yr, and no carry-forward.
            yearly = min(yearly, MPAA_ANNUAL_CAP_PENCE)
        if yearly <= 0:
            return
        movements.append(Movement(
            on=on, kind="contribution", amount_pence=yearly,
            reason="12 monthly contributions, gross of relief at source"))
        balance += yearly

    contribute(start)
    if transfer_in_pence:
        movements.append(Movement(
            on=start, kind="transfer_in", amount_pence=transfer_in_pence,
            reason="transfer received from a ceding scheme, scam checks passed"))
        balance += transfer_in_pence

    statements = statement_dates("retirement_account", start, born=born)
    take_at = None
    if benefit_route and statements:
        # Was `len(statements) > 2`, which silently skipped the benefit on any
        # account too young to have three — and left three pensions marked
        # `claimed` with nothing in their history saying so.
        take_at = statements[rng.randint(0, len(statements) - 1)]

    # `paid_up` and `lapsed` both mean contributions have ceased; the pot stays
    # invested and keeps paying charges. The player had no path for either, so
    # eleven accounts carried the status and went on contributing — one of them
    # £7,270 in 2026 while labelled lapsed.
    cease_at = None
    if policy.status in CEASED_STATUSES and statements:
        cease_at = statements[rng.randint(0, len(statements) - 1)]

    for on in statements:
        for movement in growth_movements(balance, on, holdings, seed=seed):
            movements.append(movement)
            balance += (movement.amount_pence if movement.kind in CREDIT_GROWTH
                        else -movement.amount_pence)
        for movement in charge_movements(balance, on, holdings):
            movements.append(movement)
            balance -= movement.amount_pence

        if (take_at is not None and on == take_at and balance > 0
                and old_enough_for_benefits(member_dob, on)):
            paid, mpaa_on, lsa_used = _take_benefit(
                benefit_route, on, balance, lsa_used, movements, events)
            balance -= paid
            take_at = None

        if cease_at is not None and on == cease_at:
            events.append(LifeEvent(
                on=on, kind=CEASED_STATUSES[policy.status],
                detail=CEASED_DETAIL[policy.status]))
            cease_at = None
            ceased = True

        if not ceased:
            contribute(on)

    return PensionPlan(policy.policy_no, tuple(movements), tuple(events),
                       policy.status, mpaa_on, benefit_route)


def _take_benefit(route: str, on: date, balance: int, lsa_used: int,
                  movements: list[Movement],
                  events: list[LifeEvent]) -> tuple[int, Optional[date], int]:
    """Pay one benefit, and record what taking it did to the allowance."""
    if route == "small_pot" and not is_small_pot(balance):
        # `03-PEN:9.5` — a small pot is a pot at or under £10,000. A larger one
        # cannot be taken this way, so nothing is paid rather than a rule bent.
        return 0, None, lsa_used

    if route == "pcls":
        amount = pcls_pence(balance, lsa_used_pence=lsa_used)
        lsa_used += amount
        detail = "tax-free cash taken, funds designated to drawdown, no income"
    elif route == "ufpls":
        amount = min(balance, max(1, balance // 4))
        tax_free, taxable = ufpls_split(amount)
        lsa_used += tax_free
        detail = (f"UFPLS of {amount}p — {tax_free}p tax-free, {taxable}p taxed "
                  "at marginal rate")
    elif route == "small_pot":
        amount = balance
        detail = "small-pot lump sum, whole pot taken (`03-PEN:9.5`)"
    else:  # drawdown, annuity
        amount = min(balance, max(1, balance // 5))
        detail = (f"{route} — {amount}p crystallised")

    if amount <= 0:
        return 0, None, lsa_used

    movements.append(Movement(on=on, kind=movement_kind_for(route),
                              amount_pence=amount, reason=detail))
    events.append(LifeEvent(on=on, kind="benefit_taken", detail=detail))

    mpaa_on = None
    if triggers_mpaa(route):
        mpaa_on = on
        events.append(LifeEvent(
            on=on, kind="mpaa_triggered",
            detail=("taxable pension income flexibly accessed; future money-"
                    "purchase contributions capped at £10,000 a year with no "
                    "carry-forward (`03-PEN:4.3`) — permanent")))
    return amount, mpaa_on, lsa_used
