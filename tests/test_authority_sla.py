"""v4 phase 2 · task 5 — service levels, as data with their sources.

The SLA table was three numbers inlined in the console. It is now a data
literal carrying, for every entry, the KB chunk that states it — so a handler
asking "why five days?" gets a citation rather than a shrug (AD-CL-028).

The full authority matrix lands in phase 3; this is the service-level half.
"""

import pytest

from src.authority.sla import (
    PRIORITY_SLA_HOURS,
    SLA_TABLE,
    business_days_for,
    sla_due,
    sla_hours_for_priority,
)


# ── the KB's own table ───────────────────────────────────────────────────
def test_every_entry_names_the_chunk_that_states_it():
    assert SLA_TABLE
    for entry in SLA_TABLE.values():
        assert entry.source_chunk_id, f"{entry.transaction} has no source"
        assert ":" in entry.source_chunk_id      # doc:sec, the chunk_id grammar


def test_the_table_covers_all_three_products():
    docs = {entry.source_chunk_id.split(":")[0] for entry in SLA_TABLE.values()}
    assert {"01-WOL", "02-BOND", "03-PEN"} <= docs


def test_a_bond_partial_withdrawal_takes_five_business_days():
    # `02-BOND:II.14` — "Partial withdrawal / full surrender | 5 / 10 business days"
    assert business_days_for("horizon_bond", "partial_withdrawal") == 5
    assert business_days_for("horizon_bond", "full_surrender") == 10


def test_a_bank_change_is_two_business_days_on_every_product():
    for product in ("lifelong_protection", "horizon_bond", "retirement_account"):
        assert business_days_for(product, "bank_change") == 2


def test_an_address_change_is_same_day():
    assert business_days_for("lifelong_protection", "address_change") == 0


def test_an_unknown_transaction_raises_rather_than_defaulting():
    # A silent default would invent a service promise the KB never made.
    with pytest.raises(KeyError):
        business_days_for("horizon_bond", "teleport_the_money")


def test_an_unknown_product_raises():
    with pytest.raises(KeyError):
        business_days_for("endowment", "bank_change")


# ── the priority fallback the raise path uses ────────────────────────────
def test_priority_hours_are_marked_as_a_repo_convention():
    # These are not in the KB — the console needed a due time before the
    # transaction type was known. Phase 3's matrix replaces them.
    assert set(PRIORITY_SLA_HOURS) == {"high", "medium", "low"}
    assert PRIORITY_SLA_HOURS["high"] < PRIORITY_SLA_HOURS["low"]


def test_an_unknown_priority_falls_back_to_the_medium_promise():
    assert sla_hours_for_priority("whatever") == PRIORITY_SLA_HOURS["medium"]


# ── the due time is computed from an injected now ────────────────────────
def test_sla_due_is_measured_from_the_injected_now():
    assert sla_due("2026-07-13T09:00:00", "high") == "2026-07-13T13:00:00"
    assert sla_due("2026-07-13T09:00:00", "medium") == "2026-07-14T09:00:00"


def test_sla_due_accepts_an_explicit_hour_offset():
    # The demo needs an already-overdue case; negative hours are legitimate.
    assert sla_due("2026-07-13T09:00:00", "medium", hours=-2) == "2026-07-13T07:00:00"
