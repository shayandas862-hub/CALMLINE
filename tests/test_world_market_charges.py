"""Charges — an exact integer number of pence, never a rounding of a float.

The basis points are already on the fund record (`FundHolding.amc_bp`, 0.65% →
65), which is why they are there: a percentage held as a float would make every
charge in the book a rounding, and thirty years of roundings do not reconcile.

Corpus rules this is built to:

- `02-BOND:3.3` — "Product/administration 0.30% p.a.; fund AMCs 0.10%–1.00%".
- `03-PEN:3.3` — "Annual product charge 0.30% p.a.; fund AMCs 0.10%–1.00%".
- `01-WOL:3.2` — "Monthly policy fee £4.50. Unit-linked: fund AMCs 0.35%–1.00%".

The corpus states charge *rates* and, for whole of life alone, a *monthly*
deduction. It is silent on deduction frequency for the bond and the pension.
Both are resolved by a recorded decision: the charge is **calculated** as the
corpus states it and **posted** as an annual summary, the same treatment
premiums already get.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.records.products import FundHolding
from world.lifetimes.markets import (
    PRODUCT_CHARGE_BP,
    WOL_MONTHLY_POLICY_FEE_PENCE,
    annual_charge_pence,
    charge_movements,
    charge_pence,
    fund,
)


def _holding(fund_id="managed_growth", split_pct=100):
    f = fund(fund_id)
    return FundHolding(fund_id=f.fund_id, fund_name=f.name, split_pct=split_pct,
                       amc_bp=f.amc_bp, price_date="2026-07-28")


# ── the corpus figures, held as integers ─────────────────────────────────
def test_the_product_charge_is_the_corpus_thirty_basis_points():
    """0.30% p.a., stated identically in `02-BOND:3.3` and `03-PEN:3.3`."""
    assert PRODUCT_CHARGE_BP == 30


def test_the_whole_of_life_policy_fee_is_the_corpus_four_pounds_fifty():
    """`01-WOL:3.2` — £4.50 a month, held in pence so it never rounds."""
    assert WOL_MONTHLY_POLICY_FEE_PENCE == 450


# ── exactness ────────────────────────────────────────────────────────────
def test_a_charge_is_an_exact_integer_number_of_pence():
    # Arrange / Act — 0.65% of £100,000
    charged = charge_pence(100_000_00, bp=65)

    # Assert — £650.00 exactly, computed by integer arithmetic
    assert charged == 650_00
    assert isinstance(charged, int)


@pytest.mark.parametrize("value_pence", [1, 7, 99, 12_345_67, 999_999_99,
                                         123_456_789, 1])
@pytest.mark.parametrize("bp", [10, 22, 30, 65, 75, 100])
def test_no_charge_anywhere_introduces_a_fractional_penny(value_pence, bp):
    charged = charge_pence(value_pence, bp=bp)
    assert isinstance(charged, int)
    assert charged >= 0


def test_a_charge_rounds_down_rather_than_up():
    """Where the exact figure falls between pennies the customer keeps the
    fraction. A deliberate direction, not an artefact of integer division:
    an insurer that rounds its own charges up on every policy every year for
    thirty years has helped itself, a penny at a time."""
    # 0.65% of £1.00 is 0.65p — not a whole penny
    assert charge_pence(100, bp=65) == 0


def test_a_charge_on_nothing_is_nothing():
    assert charge_pence(0, bp=65) == 0


def test_a_charge_never_exceeds_the_value_it_is_taken_from():
    for value in (1, 100, 100_000_00):
        assert charge_pence(value, bp=100) <= value


# ── charges across a policy's holdings ───────────────────────────────────
def test_each_fund_charges_its_own_slice():
    # Arrange — the bond sample: 60% Managed Growth (65bp), 40% With-Profits
    holdings = (_holding("managed_growth", 60), _holding("with_profits", 40))
    value = 151_240_00

    # Act
    charged = annual_charge_pence(value, holdings)

    # Assert — each slice charged at its own rate, plus the product charge
    expected = (
        charge_pence(value * 60 // 100, bp=65)
        + charge_pence(value * 40 // 100, bp=fund("with_profits").amc_bp)
        + charge_pence(value, bp=PRODUCT_CHARGE_BP)
    )
    assert charged == expected


def test_the_product_charge_applies_even_with_no_fund_holdings():
    """`02-BOND:3.3` charges product/administration on the bond, not on a fund."""
    assert annual_charge_pence(100_000_00, ()) == charge_pence(100_000_00, bp=30)


def test_the_annual_charge_is_a_whole_number_of_pence_at_every_value():
    holdings = (_holding("managed_growth", 60), _holding("with_profits", 40))
    for value in range(0, 1_000_000, 7_919):
        assert isinstance(annual_charge_pence(value, holdings), int)


def test_the_annual_charge_never_exceeds_the_value():
    """A charge that could overdraw a policy would be refused by the ledger and
    stop the whole book. It cannot: the rates sum well under 100%."""
    for value in (1, 99, 100_00, 500_000_00):
        holdings = (_holding("managed_growth", 100),)
        assert annual_charge_pence(value, holdings) <= value


# ── the movements it produces ────────────────────────────────────────────
def test_a_charge_posts_as_a_single_charge_movement():
    (movement,) = charge_movements(100_000_00, date(2020, 3, 1),
                                   (_holding("managed_growth"),))
    assert movement.kind == "charge"
    assert movement.on == date(2020, 3, 1)
    assert movement.amount_pence > 0


def test_a_charge_movement_says_what_it_was_for():
    (movement,) = charge_movements(100_000_00, date(2020, 3, 1),
                                   (_holding("managed_growth"),))
    assert movement.reason, "a charge with no reason is unexplainable to a caller"


def test_no_charge_movement_is_posted_when_there_is_nothing_to_charge():
    assert charge_movements(0, date(2020, 3, 1),
                            (_holding("managed_growth"),)) == ()


def test_the_whole_of_life_policy_fee_can_be_added_to_the_year():
    """`01-WOL:3.2` — twelve monthly fees, posted as one annual line."""
    (movement,) = charge_movements(
        100_000_00, date(2020, 3, 1), (_holding("managed_growth"),),
        policy_fee_months=12)
    plain = charge_movements(100_000_00, date(2020, 3, 1),
                             (_holding("managed_growth"),))[0]
    assert movement.amount_pence == plain.amount_pence + 12 * 450
