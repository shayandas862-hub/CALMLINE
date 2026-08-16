"""Core data shapes for the system of record.

Money is integer PENCE everywhere — never a float — so balances are exact.
A transaction's ``amount_pence`` is a positive magnitude; its ``kind`` decides
whether it credits or debits the balance (applied by the ledger engine).

``Policy`` holds only what all three Aldercrest products share. Per-product
detail — cover, funds, segments, contributions, pension tax — lives in
``src.records.products``, because a single flat policy row cannot carry three
genuinely different sets of mechanics without lying about one of them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Movement kinds, split by the direction they push the balance. The vocabulary
# grows per product: a bond's regular withdrawal and a pension's UFPLS payment
# are not the same event, and the ledger should not pretend they are.
#
# The last four are what happens to a policy between the phone calls — the fund
# rising and falling, the annual management charge, the bonus added at an
# interval. Each is named for what it is rather than folded into the generic
# adjustment above, because "why is it worth less than last year" is a question
# the history has to be able to answer. A fall is `investment_loss`, a separate
# kind, rather than a signed `investment_return`: that keeps `amount_pence` a
# magnitude with the kind carrying the direction, which is what the money guard,
# the ledger's overdraw check and the store's SQL all already rely on.
CREDIT_KINDS = frozenset({
    "opening", "premium", "contribution", "transfer_in", "credit_adjustment",
    "investment_return", "bonus",
})
DEBIT_KINDS = frozenset({
    "withdrawal", "surrender", "payout", "claim_payment",
    "regular_withdrawal", "segment_surrender", "ufpls_payment", "debit_adjustment",
    "investment_loss", "charge",
})
ALL_KINDS = CREDIT_KINDS | DEBIT_KINDS

# Vocabularies from the data dictionary (KB `05-OPS:19`), snake_case.
PRODUCTS = frozenset({"lifelong_protection", "horizon_bond", "retirement_account"})
POLICY_STATUSES = frozenset({"in_force", "lapsed", "paid_up", "claimed", "surrendered"})
LIVES_ASSURED_BASES = frozenset({"single", "joint_last_survivor"})
LOA_SCOPES = frozenset({"servicing", "information", "switches", "withdrawals"})
ID_VERIFICATION_LEVELS = frozenset({"SV", "EV"})

# Reference grammars (KB `05-OPS:1.4`). The prefix is the product marker.
POLICY_NO_RE = re.compile(r"^(LP|HB|RA)-\d{8}$")
PARTY_ID_RE = re.compile(r"^PH-\d{4}$")
PREFIX_PRODUCT = {
    "LP": "lifelong_protection",
    "HB": "horizon_bond",
    "RA": "retirement_account",
}


def gbp(pounds: float) -> int:
    """Pounds → integer pence. `gbp(50_000) == 5_000_000`."""
    return int(round(pounds * 100))


def format_gbp(pence: int) -> str:
    """Integer pence → a `£30,000.00` string (exact, no float rounding)."""
    sign = "-" if pence < 0 else ""
    pounds, p = divmod(abs(int(pence)), 100)
    return f"{sign}£{pounds:,}.{p:02d}"


def require_pence(owner: str, name: str, value: object) -> None:
    """Guard a money field: a non-negative integer number of pence."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{owner}: {name} must be a non-negative integer (pence)")


def require_in(owner: str, name: str, value: object, allowed: frozenset) -> None:
    """Guard a closed vocabulary — an unknown value raises rather than defaults."""
    if value not in allowed:
        raise ValueError(
            f"{owner}: unknown {name} {value!r} (expected one of {sorted(allowed)})"
        )


# ── Party ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Contact:
    """Contact points. ``registered`` marks these as the ones on the record."""

    phone: str
    email: str
    registered: bool = False


@dataclass(frozen=True)
class VulnerabilityFlag:
    """Special-category care: a reference and a category, never the detail."""

    support_needs_ref: str
    category: str


@dataclass(frozen=True)
class IdVerification:
    """A cached snapshot of the identity level. The verification history is
    authoritative; this exists so the page need not replay it to render."""

    level: str  # SV | EV
    at: str

    def __post_init__(self) -> None:
        require_in("IdVerification", "level", self.level, ID_VERIFICATION_LEVELS)


