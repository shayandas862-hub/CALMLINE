"""v4 phase 3 · task 4 — the compiled authority matrix.

The bands are held as data literals, each carrying the chunk that states it
(AD-CL-028). They are genuinely **per product**: the withdrawal ladder is the
bond's (`02-BOND:II.13`), pension access is the pension's (`03-PEN:II.13`) and
the death-claim ladder is whole-of-life's (`01-WOL:II.13`), with the
cross-product table at `05-OPS:14`. The phase-3 card cited "05-OPS II.13/§14",
which is one section that does not exist and one that does — D-CL-045.

The KB states five approval levels; this console has three session roles, and
`ops` is read-only. So exactly one role approves anything, and it approves the
bottom band only. Everything above it is refused for want of a level that has
no session — which is the honest outcome, and the one worth demonstrating.
"""

import pytest

from src.authority.matrix import (
    APPROVAL_LEVELS,
    MATRIX,
    band_for,
    level_for_role,
    may_approve,
    requires_second_approver,
    transaction_for,
)
from src.records.models import gbp


# ── the literals carry their sources ─────────────────────────────────────
def test_every_band_names_the_chunk_that_states_it():
    assert MATRIX, "the matrix must not be empty"
    for band in MATRIX:
        assert band.source, f"{band.transaction} band has no source chunk id"
        assert ":" in band.source, f"{band.source!r} is not a chunk id"


def test_the_sources_are_the_per_product_tables_and_the_cross_product_one():
    sources = {band.source for band in MATRIX}
    assert "05-OPS:14" in sources
    assert "02-BOND:II.13" in sources
    assert "03-PEN:II.13" in sources
    assert "01-WOL:II.13" in sources
    # The section the spec invented is not among them.
    assert "05-OPS:II.13" not in sources


def test_the_levels_run_from_front_office_to_head_of_claims():
    assert APPROVAL_LEVELS == (
        "front_office", "back_office", "team_manager", "senior_manager",
        "head_of_claims")


# ── roles map to levels; ops approves nothing ────────────────────────────
def test_a_back_office_session_is_the_back_office_level():
    assert level_for_role("back_office") == "back_office"


def test_a_front_office_session_is_the_front_office_level():
    assert level_for_role("front_office") == "front_office"


def test_an_ops_session_has_no_approval_level_at_all():
    # CONTEXT.md: ops is oversight, strictly read-only.
    assert level_for_role("ops") is None


# ── the withdrawal ladder (02-BOND:II.13) ────────────────────────────────
def test_back_office_may_approve_a_withdrawal_at_the_bottom_band():
    assert may_approve("back_office", "withdrawal", gbp(25_000)) is True


def test_back_office_may_not_approve_a_withdrawal_above_its_band():
    assert may_approve("back_office", "withdrawal", gbp(25_001)) is False


def test_the_middle_withdrawal_band_needs_a_team_manager():
    assert band_for("withdrawal", gbp(60_000)).approver == "team_manager"


def test_the_top_withdrawal_band_needs_a_senior_manager():
    assert band_for("withdrawal", gbp(150_000)).approver == "senior_manager"


def test_a_front_office_session_can_never_approve_money():
    for amount in (gbp(1), gbp(25_000), gbp(500_000)):
        assert may_approve("front_office", "withdrawal", amount) is False


def test_an_ops_session_can_never_approve_money():
    assert may_approve("ops", "withdrawal", gbp(1)) is False


# ── dual authorisation above £250,000 (05-OPS:14) ────────────────────────
def test_a_withdrawal_over_two_hundred_and_fifty_thousand_needs_two_approvers():
    assert requires_second_approver("withdrawal", gbp(250_001)) is True


def test_a_withdrawal_at_the_threshold_does_not():
    # "above £250,000" — the threshold itself is not above it.
    assert requires_second_approver("withdrawal", gbp(250_000)) is False


def test_pension_access_over_the_threshold_needs_two_approvers():
    assert requires_second_approver("pension_access", gbp(250_001)) is True


def test_a_small_withdrawal_needs_only_one():
    assert requires_second_approver("withdrawal", gbp(5_000)) is False


# ── the other ladders ────────────────────────────────────────────────────
def test_pension_access_sits_in_the_back_office_band_up_to_fifty_thousand():
    assert may_approve("back_office", "pension_access", gbp(50_000)) is True
    assert may_approve("back_office", "pension_access", gbp(50_001)) is False


def test_a_death_claim_up_to_fifty_thousand_is_back_office():
    assert may_approve("back_office", "death_claim", gbp(50_000)) is True


def test_a_death_claim_over_a_million_goes_to_the_head_of_claims():
    band = band_for("death_claim", gbp(1_000_001))
    assert band.approver == "head_of_claims"
    assert requires_second_approver("death_claim", gbp(1_000_001)) is True


def test_a_top_up_over_twenty_five_thousand_leaves_the_back_office_band():
    assert may_approve("back_office", "top_up", gbp(25_000)) is True
    assert may_approve("back_office", "top_up", gbp(25_001)) is False


# ── mapping a movement onto a matrix row ─────────────────────────────────
def test_a_bond_withdrawal_is_a_withdrawal():
    assert transaction_for("withdrawal", "horizon_bond") == "withdrawal"


def test_taking_money_from_a_pension_is_pension_access_not_a_withdrawal():
    # The ladders differ — £50k is inside the band for one and outside for the
    # other — so reading the product is not cosmetic.
    assert transaction_for("withdrawal", "retirement_account") == "pension_access"
    assert transaction_for("ufpls_payment", "retirement_account") == "pension_access"


def test_a_claim_payment_is_a_death_claim():
    assert transaction_for("claim_payment", "lifelong_protection") == "death_claim"


def test_money_in_is_a_top_up():
    for kind in ("premium", "contribution", "transfer_in"):
        assert transaction_for(kind, "horizon_bond") == "top_up"


def test_an_unmapped_transaction_type_is_refused_rather_than_defaulted():
    # A movement with no band is not a movement anyone may wave through.
    with pytest.raises(ValueError):
        band_for("something_new", gbp(1))
