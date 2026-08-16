"""The routes a pension pays out through, and the trigger that never resets.

Money leaves a Retirement Account **only** through a route a pension actually
pays out through. A plain withdrawal is not one, and refusing it is the whole
point of `03-PEN`.

`03-PEN:4.3`, the trap this module exists to avoid:

> Once **taxable** pension income is flexibly accessed (FAD income or any
> UFPLS), future DC contributions are capped at **£10,000/yr**, with **no
> carry-forward**. Taking **only** PCLS with no taxable income does **not**
> trigger it; nor do **small-pot lump sums** (§9.5).

Four ways to be internally consistent and externally false, all guarded by
tests: drawdown does *not* always trigger (`03-PEN:9.2` — the first *taxable
income* payment does); PCLS never triggers (`03-PEN:9.1`); small pots never
trigger (`03-PEN:9.5`); an annuity is not in the list at all.

🔴 **Where the rulebook and the shipped code disagree.** `products.py:28` lists
`trivial_commutation` among `RA_BENEFIT_ROUTES`, but `03-PEN:9.5` says trivial
commutation "applies to **defined-benefit** rights (and some in-payment
benefits), **not to uncrystallised DC pots**". A Retirement Account is a personal
pension, so it cannot pay out that way. **The shipped constant is deliberately
not changed** — it is v4 code with its own tests, and this version promises to
change no running behaviour. The world uses the narrower set below, which is a
strict subset of it.
"""

from __future__ import annotations

from datetime import date

# `03-PEN:4.3` and `05-OPS:10`.
MPAA_ANNUAL_CAP_PENCE = 10_000_00

# `03-PEN:9.1` — the Lump Sum Allowance for 2025/26.
LUMP_SUM_ALLOWANCE_PENCE = 268_275_00

PCLS_SHARE_BP = 2_500        # `03-PEN:9.1` — normally 25% of what is crystallised
UFPLS_TAX_FREE_BP = 2_500    # `03-PEN:9.3` — 25% tax-free / 75% taxed
BASIS_POINTS_IN_WHOLE = 10_000

# `03-PEN:9.5` — a pot at or under £10,000 can be taken whole, up to three times.
SMALL_POT_CEILING_PENCE = 10_000_00
SMALL_POT_MAX_TIMES = 3

# `03-PEN:8` — "Normal minimum pension age 55, rising to 57 on 6 April 2028".
MINIMUM_PENSION_AGE = 55
RAISED_PENSION_AGE = 57
PENSION_AGE_RISES_ON = date(2028, 4, 6)

# `03-PEN:9.2`, COBS 19.10 — the four ready-made options a non-advised member
# entering drawdown must be offered.
PATHWAYS = {
    1: "no plans to touch the money within 5 years",
    2: "plan to buy an annuity within 5 years",
    3: "plan to take long-term income within 5 years",
    4: "plan to take it all within 5 years",
}

# What the world actually generates — a strict subset of `RA_BENEFIT_ROUTES`.
WORLD_BENEFIT_ROUTES = frozenset({"ufpls", "pcls", "drawdown", "annuity",
                                  "small_pot"})

# `03-PEN:4.3` — only these two can flexibly access *taxable* income.
MPAA_CAPABLE_ROUTES = frozenset({"ufpls", "drawdown"})

MOVEMENT_KINDS = {"ufpls": "ufpls_payment"}


def minimum_pension_age(on: date) -> int:
    """`03-PEN:8`. Every benefit in this book is taken under the age-55 rule —
    the rise is legislated and dated here rather than left out, because leaving
    it out would make the world silently wrong the moment it is extended."""
    return RAISED_PENSION_AGE if on >= PENSION_AGE_RISES_ON else MINIMUM_PENSION_AGE


def old_enough_for_benefits(member_dob: date, on: date) -> bool:
    """Whether the member has reached the minimum pension age by ``on``."""
    age = on.year - member_dob.year
    if (on.month, on.day) < (member_dob.month, member_dob.day):
        age -= 1
    return age >= minimum_pension_age(on)


def triggers_mpaa(route: str, *, taxable_income_taken: bool = True) -> bool:
    """Whether taking ``route`` flexibly accesses taxable income.

    ``taxable_income_taken`` matters for drawdown alone: `03-PEN:9.2` triggers
    on the **first taxable income payment**, so designating funds into drawdown
    and taking only tax-free cash leaves the allowance intact.
    """
    if route not in WORLD_BENEFIT_ROUTES:
        raise ValueError(
            f"{route!r} is not a route this world pays out through — "
            f"`03-PEN` gives {sorted(WORLD_BENEFIT_ROUTES)}")
    if route == "ufpls":
        return True                      # `03-PEN:9.3` — on the first payment
    if route == "drawdown":
        return taxable_income_taken      # `03-PEN:9.2`
    return False                         # PCLS, small pot, annuity


def movement_kind_for(route: str) -> str:
    """The ledger kind a benefit payment posts as. Never ``withdrawal``."""
    if route not in WORLD_BENEFIT_ROUTES:
        raise ValueError(
            f"a Retirement Account cannot pay out by {route!r}: money leaves "
            f"only through {sorted(WORLD_BENEFIT_ROUTES)} (`03-PEN:9`)")
    return MOVEMENT_KINDS.get(route, "payout")


def pcls_pence(crystallised_pence: int, *, lsa_used_pence: int = 0) -> int:
    """`03-PEN:9.1` — 25% of what is crystallised, capped by the LSA."""
    quarter = crystallised_pence * PCLS_SHARE_BP // BASIS_POINTS_IN_WHOLE
    headroom = max(0, LUMP_SUM_ALLOWANCE_PENCE - lsa_used_pence)
    return min(quarter, headroom)


def ufpls_split(amount_pence: int) -> tuple[int, int]:
    """`03-PEN:9.3` — 25% tax-free, the rest taxed. The halves always add back
    to the payment: the taxable part is the remainder, never a second rounding."""
    tax_free = amount_pence * UFPLS_TAX_FREE_BP // BASIS_POINTS_IN_WHOLE
    return tax_free, amount_pence - tax_free


def is_small_pot(value_pence: int) -> bool:
    """`03-PEN:9.5` — a personal-pension pot at or under £10,000."""
    return 0 < value_pence <= SMALL_POT_CEILING_PENCE
