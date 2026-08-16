"""Trusts, adviser mandates, third-party authorities and bank mandates.

Everything here exists to be *refused* on some policies and allowed on others,
so the counts are the point. They come from the bucket plan and are met exactly.

Corpus rules this is built to:

- `05-OPS:5.1` — an LOA names Aldercrest and the firm, and the firm's FRN is
  checked on the FCA Register. It does **not** authorise receiving claim or
  surrender proceeds, or changing the customer's bank details.
- `05-OPS:5.2` — an LPA is "valid only once **registered with the OPG**".
- `05-OPS:5.8` — trusteeship is **personal**, and registrability is decided by
  the product: "**bond trusts always registrable; pure-protection policy trusts
  excluded while the policy is held**". So a Lifelong Protection trust is not
  registrable and cannot be in breach for want of a URN — only bond trusts can.
- `05-OPS:3.4` — enhanced verification is required for "an address change
  followed within 30 days by a bank change or withdrawal", which is the fraud
  pattern the change history exists to make answerable.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.records.models import Policy
from world import WORLD_BIRTH_DATE
from world.lifetimes.authorities import (
    BANK_ON_HOLD,
    BANK_RECENTLY_CHANGED,
    BANK_UNVERIFIED,
    BANK_VERIFIED,
    DEPUTIES,
    MANDATES_TOTAL,
    PERSONAL_REPRESENTATIVES,
    RECENT_CHANGE_WINDOW_DAYS,
    TRUSTS_TOTAL,
    allocate_bank_mandates,
    allocate_mandates,
    allocate_third_party_authorities,
    allocate_trusts,
    is_registrable,
)

SEED = 11
PREFIX = {"lifelong_protection": "LP", "horizon_bond": "HB",
          "retirement_account": "RA"}


def _book():
    """A stand-in for the bucket plan's 200: 70 LP, 65 HB, 65 RA."""
    policies, n = [], 0
    for product, count in (("lifelong_protection", 70), ("horizon_bond", 65),
                           ("retirement_account", 65)):
        for _ in range(count):
            n += 1
            policies.append(Policy(
                policy_no=f"{PREFIX[product]}-{20_000_000 + n}",
                product=product, status="in_force",
                start_date="2015-03-01", holder_party_id="PH-2001"))
    return policies


def _firms():
    return [{"firm_id": f"AF-{i:03d}", "name": f"Firm {i}",
             "firm_ref": f"FRN-{600000 + i}",
             "individuals": [f"PH-{3000 + i * 3 + k}" for k in range(3)]}
            for i in range(1, 13)]


def _people(role, count, base):
    return [{"role": role, "party_id": f"PH-{base + i}"} for i in range(count)]


# ── registrability, which the product decides ────────────────────────────
def test_a_bond_trust_is_always_registrable():
    """`05-OPS:5.8` — "bond trusts always registrable"."""
    assert is_registrable("horizon_bond")


def test_a_pure_protection_trust_is_not_registrable_while_the_policy_is_held():
    """`05-OPS:5.8` — the exclusion ends only if proceeds are held more than two
    years after death, which no in-force policy has reached."""
    assert not is_registrable("lifelong_protection")


def test_a_pension_is_not_written_in_trust_at_all():
    """A Retirement Account passes by nomination and expression of wish
    (`03-PEN:9.6`), not by a policy trust."""
    assert not is_registrable("retirement_account")


# ── trusts ───────────────────────────────────────────────────────────────
def test_the_bucket_plans_trust_count_is_met_exactly():
    trusts = allocate_trusts(_book(), seed=SEED)
    assert len(trusts) == TRUSTS_TOTAL == 32


def test_six_trusts_were_never_properly_executed():
    trusts = allocate_trusts(_book(), seed=SEED)
    assert sum(1 for t in trusts.values() if t.executed == "no") == 6


def test_six_trusts_are_registrable_and_have_no_urn():
    """The refusal: a registrable trust cannot be dealt with until it is on the
    register, and these six are what make that demonstrable."""
    trusts = allocate_trusts(_book(), seed=SEED)
    unregistered = [t for t in trusts.values() if t.registrable and not t.urn]
    assert len(unregistered) == 6


