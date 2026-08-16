"""Adviser mandates, and third-party authorities.

`05-OPS:5.1` — a letter of authority names Aldercrest and the firm, the firm's
FRN is checked on the FCA Register, and the adviser is linked to the firm. Scope
is "usually servicing and information". **It does not authorise receiving claim
or surrender proceeds, or changing the customer's bank details** — structural
limits that hold whatever the scope tuple says, which is why they are not
expressed as scope entries here.

The mandate belongs to the **firm**; the individuals who may exercise it are
named under it, and every name comes from that firm's own staff. A name from
another firm would pass the firm check and fail the person — which is a real
scenario, but not one that should arise from the generator being careless.

`05-OPS:5.2` — an LPA is "valid only once **registered with the OPG**", so three
unregistered ones are the refusal the bucket plan asks for.

`05-OPS:5.8` — trusteeship is **personal**: no attorney, deputy or personal
representative ever carries a trustee scope. That is the E22 failure mode, and
it is prevented here rather than only refused at the gate.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Sequence

from src.records.authorisations import AuthorityRecord
from src.records.models import AdviserLoa, Policy
from world.lifetimes.authorities.counts import (
    ATTORNEYS_EPA,
    ATTORNEYS_LPA_REGISTERED,
    ATTORNEYS_LPA_UNREGISTERED,
    DEPUTIES,
    MANDATES_EXPIRED,
    MANDATES_TOTAL,
    PERSONAL_REPRESENTATIVES,
    SCOPE_PLUS_SWITCHES,
    SCOPE_PLUS_WITHDRAWALS,
)

BASE_SCOPE = ("information", "servicing")

# Scopes an attorney or deputy may hold. `trustee_change` is deliberately absent
# from every one of them (`05-OPS:5.8`).
THIRD_PARTY_SCOPES = ("information", "servicing", "bank_change")


def allocate_mandates(policies: Sequence[Policy], firms: Sequence[dict], *,
                      seed: int, born: date) -> dict[str, AdviserLoa]:
    """Which policies have an adviser mandate, and in what standing."""
    rng = random.Random(f"{seed}:mandates")
    chosen = sorted(p.policy_no for p in policies)
    rng.shuffle(chosen)
    chosen = chosen[:MANDATES_TOTAL]
    if len(chosen) < MANDATES_TOTAL:
        raise ValueError(
            f"the plan needs {MANDATES_TOTAL} mandates; the book offers "
            f"{len(chosen)} policies")

    allocated: dict[str, AdviserLoa] = {}
    for index, policy_no in enumerate(sorted(chosen)):
        firm = firms[index % len(firms)]
        scope = list(BASE_SCOPE)
        if index < SCOPE_PLUS_WITHDRAWALS:
            scope += ["switches", "withdrawals"]
        elif index < SCOPE_PLUS_WITHDRAWALS + SCOPE_PLUS_SWITCHES:
            scope.append("switches")

        # Eight have run out. An expiry is a date, so "expired" is derived
        # rather than stored — a stored flag and a stored date can disagree.
        if index < MANDATES_EXPIRED:
            expiry = born - timedelta(days=rng.randint(30, 900))
        else:
            expiry = born + timedelta(days=rng.randint(60, 1200))

        named = firm["individuals"]
        allocated[policy_no] = AdviserLoa(
            firm=firm["name"], frn=firm["firm_ref"], scope=tuple(scope),
            expiry=expiry.isoformat(),
            individuals=tuple(sorted(rng.sample(named,
                                                rng.randint(1, len(named))))))
    return allocated


def allocate_third_party_authorities(
        policies: Sequence[Policy], *, attorneys: Sequence[dict],
        deputies: Sequence[dict], personal_representatives: Sequence[dict],
        seed: int) -> dict[str, tuple[AuthorityRecord, ...]]:
    """Attorneys, court-appointed deputies and personal representatives.

    None of them is ever given a trustee scope (`05-OPS:5.8`).
    """
    rng = random.Random(f"{seed}:third-party")
    pool = sorted(p.policy_no for p in policies)
    rng.shuffle(pool)

    allocated: dict[str, list[AuthorityRecord]] = {}
    cursor = 0

    def place(people: Sequence[dict], type_: str, count: int,
              status: str) -> None:
        nonlocal cursor
        for person in list(people)[:count]:
            policy_no = pool[cursor]
            cursor += 1
            allocated.setdefault(policy_no, []).append(AuthorityRecord(
                authority_id=f"AUT-{cursor:04d}",
                policy_no=policy_no,
                party_id=person["party_id"],
                type=type_,
                scope=tuple(THIRD_PARTY_SCOPES[:rng.randint(1, 3)]),
                evidence_ref=f"EV-{cursor:05d}",
                verified_date=None if status == "unverified" else "2024-01-15",
                status=status,
            ))

    registered, epa, unregistered = (
        attorneys[:ATTORNEYS_LPA_REGISTERED],
        attorneys[ATTORNEYS_LPA_REGISTERED:ATTORNEYS_LPA_REGISTERED + ATTORNEYS_EPA],
        attorneys[ATTORNEYS_LPA_REGISTERED + ATTORNEYS_EPA:],
    )
    place(registered, "LPA", ATTORNEYS_LPA_REGISTERED, "active")
    place(epa, "EPA", ATTORNEYS_EPA, "active")
    # `05-OPS:5.2` — not yet registered with the OPG, so not yet valid.
    place(unregistered, "LPA", ATTORNEYS_LPA_UNREGISTERED, "unverified")
    place(deputies, "deputy", DEPUTIES, "active")
    place(personal_representatives, "PR", PERSONAL_REPRESENTATIVES, "active")

    return {policy_no: tuple(records)
            for policy_no, records in sorted(allocated.items())}
