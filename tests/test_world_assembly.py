"""What `build_book` assembles around the money, and the references it mints.

Split out of `test_world_book.py` at the 300-line rule. That file proves the two
hundred **reconcile**; this one proves the things hanging off them exist and can
be told apart.

Both tests here were written in v4.5 phase 3 against faults phase 2 left behind,
and both are the same shape of fault: something built, tested in isolation, and
never checked once the whole book existed.
"""

from __future__ import annotations

from world import WORLD_BIRTH_DATE
from world.lifetimes.build import build_book

SEED = 11

_BOOK = None


def book():
    """Built once — two hundred policies is not free, and it is deterministic."""
    global _BOOK
    if _BOOK is None:
        _BOOK = build_book(seed=SEED, born=WORLD_BIRTH_DATE)
    return _BOOK

def test_the_book_carries_its_trusts_mandates_and_authorities():
    """Phase 2 built all three allocators and phase 2's tests called them —
    but `build_book` did not, so the world's policies carried no trust, no
    adviser mandate and no attorney. The bucket plan's §4, §5 and §6 counts
    described data that reached nothing, and the refusal register's most
    important rows — a trust never executed, an LOA that cannot change bank
    details, an attorney who cannot change trustees — had no policy behind
    them. Found in phase 3 when the reference sheet asked for them.
    """
    world = book()
    assert len(world.trusts) == 32                      # §4
    assert len(world.adviser_mandates) == 46            # §5
    assert sum(len(a) for a in world.authorities.values()) == 27  # §6: 14+5+8

    numbers = {p.policy_no for p in world.policies}
    for held in (world.trusts, world.adviser_mandates, world.authorities):
        assert set(held) <= numbers, "an authority against no policy in the book"


def test_no_two_policies_share_a_contact_or_case_reference():
    """`_reference` promises that "two policies can never collide". It did not.

    It computed ``(policy digits x 1000 + index) mod 10^width``, and eight
    policy digits plus a three-digit index is eleven — so the modulo threw the
    **leading** digits away. Every product shares a digit sequence
    (`LP-20000137`, `HB-20000137`, `RA-20000137` all exist), so their contacts
    reduced to the same reference: 819 distinct `CN-` for 1,409 contacts, 388
    of them shared.

    It matters because a contact note is keyed on its `CN-` and the change
    journal attributes edits to a `CN-` or `CW-`. Two calls sharing a reference
    are two calls whose notes land on each other — and phase 4 writes a note
    per contact.
    """
    world = book()
    for name, refs in (
            ("CN", [(c.cn_ref, p) for p in world.policies
                    for c in world.operations[p.policy_no].contacts]),
            ("CW", [(k.cw_ref, p) for p in world.policies
                    for k in world.operations[p.policy_no].cases]),
            ("EVD", [(e.evidence_id, p) for p in world.policies
                     for k in world.operations[p.policy_no].cases
                     for e in k.evidence])):
        seen = {ref for ref, _ in refs}
        assert len(seen) == len(refs), (
            f"{name}: {len(seen)} distinct references for {len(refs)} items")


# ── the holder was alive, and an adult, when the policy started ──────────
def test_no_policy_starts_before_its_holder_was_an_adult():
    """Found in phase 3 by reading twenty policies, not by a test.

    Start dates were drawn from a per-product year span and holders were
    assigned by a separate shuffle; the two were never compared. **Twenty-four
    of the two hundred started before their holder turned eighteen, and one
    started two and a half years before the holder was born** — on a life that
    then died aged four and paid a claim.

    The synthetic eighty have had this property since v4 (D-CL-029, "always
    age-consistent, so the oldest policies sit with the oldest holders"). The
    world did not inherit it.
    """
    from datetime import date

    from world.lifetimes.build import load_people

    dobs = {p["party_id"]: date.fromisoformat(p["dob"])
            for p in load_people() if "party_id" in p}

    offenders = []
    for policy in book().policies:
        dob = dobs[policy.holder_party_id]
        years = (policy.start - dob).days / 365.25
        if years < 18:
            offenders.append(f"{policy.policy_no} holder born {dob} "
                             f"started {policy.start} (age {years:.1f})")

    assert not offenders, (
        f"{len(offenders)} policies start before their holder was 18: "
        + "; ".join(offenders[:5]))


