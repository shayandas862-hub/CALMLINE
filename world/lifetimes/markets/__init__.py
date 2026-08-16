"""Deterministic fund growth and charges — the market every policy sits in.

Four mechanics, four modules, because each one grows if it is allowed to share a
file with the others:

- `funds` — what can be held, and what it charges
- `growth` — what the market did, seeded so it did the same thing for everyone
- `charges` — integer arithmetic from end to end, so nothing is ever a rounding
- `statements` — when a year's growth and charges actually post

Nothing here knows what a segment, a benefit route or a premium review is. The
products do, and they compose these pieces.
"""

from __future__ import annotations

from world.lifetimes.markets.charges import (
    PRODUCT_CHARGE_BP,
    WOL_MONTHLY_POLICY_FEE_PENCE,
    annual_charge_pence,
    charge_movements,
    charge_pence,
)
from world.lifetimes.markets.funds import CATALOGUE, Fund, fund
from world.lifetimes.markets.growth import (
    MARKET_STRESS,
    annual_return_bp,
    blended_return_bp,
    growth_movements,
)
from world.lifetimes.markets.statements import anniversary, statement_dates

__all__ = [
    "CATALOGUE", "Fund", "MARKET_STRESS", "PRODUCT_CHARGE_BP",
    "WOL_MONTHLY_POLICY_FEE_PENCE", "anniversary", "annual_charge_pence",
    "annual_return_bp", "blended_return_bp", "charge_movements", "charge_pence",
    "fund", "growth_movements", "statement_dates",
]
