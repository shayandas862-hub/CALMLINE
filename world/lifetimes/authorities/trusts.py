"""Trusts — executed and not, registrable and not.

**Registrability is decided by the product, not by the allocator.**
`05-OPS:5.8`: "**bond trusts always registrable; pure-protection policy trusts
excluded while the policy is held** (exclusion ends if proceeds held >2 years
after death)". So a Lifelong Protection trust cannot be in breach for want of a
URN — the exclusion means there is nothing to register — and only bond trusts
can be the "registrable and unregistered" refusal the bucket plan wants six of.

Getting that backwards would produce six unregistered protection trusts that a
real trust register has never heard of: a refusal the system would make and the
law would not.

A Retirement Account is not written in trust at all. Its death benefit passes by
nomination and expression of wish (`03-PEN:9.6`), which is a different mechanism.
"""

from __future__ import annotations

import random
from typing import Sequence

from src.records.models import Policy, Trust
from world.lifetimes.authorities.counts import (
    BOOK_SIZE,
    TRUSTS_EXECUTED_AND_REGISTERED,
    TRUSTS_NEVER_EXECUTED,
    TRUSTS_REGISTRABLE_UNREGISTERED,
    TRUSTS_TOTAL,
)

TRUST_KINDS = ("discretionary", "bare", "split_trust")

# `05-OPS:5.8`. A pension is excluded for a different reason — see the docstring.
REGISTRABLE_PRODUCTS = frozenset({"horizon_bond"})


def is_registrable(product: str) -> bool:
    """Whether a trust over ``product`` must appear on the trust register."""
    return product in REGISTRABLE_PRODUCTS


def _require_enough(policies: Sequence[Policy]) -> None:
    if len(policies) < BOOK_SIZE:
        raise ValueError(
            f"the bucket plan allocates over {BOOK_SIZE} policies; got "
            f"{len(policies)}. A short book would meet the counts by accident "
            "or not at all, and either way the plan would stop being met.")


def allocate_trusts(policies: Sequence[Policy], *, seed: int,
                    trustees: Sequence[str] = ()) -> dict[str, Trust]:
    """Which policies are written in trust, and in what condition.

    The two broken kinds are placed first and on products that can actually
    carry them: an unregistered *registrable* trust has to be a bond.
    """
    _require_enough(policies)
    rng = random.Random(f"{seed}:trusts")
    pool = sorted(trustees) or [f"PH-{6000 + i}" for i in range(1, 25)]

    bonds = sorted(p.policy_no for p in policies if is_registrable(p.product))
    others = sorted(p.policy_no for p in policies
                    if p.product == "lifelong_protection")
    if len(bonds) < TRUSTS_REGISTRABLE_UNREGISTERED:
        raise ValueError(
            f"only {len(bonds)} policies can carry a registrable trust; the "
            f"plan needs {TRUSTS_REGISTRABLE_UNREGISTERED} unregistered ones")

    rng.shuffle(bonds)
    rng.shuffle(others)
    allocated: dict[str, Trust] = {}

    def name_trustees() -> tuple[str, ...]:
        return tuple(sorted(rng.sample(pool, rng.randint(1, 2))))

    # Six registrable trusts with no URN — the refusal that needs a bond.
    for policy_no in bonds[:TRUSTS_REGISTRABLE_UNREGISTERED]:
        allocated[policy_no] = Trust(kind=rng.choice(TRUST_KINDS), executed="yes",
                                     trustees=name_trustees(), registrable=True,
                                     urn=None)

    # Six nobody ever executed. A trust nobody executed is not a trust.
    #
    # Placed on protection policies, which `05-OPS:5.8` excludes from the
    # register: otherwise a never-executed bond trust would ALSO be registrable
    # with no URN, and the two refusals the bucket plan counts separately would
    # be the same six rows wearing two hats.
    for policy_no in others[:TRUSTS_NEVER_EXECUTED]:
        allocated[policy_no] = Trust(
            kind=rng.choice(TRUST_KINDS), executed="no",
            trustees=name_trustees(), registrable=False, urn=None)

    # Twenty in good order: executed, and registered wherever registration bites.
    remaining = (bonds[TRUSTS_REGISTRABLE_UNREGISTERED:]
                 + others[TRUSTS_NEVER_EXECUTED:])
    for policy_no in remaining[:TRUSTS_EXECUTED_AND_REGISTERED]:
        registrable = is_registrable(_product_of(policies, policy_no))
        allocated[policy_no] = Trust(
            kind=rng.choice(TRUST_KINDS), executed="yes",
            trustees=name_trustees(), registrable=registrable,
            urn=f"TRS{rng.randrange(10_000_000, 99_999_999)}" if registrable
            else None)

    if len(allocated) != TRUSTS_TOTAL:
        raise ValueError(
            f"allocated {len(allocated)} trusts, the plan says {TRUSTS_TOTAL}")
    return allocated


def _product_of(policies: Sequence[Policy], policy_no: str) -> str:
    for policy in policies:
        if policy.policy_no == policy_no:
            return policy.product
    raise KeyError(policy_no)
