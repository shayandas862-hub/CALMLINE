"""Service levels, as data with their sources (AD-CL-028).

Every entry names the KB chunk that states it, so "why five business days?" is
answerable with a citation rather than an assurance. The table is a literal
rather than a retrieval call on purpose: an SLA is enforced by the console, and
a promise the system makes about its own turnaround should not depend on a
similarity search returning the right chunk.

The full authority matrix (`05-OPS:14`) lands in phase 3.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class ServiceLevel:
    """One promised turnaround, and the chunk that promises it."""

    product: str
    transaction: str
    business_days: int
    source_chunk_id: str
    note: str = ""


def _entries() -> "tuple[ServiceLevel, ...]":
    """The three product SLA tables (`II.14` in each), transcribed."""
    shared = (
        ("address_change", 0, "Same day; suppression within 24h"),
        ("name_change", 3, ""),
        ("bank_change", 2, "Plus a hold on the account"),
        ("expression_of_wish", 5, ""),
        ("dsar", 20, "One month, extendable to three"),
    )
    rows: list[ServiceLevel] = []
    for product, chunk_id, extra in (
        ("lifelong_protection", "01-WOL:II.14", (
            ("premium_change", 3, ""), ("indexation", 3, ""),
            ("trust_or_assignment", 10, ""), ("gio_increment", 5, ""),
            ("reinstatement", 5, ""), ("unit_linked_surrender", 5, ""))),
        ("horizon_bond", "02-BOND:II.14", (
            ("fund_switch", 2, "Placed within 2 business days"),
            ("withdrawal_instruction_change", 3, ""),
            ("trust_or_assignment", 10, ""),
            ("top_up", 3, "5–10 where enhanced due diligence applies"),
            ("partial_withdrawal", 5, ""), ("full_surrender", 10, ""))),
        ("retirement_account", "03-PEN:II.14", (
            ("contribution_change", 3, "Or the next collection cycle"),
            ("fund_switch", 2, "Placed within 2 business days"),
            ("target_retirement_age_change", 3, ""),
            ("transfer_in", 10, "Plus the ceding scheme's own time"),
            ("retirement_quote", 5, ""),
            ("pension_access_setup", 5, "5–10 business days"),
            ("top_up", 3, "5–10 where enhanced due diligence applies"))),
    ):
        for transaction, days, note in shared + extra:
            rows.append(ServiceLevel(product=product, transaction=transaction,
                                     business_days=days, source_chunk_id=chunk_id,
                                     note=note))
    return tuple(rows)


SLA_TABLE: "dict[tuple[str, str], ServiceLevel]" = {
    (entry.product, entry.transaction): entry for entry in _entries()
}

# Not from the KB. The console needs a due time at the moment a case is raised,
# before anyone has classified the transaction. Phase 3's matrix replaces this.
PRIORITY_SLA_HOURS = {"high": 4, "medium": 24, "low": 96}


def business_days_for(product: str, transaction: str) -> int:
    """The promised turnaround, in business days.

    Raises for an unknown product or transaction — defaulting would invent a
    service promise the knowledge base never made.
    """
    try:
        return SLA_TABLE[(product, transaction)].business_days
    except KeyError:
        raise KeyError(
            f"no stated SLA for {transaction!r} on {product!r}") from None


def source_for(product: str, transaction: str) -> str:
    """The chunk id that states this SLA."""
    return SLA_TABLE[(product, transaction)].source_chunk_id


def sla_hours_for_priority(priority: str) -> int:
    """Hours allowed for a case at ``priority`` (unknown → the medium promise)."""
    return PRIORITY_SLA_HOURS.get(priority, PRIORITY_SLA_HOURS["medium"])


def sla_due(now: str, priority: str, *, hours: "int | None" = None) -> str:
    """When a case raised at ``now`` falls due. Time is always injected."""
    offset = sla_hours_for_priority(priority) if hours is None else hours
    return (datetime.fromisoformat(now) + timedelta(hours=offset)).isoformat()
