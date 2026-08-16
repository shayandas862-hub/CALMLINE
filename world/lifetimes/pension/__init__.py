"""Retirement Account — contributions, transfers in, and benefit routes only.

Two modules:

- `benefits` — the routes `03-PEN:9` pays out through, what each pays, and
  `03-PEN:4.3`'s money-purchase annual-allowance trigger
- `plan`     — the walker, and the seam rule that refuses everything else
"""

from __future__ import annotations

from world.lifetimes.pension.benefits import (
    LUMP_SUM_ALLOWANCE_PENCE,
    MPAA_ANNUAL_CAP_PENCE,
    PATHWAYS,
    WORLD_BENEFIT_ROUTES,
    is_small_pot,
    minimum_pension_age,
    movement_kind_for,
    old_enough_for_benefits,
    pcls_pence,
    triggers_mpaa,
    ufpls_split,
)
from world.lifetimes.pension.plan import (
    PensionPlan,
    play_pension,
    refuse_non_benefit_money_out,
)

__all__ = [
    "LUMP_SUM_ALLOWANCE_PENCE", "MPAA_ANNUAL_CAP_PENCE", "PATHWAYS",
    "PensionPlan", "WORLD_BENEFIT_ROUTES", "is_small_pot",
    "minimum_pension_age", "movement_kind_for", "old_enough_for_benefits",
    "pcls_pence", "play_pension", "refuse_non_benefit_money_out",
    "triggers_mpaa", "ufpls_split",
]
