"""Placing past contacts and cases in time, so the ordering is provable.

Two properties, both about order rather than content:

- **A case that authorised money is dated before the money moved.** Approval is
  the only path that moves money, so a payment with no prior case — or with one
  dated after it — is a control that never operated. Every money-out movement
  gets a contact, then a case, then the payment, in that order.
- **Everything historical is finished business.** No open cases and nothing
  half-done: a queue of thirty-year-old work in progress is not a book anybody
  would recognise.

The distribution is deliberately **uneven**. An even spread is what a generator
produces when nobody thought about it, and it is the first thing that reads as
synthetic: real books have policies nobody has ever rung about and a handful
that generate a call a quarter.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Sequence

from world import WORLD_BIRTH_DATE
from world.lifetimes.timeline import Movement
from world.lifetimes.workingdays import add_working_days
from world.operations.shapes import (
    CHANNELS,
    INTENTS,
    PlannedCase,
    PlannedContact,
    PlannedEvidence,
    PolicyOperations,
)

# Movements that took money out **at a customer's request**, and so needed a
# case behind them. A charge and an investment loss are not requests — nobody
# rang up to ask for the annual management charge.
MONEY_OUT_KINDS = frozenset({
    "withdrawal", "surrender", "payout", "claim_payment",
    "regular_withdrawal", "segment_surrender", "ufpls_payment",
})

# What a case asks for, and where the requirement behind its evidence comes
# from. Sources are real clause references, so evidence points at a rule.
REQUIREMENTS = (
    ("identity confirmed to standard verification", "05-OPS:3.2"),
    ("bank mandate verified", "05-OPS:6.3"),
    ("written instruction received", "05-OPS:6.1"),
    ("trustee signatures obtained", "05-OPS:5.8"),
    ("adviser authority checked against the FCA Register", "05-OPS:5.1"),
    ("source of funds evidenced", "05-OPS:13"),
)

# Weights for how many contacts a policy has ever had. Index is the count.
# Most policies a few, a real share none at all, a handful many.
CONTACT_WEIGHTS = (14, 22, 22, 16, 10, 6, 4, 3, 2, 1)

# Requests that get turned down often enough to be worth having in the book.
REFUSABLE_INTENTS = ("withdrawal_request", "surrender_request",
                     "adviser_authority", "trust_query", "bank_change")

# Why work was refused, and the clause that refused it. A refusal with no rule
# behind it is somebody's opinion.
REFUSAL_REASONS = (
    ("instruction fell outside the verified adviser scope", "05-OPS:5.1"),
    ("an LOA cannot change the customer's bank details", "05-OPS:5.1"),
    ("the trust was never properly executed", "05-OPS:5.8"),
    ("all trustees must instruct and one did not", "05-OPS:5.8"),
    ("the power of attorney is not yet registered with the OPG", "05-OPS:5.2"),
    ("identity could not be verified to the required standard", "05-OPS:3.2"),
)


def contact_distribution(policy_nos: Sequence[str], *,
                         seed: int) -> dict[str, int]:
    """How many contacts each policy has ever had. Uneven on purpose."""
    counts: dict[str, int] = {}
    for policy_no in sorted(policy_nos):
        rng = random.Random(f"{seed}:contacts:{policy_no}")
        counts[policy_no] = rng.choices(range(len(CONTACT_WEIGHTS)),
                                        weights=CONTACT_WEIGHTS)[0]
    return counts


# One digit per product, so a reference carries which book its policy is in.
# Without it `LP-20000137`, `HB-20000137` and `RA-20000137` — all three of which
# exist — reduce to the same digits and their contacts collide.
PRODUCT_DIGIT = {"LP": 1, "HB": 2, "RA": 3}

# What a reference reserves for the item's own position within its policy.
INDEX_DIGITS = 3


def _reference(prefix: str, digits: int, policy_no: str, index: int) -> str:
    """A deterministic reference derived from the policy it belongs to.

    Three fields, and the widths are the whole point: **one digit of product,
    then the policy's serial, then the item's index.**

    The obvious version — ``(policy digits * 1000 + index) % 10**digits`` —
    was wrong and quietly so. Eight policy digits plus a three-digit index is
    eleven, so the modulo discarded the **leading** digits rather than the
    trailing ones: `LP-20000137`, `HB-20000137` and `RA-20000137` all reduced to
    137000 and shared every contact reference between them. 819 distinct `CN-`
    for 1,409 contacts. A contact note is keyed on its `CN-`, so two calls
    sharing one are two calls whose notes land on each other.

    The serial is taken modulo whatever room is left, which is safe because the
    generated block is narrower than that room — and `build_book` asserts across
    the whole finished world that no two items share a reference, so widening
    the block later fails loudly here instead of silently colliding again.
    """
    room = digits - INDEX_DIGITS - 1
    product = PRODUCT_DIGIT.get(policy_no[:2], 9)
    serial = abs(int("".join(c for c in policy_no if c.isdigit()) or "0"))
    value = (product * 10 ** (digits - 1)
             + (serial % 10 ** room) * 10 ** INDEX_DIGITS
             + index % 10 ** INDEX_DIGITS)
    return f"{prefix}-{value:0{digits}d}"


def plan_operations(policy_no: str, movements: Sequence[Movement], *,
                    start: date, seed: int,
                    born: date = WORLD_BIRTH_DATE) -> PolicyOperations:
    """One policy's contacts and cases, placed in time."""
    if start > born:
        raise ValueError(
            f"{policy_no} starts {start.isoformat()}, after the world's birth "
            f"date {born.isoformat()}")

    rng = random.Random(f"{seed}:operations:{policy_no}")
    contacts: list[PlannedContact] = []
    cases: list[PlannedCase] = []
    index = 0

    def add_contact(on: date, intent: str, outcome: str) -> PlannedContact:
        nonlocal index
        index += 1
        contact = PlannedContact(
            cn_ref=_reference("CN", 10, policy_no, index),
            policy_no=policy_no, on=on,
            channel=rng.choice(CHANNELS), intent=intent, outcome=outcome)
        contacts.append(contact)
        return contact

    # Every money-out movement gets a contact, then a case, then the payment.
    for movement in movements:
        if movement.kind not in MONEY_OUT_KINDS:
            continue
        # Far enough ahead that the case can open, gather evidence and close
        # before the money moves, and never before the policy started.
        called_on = max(start, movement.on - timedelta(days=rng.randint(14, 40)))
        contact = add_contact(called_on, _intent_for(movement.kind),
                              "case_raised")
        cases.append(_case_for(policy_no, contact, movement, rng, index))

    # Work that was asked for and refused. A queue where everything proceeded
    # is a queue whose refusal path has never been exercised, and roughly one
    # request in six is turned down for authority, evidence or eligibility.
    span = (born - start).days
    if span > 60 and rng.random() < 0.18:
        called_on = start + timedelta(days=rng.randrange(span - 30))
        contact = add_contact(called_on, rng.choice(REFUSABLE_INTENTS),
                              "case_raised")
        cases.append(_refused_case(policy_no, contact, rng, index))

    # Ordinary contact that raised nothing — most of a book's traffic.
    #
    # A death is notified once. After the claim is paid the policy is gone, so
    # a second bereavement notification is not a late call but an impossible
    # one — and phase 4 would have to invent a note for it.
    settled = min((m.on for m in movements if m.kind == "claim_payment"),
                  default=None)
    if span > 0:
        for _ in range(rng.choice(range(len(CONTACT_WEIGHTS)))):
            called_on = start + timedelta(days=rng.randrange(span))
            allowed = INTENTS
            if settled is not None and called_on > settled:
                allowed = tuple(i for i in INTENTS
                                if i != "bereavement_notification")
            add_contact(called_on, rng.choice(allowed),
                        rng.choice(("resolved", "information_given",
                                    "referred", "refused_verification")))

    contacts.sort(key=lambda c: (c.on, c.cn_ref))
    cases.sort(key=lambda c: (c.opened_on, c.cw_ref))
    return PolicyOperations(policy_no, tuple(contacts), tuple(cases))


