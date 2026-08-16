"""The pension's benefit routes, and the trigger that can never be untriggered.

Money leaves a Retirement Account **only** through a route a pension actually
pays out through. A plain withdrawal is not among them, and that is the whole
point of `03-PEN`.

`03-PEN:4.3` is the trap this task exists to avoid:

> Once **taxable** pension income is flexibly accessed (FAD income or any
> UFPLS), future DC contributions are capped at **£10,000/yr**, with **no
> carry-forward**. Taking **only** PCLS with no taxable income does **not**
> trigger it; nor do **small-pot lump sums** (§9.5).

Four ways to be internally consistent and externally false:

1. **Drawdown always triggers.** It does not. `03-PEN:9.2` — the *first taxable
   income payment* triggers it. Designating funds into drawdown and taking only
   tax-free cash does not.
2. **PCLS triggers.** `03-PEN:9.1` says the opposite, explicitly.
3. **Small pots trigger.** `03-PEN:9.5` says they do not, and do not use the LSA.
4. **Buying an annuity triggers.** It is not in `03-PEN:4.3`'s list.

🔴 **A place the rulebook and the shipped code disagree.** `products.py:28` lists
`trivial_commutation` in `RA_BENEFIT_ROUTES`, but `03-PEN:9.5` says trivial
commutation "applies to **defined-benefit** rights (and some in-payment
benefits), **not to uncrystallised DC pots**". A Retirement Account is a personal
pension — a DC pot — so it cannot pay out that way. The shipped constant is **not
changed**: it is v4 code with its own tests, and this version promises to change
no running behaviour. The world simply never generates one, asserted below.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.records.products import RA_BENEFIT_ROUTES
from world.lifetimes.pension.benefits import (
    LUMP_SUM_ALLOWANCE_PENCE,
    MPAA_ANNUAL_CAP_PENCE,
    PATHWAYS,
    WORLD_BENEFIT_ROUTES,
    minimum_pension_age,
    movement_kind_for,
    old_enough_for_benefits,
    pcls_pence,
    triggers_mpaa,
    ufpls_split,
)


# ── the corpus figures ───────────────────────────────────────────────────
def test_the_mpaa_cap_is_the_corpus_ten_thousand():
    """`03-PEN:4.3` and `05-OPS:10`."""
    assert MPAA_ANNUAL_CAP_PENCE == 10_000_00


def test_the_lump_sum_allowance_is_the_corpus_figure():
    """`03-PEN:9.1` — £268,275 for 2025/26."""
    assert LUMP_SUM_ALLOWANCE_PENCE == 268_275_00


def test_the_four_investment_pathways_are_the_corpus_four():
    """`03-PEN:9.2`, COBS 19.10 — non-advised members entering drawdown must be
    offered four ready-made options."""
    assert sorted(PATHWAYS) == [1, 2, 3, 4]


# ── minimum pension age ──────────────────────────────────────────────────
def test_the_minimum_pension_age_is_fifty_five_throughout_the_worlds_life():
    """`03-PEN:8` — 55, rising to 57 on 6 April 2028. The world's birth date is
    2026-07-28, so every benefit in the book is taken under the age-55 rule."""
    assert minimum_pension_age(date(2026, 7, 28)) == 55
    assert minimum_pension_age(date(1994, 1, 1)) == 55


def test_the_rise_to_fifty_seven_is_dated_rather_than_ignored():
    """It is legislated and real, even though nothing in the book reaches it."""
    assert minimum_pension_age(date(2028, 4, 5)) == 55
    assert minimum_pension_age(date(2028, 4, 6)) == 57


def test_a_member_under_the_minimum_age_cannot_take_benefits():
    """Inside the world's own life, where the threshold is 55."""
    born = date(1965, 6, 1)
    assert not old_enough_for_benefits(born, date(2020, 5, 31))
    assert old_enough_for_benefits(born, date(2020, 6, 1))


def test_the_threshold_that_applies_is_the_one_in_force_on_the_day():
    """A member who is 55 in 2035 is *not* old enough — by then the minimum has
    risen to 57. Reading the age off a constant instead of off the date would
    quietly let benefits out two years early the moment the world is extended."""
    born = date(1980, 6, 1)
    assert not old_enough_for_benefits(born, date(2035, 6, 1))
    assert old_enough_for_benefits(born, date(2037, 6, 1))


# ── what triggers the MPAA, and what does not ────────────────────────────
def test_any_ufpls_triggers_the_mpaa_on_the_first_payment():
    """`03-PEN:9.3` — "triggers the MPAA on the first payment"."""
    assert triggers_mpaa("ufpls")
    assert triggers_mpaa("ufpls", taxable_income_taken=False)


