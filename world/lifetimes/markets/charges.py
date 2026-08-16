"""Charges — integer arithmetic from end to end, so nothing is ever a rounding.

The rates come from the product masters and are held as integers:

- `02-BOND:3.3` — "Product/administration 0.30% p.a.; fund AMCs 0.10%–1.00%"
- `03-PEN:3.3` — "Annual product charge 0.30% p.a.; fund AMCs 0.10%–1.00%"
- `01-WOL:3.2` — "Monthly policy fee £4.50"

**Where the corpus is silent, and what was decided.** It states charge rates
but names a deduction *frequency* for whole of life only ("monthly cost-of-cover
deduction by unit cancellation", `01-WOL:3.2`); the bond and the pension say
"p.a.", which is a rate and not a schedule. The charge is therefore **calculated**
as each master states it and **posted** as an annual summary — the same treatment
premiums already get, and for the same reason: four hundred ledger rows on a
thirty-year policy crowd out the events that matter.
"""

from __future__ import annotations

from datetime import date
from typing import Sequence

from src.records.products import FundHolding
from world.lifetimes.timeline import Movement

# `02-BOND:3.3` and `03-PEN:3.3`, which state the same figure: 0.30% p.a.
PRODUCT_CHARGE_BP = 30

# `01-WOL:3.2` — £4.50 a month, in pence so it never becomes a float.
WOL_MONTHLY_POLICY_FEE_PENCE = 450

BASIS_POINTS_IN_WHOLE = 10_000


def charge_pence(value_pence: int, *, bp: int) -> int:
    """``bp`` basis points of ``value_pence``, as whole pence.

    **Rounds down.** Where the exact figure falls between pennies the customer
    keeps the fraction — a direction chosen rather than inherited from integer
    division. An insurer rounding its own charges up, on every policy, every
    year, for thirty years, has helped itself a penny at a time.
    """
    if value_pence <= 0 or bp <= 0:
        return 0
    return value_pence * bp // BASIS_POINTS_IN_WHOLE


def annual_charge_pence(value_pence: int, holdings: Sequence[FundHolding], *,
                        policy_fee_months: int = 0,
                        product_charge_bp: int = PRODUCT_CHARGE_BP) -> int:
    """A year's charges on ``value_pence``: each fund on its own slice, plus
    the product charge on the whole, plus any whole-of-life policy fee.

    ``product_charge_bp`` is a parameter rather than a constant because **only
    two of the three products have one**. `02-BOND:3.3` and `03-PEN:3.3` state
    0.30% p.a.; `01-WOL:3.2` states a £4.50 monthly policy fee and no percentage
    charge at all. Applying the bond's charge to a whole-of-life policy would be
    inventing a fee the corpus does not give it.

    Never more than the value it is taken from. The rates sum well under 100%,
    so the cap is a guarantee rather than a correction — but a charge that could
    overdraw a policy would be refused by the ledger and stop the whole book,
    and that is not a thing to leave to arithmetic that happens to work out.
    """
    if value_pence <= 0:
        return 0
    total = sum(
        charge_pence(value_pence * h.split_pct // 100, bp=h.amc_bp)
        for h in holdings
    )
    total += charge_pence(value_pence, bp=product_charge_bp)
    total += max(0, policy_fee_months) * WOL_MONTHLY_POLICY_FEE_PENCE
    return min(total, value_pence)


def charge_movements(value_pence: int, on: date,
                     holdings: Sequence[FundHolding], *,
                     policy_fee_months: int = 0) -> tuple[Movement, ...]:
    """The year's charges as a single ledger movement, or nothing at all."""
    amount = annual_charge_pence(value_pence, holdings,
                                 policy_fee_months=policy_fee_months)
    if amount <= 0:
        return ()
    reason = "annual management and product charges"
    if policy_fee_months:
        reason = f"{reason}, and {policy_fee_months} months' policy fee"
    return (Movement(on=on, kind="charge", amount_pence=amount, reason=reason),)