def _intent_for(kind: str) -> str:
    if kind in {"surrender", "segment_surrender"}:
        return "surrender_request"
    if kind == "claim_payment":
        return "bereavement_notification"
    if kind == "ufpls_payment":
        return "benefit_enquiry"
    return "withdrawal_request"


def _case_for(policy_no: str, contact: PlannedContact, movement: Movement,
              rng: random.Random, index: int) -> PlannedCase:
    """A completed case, closing before the money it authorised moved."""
    opened_on = add_working_days(contact.on, 1)
    closed_on = min(add_working_days(opened_on, rng.randint(2, 6)), movement.on)
    if closed_on < opened_on:
        opened_on = closed_on

    requirement, source = REQUIREMENTS[rng.randrange(len(REQUIREMENTS))]
    evidence = (PlannedEvidence(
        evidence_id=_reference("EVD", 9, policy_no, index),
        requirement=requirement, requirement_source=source,
        received_on=min(max(opened_on, contact.on), closed_on),
        satisfies="yes", received_via=contact.channel),)

    return PlannedCase(
        cw_ref=_reference("CW", 9, policy_no, index),
        policy_no=policy_no, cn_ref=contact.cn_ref,
        opened_on=opened_on, closed_on=closed_on,
        request=f"{contact.intent} — {movement.amount_pence}p",
        type="servicing", status="completed", human_decision="proceed",
        evidence=evidence, authorised_movement_on=movement.on)


def _refused_case(policy_no: str, contact: PlannedContact,
                  rng: random.Random, index: int) -> PlannedCase:
    """A request that was turned down, and the clause that turned it down.

    ``authorised_movement_on`` is ``None``: nothing moved, which is the whole
    point. The evidence that arrived did **not** satisfy its requirement, which
    is usually why.
    """
    opened_on = add_working_days(contact.on, 1)
    closed_on = add_working_days(opened_on, rng.randint(2, 8))
    reason, source = REFUSAL_REASONS[rng.randrange(len(REFUSAL_REASONS))]
    evidence = (PlannedEvidence(
        evidence_id=_reference("EVD", 9, policy_no, index + 500),
        requirement=reason, requirement_source=source,
        received_on=opened_on, satisfies="no", received_via=contact.channel),)

    return PlannedCase(
        cw_ref=_reference("CW", 9, policy_no, index + 500),
        policy_no=policy_no, cn_ref=contact.cn_ref,
        opened_on=opened_on, closed_on=closed_on,
        request=f"{contact.intent} — refused",
        type="servicing", status="completed", human_decision="refused",
        evidence=evidence, authorised_movement_on=None)
