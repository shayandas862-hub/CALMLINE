"""Everyone the world needs — not policyholders only.

A book of two hundred policies is not two hundred people. Somebody holds the
power of attorney, somebody is the deputy the court appointed, somebody is the
trustee whose signature the deed needs, somebody is the personal representative
once the holder has died, and somebody is the adviser who telephones on a
Tuesday. **None of them exist in the v4 book**, which is why it can only ever
demonstrate a customer ringing about their own policy.

An **adviser firm is not a person.** `05-OPS:5.1` verifies the firm and its
regulator reference, not an individual, so the firm is a record in its own right
with a trading name and a reference — and no date of birth to be wrong about.
The individuals who may exercise its mandate are named under it.

Every value comes from `reserved`, which is the single definition of what a
synthetic identity looks like. Nothing here reads the wall clock: the as-of date
is injected, so the same seed produces the same people forever.
"""

from __future__ import annotations

import random
from datetime import date

from world.identities.reserved import (
    adult_dob,
    firm_name,
    firm_reference,
    reserved_address,
    reserved_email,
    synthetic_name,
    unique_reserved_phone,
)

POLICYHOLDER = "policyholder"
ADVISER = "adviser"
ATTORNEY = "attorney"
DEPUTY = "deputy"
TRUSTEE = "trustee"
PERSONAL_REPRESENTATIVE = "personal_representative"
ADVISER_FIRM = "adviser_firm"

# Everyone who is a person. `ADVISER_FIRM` is deliberately not here.
PERSON_ROLES = (POLICYHOLDER, ADVISER, ATTORNEY, DEPUTY, TRUSTEE,
                PERSONAL_REPRESENTATIVE)

# Party ids are banded by role so a reference is legible on sight: PH-2xxx is a
# holder, PH-4xxx an attorney. `PARTY_ID_RE` allows four digits, and the world
# needs a few hundred parties, so the bands are nowhere near colliding.
ID_BASE = {
    POLICYHOLDER: 2000,
    ADVISER: 3000,
    ATTORNEY: 4000,
    DEPUTY: 5000,
    TRUSTEE: 6000,
    PERSONAL_REPRESENTATIVE: 7000,
}

VULNERABILITY_CATEGORIES = ("communication", "recent_bereavement", "health")

# What the world holds by default. Each count is chosen to make a particular
# situation demonstrable rather than merely possible.
DEFAULT_HOLDERS = 200
DEFAULT_FIRMS = 12
DEFAULT_ADVISERS_PER_FIRM = (2, 4)
DEFAULT_ATTORNEYS = 14
DEFAULT_DEPUTIES = 5
DEFAULT_TRUSTEES = 24
DEFAULT_PERSONAL_REPRESENTATIVES = 8


def _person(rng: random.Random, role: str, number: int, as_of: date,
            names_used: set[str], phones_used: set[str], *,
            may_be_vulnerable: bool = False) -> dict:
    """One person of ``role``, entirely from reserved ranges."""
    n = ID_BASE[role] + number
    party_id = f"PH-{n:04d}"
    flag = None
    # A small, honest minority carry a support flag. Recorded on the customer's
    # own record, so only holders draw for one.
    if may_be_vulnerable and rng.random() < 0.06:
        flag = {"support_needs_ref": f"SN-{n:04d}",
                "category": rng.choice(VULNERABILITY_CATEGORIES)}
    return {
        "role": role,
        "party_id": party_id,
        "name": synthetic_name(rng, names_used),
        "dob": adult_dob(rng, as_of),
        "registered_address": reserved_address(rng),
        "contact": {
            "phone": unique_reserved_phone(rng, phones_used),
            "email": reserved_email(party_id.lower()),
            "registered": True,
        },
        "scottish_taxpayer": rng.random() < 0.15,
        "vulnerability_flag": flag,
        # Verification happens only at the gate, at runtime. A generated party
        # must never arrive already verified.
        "id_verified_level": None,
    }


def _firm(rng: random.Random, index: int, names_used: set[str],
          refs_used: set[str], phones_used: set[str],
          individuals: list[str]) -> dict:
    """One adviser firm — an organisation, with the people it has named."""
    firm_id = f"AF-{index:03d}"
    return {
        "role": ADVISER_FIRM,
        "firm_id": firm_id,
        "name": firm_name(rng, names_used),
        "firm_ref": firm_reference(rng, refs_used),
        "registered_address": reserved_address(rng),
        "contact": {
            "phone": unique_reserved_phone(rng, phones_used),
            "email": reserved_email(firm_id.lower()),
            "registered": True,
        },
        "individuals": individuals,
    }


def generate_identities(
    *,
    seed: int,
    as_of: date,
    holders: int = DEFAULT_HOLDERS,
    firms: int = DEFAULT_FIRMS,
    advisers_per_firm: tuple[int, int] = DEFAULT_ADVISERS_PER_FIRM,
    attorneys: int = DEFAULT_ATTORNEYS,
    deputies: int = DEFAULT_DEPUTIES,
    trustees: int = DEFAULT_TRUSTEES,
    personal_representatives: int = DEFAULT_PERSONAL_REPRESENTATIVES,
) -> list[dict]:
    """Everyone the world needs, deterministic for ``seed`` and ``as_of``."""
    if holders < 1:
        raise ValueError(f"a world needs at least one policyholder, got {holders}")
    rng = random.Random(seed)
    names_used: set[str] = set()
    firm_names_used: set[str] = set()
    phones_used: set[str] = set()
    refs_used: set[str] = set()
    world: list[dict] = []

    for i in range(holders):
        world.append(_person(rng, POLICYHOLDER, i + 1, as_of, names_used,
                             phones_used, may_be_vulnerable=True))

    adviser_number = 0
    for index in range(1, firms + 1):
        firm_id = f"AF-{index:03d}"
        individuals: list[str] = []
        for _ in range(rng.randint(*advisers_per_firm)):
            adviser_number += 1
            person = _person(rng, ADVISER, adviser_number, as_of, names_used,
                             phones_used)
            person["firm_id"] = firm_id
            world.append(person)
            individuals.append(person["party_id"])
        world.append(_firm(rng, index, firm_names_used, refs_used, phones_used,
                          individuals))

    for role, count in ((ATTORNEY, attorneys), (DEPUTY, deputies),
                        (TRUSTEE, trustees),
                        (PERSONAL_REPRESENTATIVE, personal_representatives)):
        for i in range(count):
            world.append(_person(rng, role, i + 1, as_of, names_used, phones_used))

    return world
