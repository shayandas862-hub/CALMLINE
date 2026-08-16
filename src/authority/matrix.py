"""The compiled authority matrix — who may approve what, and when two must.

Every band is a data literal carrying the chunk that states it (AD-CL-028), and
the bands are genuinely **per product**: the withdrawal ladder is the bond's
(`02-BOND:II.13`), pension access is the pension's (`03-PEN:II.13`), the
death-claim ladder is whole-of-life's (`01-WOL:II.13`), and the cross-product
table is `05-OPS:14`. Each of those documents states its rows atomically —
"`authority: withdrawal ≤25000 → back_office`" — so these literals transcribe
the corpus rather than paraphrase it.

**Two controls, not one.** `07-RUNBOOK:4.3` is explicit that four-eyes and dual
authorisation are separate, additional controls: *"four-eyes tests correctness,
dual authorisation tests authority."* Four-eyes lives in the approval path
(maker ≠ checker); this module owns the value thresholds.

**Five levels, three roles.** The KB names five approval levels. The console has
three session roles and `ops` is read-only (CONTEXT.md), so exactly one role
approves anything and it approves the bottom band only. Everything above it is
refused for want of a level no session can hold. That is the honest outcome
rather than a modelling gap: the matrix says what the firm requires, and the
console says what this deployment can actually do (D-CL-048).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.records.models import gbp

# Ascending. ``ops`` is absent on purpose — oversight approves nothing.
APPROVAL_LEVELS = (
    "front_office", "back_office", "team_manager", "senior_manager",
    "head_of_claims",
)

# The session roles this console issues, mapped onto the KB's levels.
_ROLE_LEVELS = {"front_office": "front_office", "back_office": "back_office"}

# Above this, two distinct approvers are required (`05-OPS:14`, the "Dual
# authorisation" column: ✅ above £250,000). Strictly above — the threshold
# itself is not above itself.
DUAL_AUTH_ABOVE_PENCE = gbp(250_000)
DUAL_AUTH_SOURCE = "05-OPS:14"


@dataclass(frozen=True)
class Band:
    """One row of the matrix: a ceiling, who approves up to it, and its source."""

    transaction: str
    max_pence: Optional[int]        # ``None`` — no ceiling, the top band
    approver: str
    source: str
    dual: bool = False

    def covers(self, amount_pence: int) -> bool:
        return self.max_pence is None or amount_pence <= self.max_pence


# Transcribed from the atomic row records in each product's II.13, plus the
# cross-product table. Ordered by ceiling within each transaction.
MATRIX: tuple[Band, ...] = (
    # `authority: withdrawal ≤25000 → back_office` · `25000–100000 →
    # team_manager` · `>100000 → senior_manager (dual >250000)` — 02-BOND:II.13
    Band("withdrawal", gbp(25_000), "back_office", "02-BOND:II.13"),
    Band("withdrawal", gbp(100_000), "team_manager", "02-BOND:II.13"),
    Band("withdrawal", None, "senior_manager", "02-BOND:II.13", dual=True),

    # `authority: pension_access ≤50000 → back_office` · `50000–250000 →
    # team_manager` · `>250000 → senior_manager + dual` — 03-PEN:II.13
    Band("pension_access", gbp(50_000), "back_office", "03-PEN:II.13"),
    Band("pension_access", gbp(250_000), "team_manager", "03-PEN:II.13"),
    Band("pension_access", None, "senior_manager", "03-PEN:II.13", dual=True),

    # `authority: death_claim ≤50000 → back_office` · `50000–250000 →
    # team_manager` · `>250000 → senior_manager + dual` · `>1000000 →
    # head_of_claims + dual` — 01-WOL:II.13
    Band("death_claim", gbp(50_000), "back_office", "01-WOL:II.13"),
    Band("death_claim", gbp(250_000), "team_manager", "01-WOL:II.13"),
    Band("death_claim", gbp(1_000_000), "senior_manager", "01-WOL:II.13", dual=True),
    Band("death_claim", None, "head_of_claims", "01-WOL:II.13", dual=True),

    # `Top-up ≤ £25,000 → back office` · `Top-up > £25,000 / EDD case →
    # senior manager approves` — 05-OPS:14 (and 02-BOND:II.13)
    Band("top_up", gbp(25_000), "back_office", "05-OPS:14"),
    Band("top_up", None, "senior_manager", "05-OPS:14"),

    # `Transfer out / DB transfer → senior manager (advice verified),
    # ✅ high value` — 05-OPS:14 / 03-PEN:II.13
    Band("transfer_out", None, "senior_manager", "05-OPS:14", dual=True),
)

# How a ledger movement maps onto a matrix row. Reading the product is not
# cosmetic: £50,000 is inside the band for pension access and outside it for a
# bond withdrawal, so calling both "a withdrawal" would approve one of them
# wrongly.
_KIND_TRANSACTIONS = {
    "withdrawal": "withdrawal",
    "surrender": "withdrawal",
    "regular_withdrawal": "withdrawal",
    "segment_surrender": "withdrawal",
    "payout": "withdrawal",
    "ufpls_payment": "pension_access",
    "claim_payment": "death_claim",
    "premium": "top_up",
    "contribution": "top_up",
    "transfer_in": "top_up",
}


def level_for_role(role: str) -> Optional[str]:
    """The approval level a session role holds, or ``None`` if it holds none."""
    return _ROLE_LEVELS.get(role)


def transaction_for(kind: str, product: str) -> str:
    """The matrix row a ledger ``kind`` falls under, for this product."""
    transaction = _KIND_TRANSACTIONS.get(kind)
    if transaction is None:
        raise ValueError(f"no authority band maps the movement kind {kind!r}")
    # Money out of a pension is pension access, whatever the kind is called.
    if product == "retirement_account" and transaction == "withdrawal":
        return "pension_access"
    return transaction


def band_for(transaction: str, amount_pence: int) -> Band:
    """The band this amount falls into. An unmapped transaction raises.

    Refusing rather than defaulting is the point: a movement with no band is
    not a movement anyone may wave through.
    """
    candidates = [b for b in MATRIX if b.transaction == transaction]
    if not candidates:
        raise ValueError(f"no authority band for transaction {transaction!r}")
    for band in candidates:
        if band.covers(amount_pence):
            return band
    return candidates[-1]


def may_approve(level_or_role: str, transaction: str, amount_pence: int) -> bool:
    """Whether this level (or session role) may approve this movement alone."""
    level = _ROLE_LEVELS.get(level_or_role, level_or_role)
    if level not in APPROVAL_LEVELS:
        return False
    band = band_for(transaction, amount_pence)
    return level == band.approver


def requires_second_approver(transaction: str, amount_pence: int) -> bool:
    """Whether a second, distinct approver is required (`05-OPS:14`)."""
    band = band_for(transaction, amount_pence)
    return band.dual and amount_pence > DUAL_AUTH_ABOVE_PENCE