@dataclass(frozen=True)
class Party:
    """A person known to the book. Every value is synthetic."""

    party_id: str
    name: str
    dob: str
    registered_address: str
    contact: Contact
    scottish_taxpayer: bool = False
    vulnerability_flag: Optional[VulnerabilityFlag] = None
    id_verified_level: Optional[IdVerification] = None
    # The fourth standard-verification check (`05-OPS:3.2`), set at onboarding.
    # ``None`` for every party in the seeded book, because no source states one
    # — and inventing 83 of them would make the gate look stronger than it is.
    # The check is simply not askable against a record that does not hold it.
    memorable: Optional[str] = None

    def __post_init__(self) -> None:
        if not PARTY_ID_RE.match(self.party_id):
            raise ValueError(f"party_id {self.party_id!r} is not PH- plus four digits")


# ── Policy ───────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class LifeAssured:
    """A life the policy covers. ``party_id`` is null when the life is not a
    party we hold a record for (the HB sample's second life)."""

    name: str
    party_id: Optional[str] = None


@dataclass(frozen=True)
class Trust:
    """Trust arrangements as the sample records carry them."""

    kind: str
    executed: str
    trustees: tuple[str, ...] = ()
    registrable: bool = False
    urn: Optional[str] = None


@dataclass(frozen=True)
class AdviserLoa:
    """A letter of authority. ``scope`` is closed on purpose: an LOA carrying
    only servicing+information cannot instruct a withdrawal.

    The mandate belongs to the **firm** — `05-OPS:5.1` verifies the firm and its
    FRN, not a person — and ``individuals`` names the people the firm has said
    may exercise it. Empty is the corpus's own shape and stays meaningful:
    "this mandate names nobody" is a different fact from "this mandate does not
    name you" (see ``src.records.authorisations.mandate_standing``).
    """

    firm: str
    frn: str
    scope: tuple[str, ...]
    expiry: str
    individuals: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for item in self.scope:
            require_in("AdviserLoa", "scope entry", item, LOA_SCOPES)
        for party_id in self.individuals:
            # A person is a party id everywhere else in the store. Accepting a
            # display name here would make the mandate the one place somebody
            # can be identified by a string that can be typed two ways.
            if not PARTY_ID_RE.match(party_id):
                raise ValueError(
                    f"AdviserLoa: named individual {party_id!r} is not a party id")


@dataclass(frozen=True)
class Policy:
    """A policy. The balance is NOT stored here — the ledger is the single
    source of truth for the current value, and point-in-time value is a fold
    over it (``src.records.valuation``).
    """

    policy_no: str
    product: str
    status: str
    start_date: str
    holder_party_id: str
    lives_assured: tuple[LifeAssured, ...] = ()
    lives_assured_basis: str = "single"
    trust: Optional[Trust] = None
    adviser_loa: Optional[AdviserLoa] = None
    bank_last4: Optional[str] = None

    def __post_init__(self) -> None:
        if not POLICY_NO_RE.match(self.policy_no):
            raise ValueError(
                f"policy_no {self.policy_no!r} does not match ^(LP|HB|RA)-\\d{{8}}$"
            )
        require_in("Policy", "product", self.product, PRODUCTS)
        require_in("Policy", "status", self.status, POLICY_STATUSES)
        require_in("Policy", "lives_assured_basis", self.lives_assured_basis,
                   LIVES_ASSURED_BASES)
        expected = PREFIX_PRODUCT[self.policy_no[:2]]
        if self.product != expected:
            raise ValueError(
                f"{self.policy_no}: prefix implies {expected}, not {self.product}"
            )
        if self.bank_last4 is not None and not re.fullmatch(r"\d{4}", self.bank_last4):
            raise ValueError(f"{self.policy_no}: bank_last4 must be four digits")


# ── Transaction and the ledger row ───────────────────────────────────────
@dataclass(frozen=True)
class Transaction:
    """A requested movement. ``amount_pence`` is a positive magnitude; the
    ``kind`` decides the direction when the ledger applies it.
    """

    txn_id: str
    policy_no: str
    kind: str
    amount_pence: int
    reason: str
    actor: str
    at: str  # ISO timestamp, supplied by the caller (keeps the ledger deterministic)

    def __post_init__(self) -> None:
        require_in("Transaction", "kind", self.kind, ALL_KINDS)
        require_pence(self.txn_id, "amount_pence", self.amount_pence)

    @property
    def is_debit(self) -> bool:
        return self.kind in DEBIT_KINDS

    @property
    def signed_pence(self) -> int:
        """The movement's effect on the balance: negative for a debit."""
        return -self.amount_pence if self.is_debit else self.amount_pence


@dataclass(frozen=True)
class LedgerEntry:
    """A committed, immutable ledger row: the transaction plus the balance it
    left behind. ``seq`` is its position in the policy's history (1-based).
    """

    seq: int
    transaction: Transaction
    balance_after_pence: int