def test_drawdown_triggers_only_when_taxable_income_is_actually_taken():
    """`03-PEN:9.2` — the *first taxable income payment* triggers it. Entering
    drawdown and taking only tax-free cash does not."""
    assert triggers_mpaa("drawdown", taxable_income_taken=True)
    assert not triggers_mpaa("drawdown", taxable_income_taken=False)


def test_taking_only_pcls_never_triggers_the_mpaa():
    """`03-PEN:9.1` and `03-PEN:4.3`, both explicit."""
    assert not triggers_mpaa("pcls")
    assert not triggers_mpaa("pcls", taxable_income_taken=True)


def test_a_small_pot_lump_sum_never_triggers_the_mpaa():
    """`03-PEN:9.5` — "does not trigger the MPAA or use LSA"."""
    assert not triggers_mpaa("small_pot")


def test_buying_an_annuity_does_not_trigger_the_mpaa():
    """`03-PEN:4.3` names FAD income and UFPLS. An annuity is neither."""
    assert not triggers_mpaa("annuity")


def test_an_unknown_route_is_refused_rather_than_assumed_harmless():
    with pytest.raises(ValueError):
        triggers_mpaa("cash_in")


# ── the routes themselves ────────────────────────────────────────────────
def test_a_plain_withdrawal_is_not_a_benefit_route():
    """The refusal the whole product exists to make."""
    assert "withdrawal" not in WORLD_BENEFIT_ROUTES
    with pytest.raises(ValueError):
        movement_kind_for("withdrawal")


def test_the_world_never_uses_trivial_commutation_on_a_pension():
    """`03-PEN:9.5` — trivial commutation is a defined-benefit mechanic and does
    not apply to uncrystallised DC pots. `products.py` lists it among
    `RA_BENEFIT_ROUTES`; that shipped constant is left alone and the world
    simply never generates one."""
    assert "trivial_commutation" in RA_BENEFIT_ROUTES
    assert "trivial_commutation" not in WORLD_BENEFIT_ROUTES


def test_every_route_the_world_uses_is_one_the_shipped_rulebook_permits():
    """The world may use fewer routes than the code allows. It must never use
    one the code would refuse."""
    assert WORLD_BENEFIT_ROUTES <= RA_BENEFIT_ROUTES


def test_a_ufpls_posts_as_its_own_movement_kind():
    assert movement_kind_for("ufpls") == "ufpls_payment"


def test_every_other_route_posts_as_a_payout_never_a_withdrawal():
    for route in WORLD_BENEFIT_ROUTES - {"ufpls"}:
        assert movement_kind_for(route) == "payout"


# ── what each route pays ─────────────────────────────────────────────────
def test_pcls_is_a_quarter_of_what_is_crystallised():
    """`03-PEN:9.1` — "Normally 25% of the amount crystallised"."""
    assert pcls_pence(200_000_00) == 50_000_00


def test_pcls_is_capped_by_the_lump_sum_allowance():
    """A £2,000,000 crystallisation would give £500,000 at 25%; the LSA stops
    it at £268,275."""
    assert pcls_pence(2_000_000_00) == LUMP_SUM_ALLOWANCE_PENCE


def test_pcls_already_used_reduces_what_is_left():
    assert pcls_pence(2_000_000_00, lsa_used_pence=200_000_00) == \
        LUMP_SUM_ALLOWANCE_PENCE - 200_000_00


def test_pcls_never_goes_negative_once_the_allowance_is_spent():
    assert pcls_pence(200_000_00, lsa_used_pence=LUMP_SUM_ALLOWANCE_PENCE) == 0


def test_a_ufpls_is_a_quarter_tax_free_and_the_rest_taxed():
    """`03-PEN:9.3` — 25% tax-free / 75% taxed at marginal rate."""
    tax_free, taxable = ufpls_split(20_000_00)
    assert tax_free == 5_000_00
    assert taxable == 15_000_00


def test_a_ufpls_split_always_adds_back_to_the_whole_payment():
    """No penny may be lost between the two halves."""
    for amount in (1, 7, 99, 12_345_67, 999_999_99):
        tax_free, taxable = ufpls_split(amount)
        assert tax_free + taxable == amount
        assert isinstance(tax_free, int) and isinstance(taxable, int)


def test_every_pcls_figure_is_whole_pence():
    for amount in (1, 33, 99_999_99, 123_456_789):
        assert isinstance(pcls_pence(amount), int)
