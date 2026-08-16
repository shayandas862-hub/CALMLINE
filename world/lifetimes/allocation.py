"""Deciding what the two hundred policies *are*, before any of them is played.

Every count here is the bucket plan's, and they are met exactly rather than
approximately — a book generated without a plan is two hundred near-copies, and
the point of the world is that it can be asked things, including things it must
refuse.

**§8 is measured on the headline value, and that is a decision rather than a
reading.** A partition of all 200 by *final ledger balance* is impossible: at
least 74 policies end at zero — everything lapsed, claimed or surrendered, plus
every protection-only whole-of-life policy, which `01-WOL:3.3` gives no surrender
value — while §8 allows only 58 under £25,000. §8 states its own purpose as the
approval matrix, and `05-OPS:9.9` bands claim-payment authority by value, so the
figure a control actually tests is the fund for investment-backed policies and
the **sum assured** for protection cover. A policy carrying £400,000 of cover is
not an "under £25,000" policy in any sense a control cares about.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from typing import Optional

# The world imports the rulebook; the reserved block is the rulebook's, because
# it is the corpus that documents the specimen records the block exists for.
from src.records.anchors import GENERATED_CEILING
from world.lifetimes.holders import _age_consistent, _holder_plan

# §2 — product × status. Empty cells are deliberate: a bond is a single-premium
# contract and cannot lapse or be made paid up; a pension is not surrendered.
PRODUCT_STATUS_COUNTS = {
    ("lifelong_protection", "in_force"): 43,
    ("lifelong_protection", "lapsed"): 14,
    ("lifelong_protection", "paid_up"): 6,
    ("lifelong_protection", "claimed"): 4,
    ("lifelong_protection", "surrendered"): 3,
    ("horizon_bond", "in_force"): 55,
    ("horizon_bond", "claimed"): 3,
    ("horizon_bond", "surrendered"): 7,
    ("retirement_account", "in_force"): 52,
    ("retirement_account", "lapsed"): 4,
    ("retirement_account", "paid_up"): 6,
    ("retirement_account", "claimed"): 3,
}

# §9 — Lifelong Protection cover basis. Forty-two carry no fund at all.
LP_UNIT_LINKED = 28
LP_GUARANTEED = 22
LP_REVIEWABLE_ONLY = 20

# §3 — lives assured.
JOINT_LIVES = 38

# §8 — value bands, on the headline value.
BAND_COUNTS = {"under_25k": 58, "25k_to_100k": 74, "100k_to_250k": 55,
               "over_250k": 13}
BAND_BOUNDS = ((25_000_00, "under_25k"), (100_000_00, "25k_to_100k"),
               (250_000_00, "100k_to_250k"))
# A **range** per band, not a single figure. Scaling every policy onto one
# target made seventy-four of them worth almost exactly £62,000, which is the
# first thing that reads as generated. Each policy draws its own target from
# inside its band, well clear of the boundaries so the two-pass scaling cannot
# overshoot into the band next door.
BAND_TARGET_RANGES = {
    "under_25k": (2_000_00, 23_000_00),
    "25k_to_100k": (27_000_00, 97_000_00),
    "100k_to_250k": (103_000_00, 244_000_00),
    "over_250k": (256_000_00, 920_000_00),
}

# §10 — history depth, per product rather than one number for all three.
HISTORY_SPANS = {"lifelong_protection": (1994, 2016),
                 "retirement_account": (2004, 2019),
                 "horizon_bond": (2015, 2024)}

PREFIX = {"lifelong_protection": "LP", "horizon_bond": "HB",
          "retirement_account": "RA"}

# §11 — sixty of the two hundred holders carry a memorable datum.
MEMORABLE_HOLDERS = 60


def band_of(headline_value_pence: int) -> str:
    """Which §8 band a figure falls in."""
    for ceiling, name in BAND_BOUNDS:
        if headline_value_pence < ceiling:
            return name
    return "over_250k"


@dataclass(frozen=True)
class PolicySpec:
    """What one policy is, before it has been played."""

    policy_no: str
    product: str
    status: str
    start: date
    holder_party_id: str
    lives_basis: str
    second_life_party_id: Optional[str]
    cover_basis: tuple[str, ...]
    band: str


def _mint(prefix: str, nth: int) -> str:
    """The nth policy number of a product, and the guarantee behind it.

    Spaced rather than sequential so a number carries no hint of how many were
    issued before it. The **refusal** is the point: a minted number landing in
    the block the corpus reserves for its own specimen records would collide
    with a documented policy, and until this check existed the three specimens
    were missed by arithmetic accident rather than by design.

    Raised here, where numbers are made, rather than checked where they are
    read — a book that has already been built on a colliding number is a book
    that has to be thrown away.
    """
    digits = 20_000_000 + nth * 137
    if digits > GENERATED_CEILING:
        raise ValueError(
            f"{prefix}-{digits:08d} is beyond the generated ceiling of "
            f"{GENERATED_CEILING} and would reach the block reserved for the "
            f"corpus's specimen records")
    return f"{prefix}-{digits:08d}"


def _statuses() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for (product, status), count in PRODUCT_STATUS_COUNTS.items():
        pairs.extend([(product, status)] * count)
    return pairs


def _cover_bases(rng: random.Random, statuses: list[str]) -> list[tuple[str, ...]]:
    """§9, with a constraint the plan does not state but `01-WOL:3.3` forces:
    a policy that was made paid up or surrendered must have had a fund."""
    needs_fund = [i for i, s in enumerate(statuses)
                  if s in {"paid_up", "surrendered"}]
    if len(needs_fund) > LP_UNIT_LINKED:
        raise ValueError(
            f"{len(needs_fund)} LP policies were paid up or surrendered but "
            f"only {LP_UNIT_LINKED} are unit-linked; `01-WOL:3.3` gives the "
            "rest no fund to do either with")

    bases: list[Optional[tuple[str, ...]]] = [None] * len(statuses)
    for index in needs_fund:
        bases[index] = ("reviewable", "unit_linked")

    spare = [i for i, b in enumerate(bases) if b is None]
    rng.shuffle(spare)
    remaining_unit_linked = LP_UNIT_LINKED - len(needs_fund)
    for index in spare[:remaining_unit_linked]:
        bases[index] = ("reviewable", "unit_linked")
    cursor = remaining_unit_linked
    for index in spare[cursor:cursor + LP_GUARANTEED]:
        bases[index] = ("guaranteed",)
    for index in spare[cursor + LP_GUARANTEED:]:
        bases[index] = ("reviewable",)
    return [b for b in bases if b is not None]


# A whole-of-life policy only builds a fund once a fifth of its premium clears
# the £4.50 monthly policy fee (`01-WOL:3.2`). Below roughly £42,000 of cover
# the fee eats the whole premium, so a small unit-linked plan never accumulates
# anything — and a plan with no fund can be neither made paid up nor
# surrendered (`01-WOL:3.3`). Those nine therefore have to sit in a band whose
# premium is large enough to invest something.
FUND_BUILDING_BANDS = ("100k_to_250k", "over_250k")
NEEDS_A_FUND = frozenset({"paid_up", "surrendered"})


def _assign_bands(rng: random.Random, pairs: list[tuple[str, str]],
                  lp_statuses: list[str]) -> list[str]:
    """§8's bands, placed so no policy is given a band it cannot live in."""
    pool: list[str] = []
    for name, count in BAND_COUNTS.items():
        pool.extend([name] * count)

    needs_fund = [i for i, (product, status) in enumerate(pairs)
                  if product == "lifelong_protection" and status in NEEDS_A_FUND]
    bands: list[Optional[str]] = [None] * len(pairs)
    for index in needs_fund:
        for candidate in FUND_BUILDING_BANDS:
            if candidate in pool:
                pool.remove(candidate)
                bands[index] = candidate
                break
        else:
            raise ValueError(
                f"no fund-building band left for policy {index}; §8 cannot "
                "cover the policies that were paid up or surrendered")

    rng.shuffle(pool)
    spare = iter(pool)
    return [band if band is not None else next(spare) for band in bands]


