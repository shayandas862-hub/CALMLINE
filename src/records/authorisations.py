"""Who may instruct, and where money may go.

Two records that together answer "is this payment allowed to happen, on this
instruction, to this account" — the questions the identity gate and the money
path both ask, and neither of which is a property of the product.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from src.records.models import require_in

AUTHORITY_TYPES = frozenset({
    "LOA", "LPA", "EPA", "deputy", "PR", "trustee", "mandate", "one_off",
})
AUTHORITY_STATUSES = frozenset({"active", "expired", "unverified", "revoked"})

# Where a caller stands against the firm's mandate. Three, not a boolean: a
# mandate that names nobody is not the same fact as one that names people and
# does not name this caller. The first describes every mandate the corpus
# carries; the second describes somebody who should not be on the telephone.
MANDATE_NAMES_NOBODY = "names_nobody"
NAMED_ON_MANDATE = "named"
NOT_NAMED_ON_MANDATE = "not_named"
MANDATE_STANDINGS = frozenset({
    MANDATE_NAMES_NOBODY, NAMED_ON_MANDATE, NOT_NAMED_ON_MANDATE,
})


def mandate_standing(loa: Optional[Any], party_id: str) -> str:
    """Where ``party_id`` stands against an adviser firm's mandate.

    **A layer above the firm check, never a replacement for it.** `05-OPS:5.1`
    verifies the firm and its FRN and decides whether the mandate is valid at
    all; that is unchanged. This answers the other half of a real adviser call
    — the firm holds a valid mandate, and is this caller one of the people the
    firm named on it?

    Returns one of ``MANDATE_STANDINGS``. A missing mandate and a mandate that
    names nobody give the same answer, because in both cases there is no list
    to check the caller against — and the gate asks this before it knows which
    it has.
    """
    named = tuple(getattr(loa, "individuals", ()) or ())
    if not named:
        return MANDATE_NAMES_NOBODY
    return NAMED_ON_MANDATE if party_id in named else NOT_NAMED_ON_MANDATE


@dataclass(frozen=True)
class MandateChange:
    """One edit to the mandate, kept forever."""

    at: str
    actor: str
    note: str


@dataclass(frozen=True)
class BankMandate:
    """The control state behind the policy's displayed ``bank_last4``.

    ``change_history`` is the fraud watch: "bank changed, then a large
    withdrawal two weeks later" is only answerable because it exists.
    """

    policy_no: str
    account_last4: str
    verified: bool = False
    hold_until: Optional[str] = None
    change_history: tuple[MandateChange, ...] = ()

    def __post_init__(self) -> None:
        if not (len(self.account_last4) == 4 and self.account_last4.isdigit()):
            raise ValueError(f"{self.policy_no}: account_last4 must be four digits")


@dataclass(frozen=True)
class AuthorityRecord:
    """A third party's authority over a policy — checked at the identity gate,
    with its scope enforced in code (AD-CL-033)."""

    authority_id: str
    policy_no: str
    party_id: str
    type: str
    scope: tuple[str, ...] = ()
    evidence_ref: str = ""
    verified_date: Optional[str] = None
    status: str = "unverified"

    def __post_init__(self) -> None:
        require_in(self.authority_id, "authority type", self.type, AUTHORITY_TYPES)
        require_in(self.authority_id, "authority status", self.status, AUTHORITY_STATUSES)