def test_twenty_trusts_are_executed_and_registered_where_registrable():
    trusts = allocate_trusts(_book(), seed=SEED)
    good = [t for t in trusts.values()
            if t.executed == "yes" and (t.urn or not t.registrable)]
    assert len(good) == 20


def test_no_trust_is_marked_registrable_on_a_product_that_cannot_be():
    """`05-OPS:5.8` decides this, not the allocator."""
    book = {p.policy_no: p for p in _book()}
    for policy_no, trust in allocate_trusts(_book(), seed=SEED).items():
        if trust.registrable:
            assert is_registrable(book[policy_no].product)


def test_every_trust_names_at_least_one_trustee():
    """Instructions require all trustees (`05-OPS:5.8`), so a trust naming none
    could never be instructed at all."""
    for trust in allocate_trusts(_book(), seed=SEED).values():
        assert trust.trustees


def test_trust_allocation_is_deterministic():
    assert allocate_trusts(_book(), seed=SEED) == allocate_trusts(_book(),
                                                                  seed=SEED)


# ── adviser mandates ─────────────────────────────────────────────────────
def test_the_bucket_plans_mandate_count_is_met_exactly():
    mandates = allocate_mandates(_book(), _firms(), seed=SEED,
                                 born=WORLD_BIRTH_DATE)
    assert len(mandates) == MANDATES_TOTAL == 46


def test_eight_mandates_have_expired():
    mandates = allocate_mandates(_book(), _firms(), seed=SEED,
                                 born=WORLD_BIRTH_DATE)
    expired = [m for m in mandates.values()
               if date.fromisoformat(m.expiry) < WORLD_BIRTH_DATE]
    assert len(expired) == 8


def test_forty_of_the_forty_six_cannot_instruct_a_withdrawal():
    """The bucket plan's own figure: only six mandates carry withdrawals."""
    mandates = allocate_mandates(_book(), _firms(), seed=SEED,
                                 born=WORLD_BIRTH_DATE)
    with_withdrawals = [m for m in mandates.values()
                        if "withdrawals" in m.scope]
    assert len(with_withdrawals) == 6
    assert len(mandates) - len(with_withdrawals) == 40


def test_every_mandate_carries_information_and_servicing():
    """`05-OPS:5.1` — "Scope usually servicing and information"."""
    mandates = allocate_mandates(_book(), _firms(), seed=SEED,
                                 born=WORLD_BIRTH_DATE)
    for mandate in mandates.values():
        assert {"information", "servicing"} <= set(mandate.scope)


def test_every_mandate_names_individuals_from_its_own_firm():
    """A mandate belongs to the firm; the individuals are named under it. A
    name from another firm would pass the firm check and fail the person."""
    firms = {f["name"]: f for f in _firms()}
    mandates = allocate_mandates(_book(), _firms(), seed=SEED,
                                 born=WORLD_BIRTH_DATE)
    for mandate in mandates.values():
        assert mandate.individuals
        assert set(mandate.individuals) <= set(firms[mandate.firm]["individuals"])


def test_mandate_allocation_is_deterministic():
    first = allocate_mandates(_book(), _firms(), seed=SEED,
                              born=WORLD_BIRTH_DATE)
    second = allocate_mandates(_book(), _firms(), seed=SEED,
                               born=WORLD_BIRTH_DATE)
    assert first == second


# ── attorneys, deputies and personal representatives ─────────────────────
def test_the_bucket_plans_third_party_counts_are_met_exactly():
    authorities = allocate_third_party_authorities(
        _book(), attorneys=_people("attorney", 14, 4001),
        deputies=_people("deputy", 5, 5001),
        personal_representatives=_people("personal_representative", 8, 7001),
        seed=SEED)
    flat = [a for records in authorities.values() for a in records]
    assert sum(1 for a in flat if a.type in {"LPA", "EPA"}) == 14
    assert sum(1 for a in flat if a.type == "deputy") == DEPUTIES == 5
    assert sum(1 for a in flat if a.type == "PR") == PERSONAL_REPRESENTATIVES == 8