def allocate_book(*, seed: int, born: date,
                  holders: Optional[list[str]] = None,
                  second_lives: Optional[list[str]] = None,
                  dobs: Optional[dict[str, date]] = None
                  ) -> tuple[PolicySpec, ...]:
    """The two hundred, decided but not yet played."""
    earliest = min(start for start, _ in HISTORY_SPANS.values())
    if born.year <= earliest:
        raise ValueError(
            f"a world born {born.isoformat()} has no room for a book reaching "
            f"back to {earliest}; §10 gives the oldest product a {earliest}"
            f"–{max(end for _, end in HISTORY_SPANS.values())} span")

    rng = random.Random(f"{seed}:allocation")
    holders = holders or [f"PH-{2000 + i}" for i in range(1, 163)]
    second_lives = second_lives or [f"PH-{2162 + i}" for i in range(1, 39)]

    pairs = _statuses()
    rng.shuffle(pairs)
    lp_statuses = [status for product, status in pairs
                   if product == "lifelong_protection"]
    bases = iter(_cover_bases(rng, lp_statuses))

    holder_for = _holder_plan(rng, holders)
    joint = set(rng.sample(range(len(pairs)), JOINT_LIVES))
    seconds = iter(second_lives)

    bands = _assign_bands(rng, pairs, lp_statuses)

    # Every start date first, because who holds a policy depends on when it
    # began — the two used to be drawn independently and never reconciled.
    starts: list[date] = []
    for product, _ in pairs:
        earliest, latest = HISTORY_SPANS[product]
        start = date(rng.randint(earliest, latest), rng.randint(1, 12),
                     rng.randint(1, 28))
        if start > born:
            start = start.replace(year=min(start.year, born.year - 1))
        starts.append(start)

    if dobs:
        holder_for = _age_consistent(holder_for, starts, dobs)

    specs: list[PolicySpec] = []
    counters = {prefix: 0 for prefix in PREFIX.values()}
    for index, (product, status) in enumerate(pairs):
        prefix = PREFIX[product]
        counters[prefix] += 1
        start = starts[index]

        specs.append(PolicySpec(
            policy_no=_mint(prefix, counters[prefix]),
            product=product,
            status=status,
            start=start,
            holder_party_id=holder_for[index],
            lives_basis="joint_last_survivor" if index in joint else "single",
            second_life_party_id=next(seconds) if index in joint else None,
            cover_basis=(next(bases) if product == "lifelong_protection"
                         else ()),
            band=bands[index],
        ))
    return tuple(specs)
