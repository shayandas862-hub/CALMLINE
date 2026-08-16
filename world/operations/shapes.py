"""What a past contact and a past case look like, before anyone writes the words.

These are the skeleton: dates, references, vocabulary and ordering. The prose
belongs to phase 4, which reads a policy's finished numbers and writes the human
half by hand into a committed file. **Nothing here generates a sentence**, and
`note_slot` is deliberately empty rather than absent — an empty slot says "this
call has a note coming"; a missing field says nothing at all.

`intent`, `outcome`, `channel` and `satisfies` are closed vocabularies the
schema already carries, not prose. "Requested a withdrawal" is a category; what
the customer actually said is a note.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

CHANNELS = ("phone", "portal", "email", "post", "adviser_portal")

# What a customer rings about. Categories from `05-OPS:6`'s servicing
# procedures, not descriptions of any particular call.
INTENTS = (
    "valuation_request", "withdrawal_request", "surrender_request",
    "address_change", "bank_change", "adviser_authority", "complaint",
    "premium_query", "review_query", "benefit_enquiry", "trust_query",
    "bereavement_notification",
)

OUTCOMES = ("resolved", "case_raised", "referred", "information_given",
            "refused_verification")

# `cases.type` (`0001_init.sql:313`).
CASE_TYPES = ("servicing", "DSAR", "transfer", "review", "claim_linked")


@dataclass(frozen=True)
class PlannedContact:
    """One past contact, without a word of what was said."""

    cn_ref: str
    policy_no: str
    on: date
    channel: str
    intent: str
    outcome: str
    # Phase 4 fills this. Empty and present, rather than absent.
    note_slot: str = ""


@dataclass(frozen=True)
class PlannedEvidence:
    """One thing that came in, against the requirement it answers."""

    evidence_id: str
    requirement: str
    requirement_source: str
    received_on: date
    satisfies: str
    received_via: str = "post"


@dataclass(frozen=True)
class PlannedCase:
    """One piece of past work, finished.

    ``status`` is always ``completed``: everything historical is finished
    business. **The schema has no terminal refusal** — `cases.status` offers
    `pending_review`, `completed`, `blocked` and `held_for_review` — so a refused
    case is `completed` carrying a ``human_decision`` that says it was refused.
    That missing exit is v4.5's own architectural finding and is not invented
    here.

    ``authorised_movement_on`` is the date of the money this case let out, or
    ``None`` for work that moved nothing. It exists so the ordering guarantee is
    checkable rather than assumed.
    """

    cw_ref: str
    policy_no: str
    cn_ref: str
    opened_on: date
    closed_on: date
    request: str
    type: str
    status: str
    human_decision: str
    evidence: tuple[PlannedEvidence, ...] = ()
    authorised_movement_on: Optional[date] = None


@dataclass(frozen=True)
class PolicyOperations:
    """One policy's whole operational history, without words."""

    policy_no: str
    contacts: tuple[PlannedContact, ...]
    cases: tuple[PlannedCase, ...]