def test_three_lasting_powers_are_not_yet_registered():
    """`05-OPS:5.2` — an LPA is valid only once registered with the OPG, so
    these three are refused until it is."""
    authorities = allocate_third_party_authorities(
        _book(), attorneys=_people("attorney", 14, 4001),
        deputies=_people("deputy", 5, 5001),
        personal_representatives=_people("personal_representative", 8, 7001),
        seed=SEED)
    flat = [a for records in authorities.values() for a in records]
    assert sum(1 for a in flat
               if a.type == "LPA" and a.status == "unverified") == 3
    assert sum(1 for a in flat if a.type == "EPA") == 3


def test_no_attorney_or_deputy_is_given_a_trustee_scope():
    """`05-OPS:5.8` — trusteeship is personal, and this is the E22 failure mode.
    Nineteen policies exist on which it can be demonstrated being refused."""
    authorities = allocate_third_party_authorities(
        _book(), attorneys=_people("attorney", 14, 4001),
        deputies=_people("deputy", 5, 5001),
        personal_representatives=_people("personal_representative", 8, 7001),
        seed=SEED)
    for records in authorities.values():
        for authority in records:
            if authority.type in {"LPA", "EPA", "deputy"}:
                assert "trustee_change" not in authority.scope


# ── bank mandates, and the fraud pattern ─────────────────────────────────
def test_every_policy_has_a_bank_position():
    mandates = allocate_bank_mandates(_book(), seed=SEED, born=WORLD_BIRTH_DATE)
    assert len(mandates) == 200


def test_the_bucket_plans_bank_partition_is_met_exactly():
    mandates = allocate_bank_mandates(_book(), seed=SEED, born=WORLD_BIRTH_DATE)
    values = list(mandates.values())
    recent_from = WORLD_BIRTH_DATE - timedelta(days=RECENT_CHANGE_WINDOW_DAYS)

    on_hold = [m for m in values if m.hold_until]
    unverified = [m for m in values if not m.verified and not m.hold_until]
    recent = [m for m in values if m.verified and m.change_history
              and date.fromisoformat(m.change_history[-1].at[:10]) >= recent_from]
    settled = [m for m in values if m.verified and m not in recent]

    assert len(unverified) == BANK_UNVERIFIED == 18
    assert len(on_hold) == BANK_ON_HOLD == 12
    assert len(recent) == BANK_RECENTLY_CHANGED == 18
    assert len(settled) == BANK_VERIFIED == 152
    # §7 is a partition: the four groups are disjoint and cover all 200.
    assert (len(unverified) + len(on_hold) + len(settled)
            + len(recent)) == 200


def test_a_recent_change_falls_inside_the_ninety_day_window():
    """Bucket plan §7 — "changed within 90 days of the world's birth date"."""
    mandates = allocate_bank_mandates(_book(), seed=SEED, born=WORLD_BIRTH_DATE)
    earliest = WORLD_BIRTH_DATE - timedelta(days=RECENT_CHANGE_WINDOW_DAYS)
    for mandate in mandates.values():
        for change in mandate.change_history:
            assert date.fromisoformat(change.at[:10]) <= WORLD_BIRTH_DATE
        if mandate.verified and mandate.change_history:
            last = date.fromisoformat(mandate.change_history[-1].at[:10])
            if last >= earliest:
                assert earliest <= last <= WORLD_BIRTH_DATE


def test_a_change_history_is_kept_oldest_first():
    mandates = allocate_bank_mandates(_book(), seed=SEED, born=WORLD_BIRTH_DATE)
    for mandate in mandates.values():
        stamps = [c.at for c in mandate.change_history]
        assert stamps == sorted(stamps)


def test_bank_allocation_is_deterministic():
    first = allocate_bank_mandates(_book(), seed=SEED, born=WORLD_BIRTH_DATE)
    second = allocate_bank_mandates(_book(), seed=SEED, born=WORLD_BIRTH_DATE)
    assert first == second


def test_a_hold_is_dated_and_not_merely_flagged():
    mandates = allocate_bank_mandates(_book(), seed=SEED, born=WORLD_BIRTH_DATE)
    held = [m for m in mandates.values() if m.hold_until]
    assert held
    for mandate in held:
        assert date.fromisoformat(mandate.hold_until)


def test_a_book_smaller_than_the_plan_is_refused_rather_than_silently_short():
    with pytest.raises(ValueError):
        allocate_trusts(_book()[:10], seed=SEED)
