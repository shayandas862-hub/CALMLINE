"""The reserved ranges every invented identity is drawn from.

**The only place in the system that decides what a synthetic person looks
like.** The v4 identity manifest (`scripts/generate_policyholders.py`) and the
world's own cast both draw from here, because two copies of a rule is how they
end up disagreeing — and a drifted copy is how a detail stops being reserved
without anyone noticing.

No value produced here can belong to a real person, and that is **structural
rather than promised** (D-CL-022):

- **Names** are ``<GivenToken> <FamilyToken> <number>``, drawn from mineral,
  geometry and astronomy vocabularies — never human given-name or surname
  lists — and the mandatory numeric tag makes the whole string impossible as a
  real legal name ("Delta Meridian 41").
- **Telephone numbers** sit in Ofcom's reserved fictional mobile range
  07700 900000–900999, which is never allocated to a real subscriber.
- **Emails** use example.org, reserved by RFC 2606 and unregistrable.
- **Postcodes** use the unallocated ZZ area; streets and towns are invented.
- **Dates of birth** are real, valid dates against an **injected** as-of date.
  The wall clock is never read.

Random values would eventually collide with a real person. Reserved ones
cannot. That is the whole argument, and it is why none of these ranges is a
matter of taste.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

# Vocabularies chosen for being obviously non-human (minerals, geometry,
# astronomy, weather instruments) — deliberately NOT name-like corpora.
GIVEN_TOKENS = (
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Theta", "Kappa",
    "Lambda", "Sigma", "Omega", "Vector", "Quartz", "Cobalt", "Argon",
    "Xenon", "Helix", "Prism", "Tensor", "Lumen", "Vertex", "Zenith",
    "Raster", "Cipher", "Isobar",
)
FAMILY_TOKENS = (
    "Meridian", "Basalt", "Gabbro", "Feldspar", "Cumulus", "Nimbus",
    "Perigee", "Apogee", "Quasar", "Nebula", "Solstice", "Equinox",
    "Lattice", "Gradient", "Fulcrum", "Keystone", "Cornice", "Azimuth",
    "Parallax", "Spectrum", "Traverse", "Contour", "Pendulum", "Gnomon",
)
STREET_SUFFIXES = ("Way", "Row", "Walk", "Rise", "Approach")
TOWNS = ("Demoford", "Sampleton", "Mocksby", "Fixture Vale", "Placeholder Heath")
POSTCODE_LETTERS = "ABDEFGHJLNPQRSTUWXYZ"  # valid inward postcode letters

# 25 given × 24 family × 999 tags = 599,400 distinct names. The world needs a
# few hundred, so uniqueness is never under pressure.
NAME_SPACE = len(GIVEN_TOKENS) * len(FAMILY_TOKENS) * 999

# What an adviser firm is called. A firm is an organisation, not a person, so
# it takes a place-ish token and a trading suffix rather than a personal name.
FIRM_SUFFIXES = (
    "Wealth", "Financial Planning", "Advisory", "Asset Management",
    "Independent Advisers", "Private Clients",
)


def synthetic_name(rng: random.Random, used: set[str]) -> str:
    """A name that cannot be a real person's, unique within ``used``."""
    while True:
        name = (f"{rng.choice(GIVEN_TOKENS)} {rng.choice(FAMILY_TOKENS)} "
                f"{rng.randint(1, 999)}")
        if name not in used:
            used.add(name)
            return name


def adult_dob(rng: random.Random, as_of: date) -> str:
    """A valid date of birth, 25–90 years before the **injected** ``as_of``."""
    age_days = rng.randint(25 * 365 + 7, 90 * 365)
    return (as_of - timedelta(days=age_days)).isoformat()


def reserved_address(rng: random.Random) -> str:
    """An invented street and town in the unallocated ZZ postcode area."""
    street = f"{rng.choice(FAMILY_TOKENS)} {rng.choice(STREET_SUFFIXES)}"
    postcode = (f"ZZ{rng.randint(1, 99)} {rng.randint(1, 9)}"
                f"{rng.choice(POSTCODE_LETTERS)}{rng.choice(POSTCODE_LETTERS)}")
    return f"{rng.randint(1, 220)} {street}, {rng.choice(TOWNS)}, {postcode}"


# Ofcom's fictional mobile range is 07700 900000–900999 — exactly a thousand
# numbers, and the only ones that can never be allocated to a real subscriber.
RESERVED_PHONE_COUNT = 1000


def reserved_phone(rng: random.Random) -> str:
    """A number from Ofcom's fictional range — never a real subscriber."""
    return f"07700 900{rng.randint(0, 999):03d}"


def unique_reserved_phone(rng: random.Random, used: set[str]) -> str:
    """A reserved number no other party already holds.

    The range holds a thousand numbers and the world needs a few hundred, so
    independent draws collide **by the birthday problem rather than by bad
    luck**: three hundred parties produce around forty-five duplicates on every
    seed. Two people sharing a registered mobile is a fault a real book would
    not have, and it would quietly spoil any question that begins "the number
    they are calling from".

    ``reserved_phone`` stays the unguarded draw: the v4 identity manifest is
    committed and has to reproduce byte for byte.
    """
    if len(used) >= RESERVED_PHONE_COUNT:
        raise ValueError(
            f"the reserved range holds only {RESERVED_PHONE_COUNT} numbers "
            f"and all are taken — a world this large cannot stay reserved")
    while True:
        phone = reserved_phone(rng)
        if phone not in used:
            used.add(phone)
            return phone


def reserved_email(local: str) -> str:
    """An address on the RFC 2606 domain, which cannot be registered."""
    return f"{local}@example.org"


def firm_name(rng: random.Random, used: set[str]) -> str:
    """An adviser firm's trading name, unique within ``used``."""
    while True:
        name = f"{rng.choice(FAMILY_TOKENS)} {rng.choice(FIRM_SUFFIXES)}"
        if name not in used:
            used.add(name)
            return name


def firm_reference(rng: random.Random, used: set[str]) -> str:
    """A regulator reference that cannot collide with a real firm's.

    The FCA register is numeric, so a reference carrying a letter is not a
    well-formed FRN and can never match one. There is **no officially reserved
    FRN range** — unlike the phone, postcode and email ranges above — so this
    buys its safety from being malformed rather than from being set aside, and
    says so rather than implying a reservation that does not exist.
    """
    while True:
        reference = f"Z{rng.randint(0, 999_999):06d}"
        if reference not in used:
            used.add(reference)
            return reference
