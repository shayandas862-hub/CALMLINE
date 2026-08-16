"""Horizon Bond — segments, the 5% allowance, withdrawals and surrenders.

Three mechanics, three modules:

- `allowance` — `02-BOND:4.2`'s 5% tax-deferred allowance, and the excess
  `02-BOND:4.3` tests at policy-year end
- `segments`  — `02-BOND:3.1`'s identical mini-policies, and why a segment
  surrender is not a partial withdrawal (`02-BOND:4.9`)
- `plan`      — the walker that composes them into one bond's history
"""

from __future__ import annotations

from world.lifetimes.bond.allowance import (
    ANNUAL_ALLOWANCE_BP,
    MAX_CUMULATIVE_BP,
    cumulative_allowance_pence,
    excess_pence,
    policy_year_of,
    remaining_allowance_pence,
)
from world.lifetimes.bond.plan import BondPlan, play_bond
from world.lifetimes.bond.segments import (
    DEFAULT_SEGMENTS,
    segment_value_pence,
    segments_for_amount,
)

__all__ = [
    "ANNUAL_ALLOWANCE_BP", "BondPlan", "DEFAULT_SEGMENTS", "MAX_CUMULATIVE_BP",
    "cumulative_allowance_pence", "excess_pence", "play_bond", "policy_year_of",
    "remaining_allowance_pence", "segment_value_pence", "segments_for_amount",
]