# ── a closed policy says how it closed, and stops behaving as if open ────
#
# What the status implies, per product. A pension pays **benefits**, never a
# claim in the whole-of-life sense, so `benefit_taken` is its terminal marker.
TERMINAL_EVENT = {
    ("lifelong_protection", "claimed"): "claim_paid",
    ("horizon_bond", "claimed"): "claim_paid",
    ("retirement_account", "claimed"): "benefit_taken",
    ("lifelong_protection", "lapsed"): "lapse",
    ("retirement_account", "lapsed"): "lapse",
    ("lifelong_protection", "paid_up"): "paid_up",
    ("retirement_account", "paid_up"): "paid_up",
    ("lifelong_protection", "surrendered"): "surrender",
    ("horizon_bond", "surrendered"): "surrender",
}


def test_every_closed_policy_records_how_it_closed():
    """Fourteen policies carried a terminal status with nothing in their
    history saying so — `RA-20000959` was `paid_up`, `RA-20001370` was
    `lapsed`, `HB-20007535` was `surrendered`, and none of the three had a
    single event. The status was assigned by the bucket plan and the history
    never caught up with it.

    Cause: both players guarded the terminal event on `len(statements) > 2`, so
    a policy too young to have three statements silently skipped it, and the
    pension player had no lapse or paid-up path at all.
    """
    offenders = []
    for policy in book().policies:
        want = TERMINAL_EVENT.get((policy.product, policy.status))
        if want and want not in {e.kind for e in policy.events}:
            offenders.append(f"{policy.policy_no} [{policy.status}] "
                             f"has no {want}")
    assert not offenders, (
        f"{len(offenders)} closed policies never say how: "
        + "; ".join(offenders[:6]))


def test_a_closed_policy_stops_taking_money_in():
    """The status was not merely unrecorded, it was contradicted: `RA-20001370`
    was `lapsed` and contributed £7,270.68 in 2026, holding £186,701. A paid-up
    or lapsed policy takes nothing further in — that is what the words mean."""
    offenders = []
    for policy in book().policies:
        if policy.status not in {"lapsed", "paid_up"}:
            continue
        ceased = [e.on for e in policy.events
                  if e.kind in {"lapse", "paid_up"}]
        if not ceased:
            continue
        after = [e for e in policy.entries
                 if e.transaction.kind in {"contribution", "premium"}
                 and e.transaction.at[:10] > max(ceased).isoformat()]
        if after:
            offenders.append(f"{policy.policy_no} [{policy.status}] took "
                             f"{len(after)} payments in after {max(ceased)}")
    assert not offenders, "; ".join(offenders[:6])


def test_no_death_is_notified_twice():
    """A death claim is paid once and the policy is gone. `LP-20002055` was
    paid in 2003 and took a second bereavement notification in 2024.

    Two rows out of 1,409, and worth the fix only because phase 4 writes a note
    for every one of them — and there is no sensible note for notifying a death
    on a policy that was settled twenty-one years earlier.
    """
    offenders = []
    for policy in book().policies:
        paid = [e.transaction.at[:10] for e in policy.entries
                if e.transaction.kind == "claim_payment"]
        if not paid:
            continue
        for contact in book().operations[policy.policy_no].contacts:
            if (contact.intent == "bereavement_notification"
                    and contact.on.isoformat() > min(paid)):
                offenders.append(f"{policy.policy_no} paid {min(paid)}, "
                                 f"notified again {contact.on}")
    assert not offenders, "; ".join(offenders)
