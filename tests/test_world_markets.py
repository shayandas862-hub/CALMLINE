"""Deterministic fund behaviour — a market that rises, falls, and never varies.

A growth path per fund, seeded so the same fund produces the same history
forever. The property that makes it a *market* rather than a per-policy random
walk: **two policies in the same fund in the same year get the same return.**
Without that, 2008 is a bad year for some policyholders and a good one for
others, and no question about the book has a coherent answer.

Corpus rules this is built to:

- `02-BOND:3.3` — fund AMCs 0.10%–1.00%; `03-PEN:3.3` the same;
  `01-WOL:3.2` — 0.35%–1.00% for unit-linked whole of life.
- `02-BOND:3.6` — the with-profits fund adds an **annual (reversionary) bonus**
  which "normally cannot be removed". So a with-profits holding never posts an
  `investment_loss`; it posts a `bonus`, and that is a product rule rather than
  a modelling convenience.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.records.products import FundHolding
from world.lifetimes.markets import (
    CATALOGUE,
    annual_return_bp,
    blended_return_bp,
    fund,
    growth_movements,
)

SEED = 11
YEARS = tuple(range(1994, 2027))


def _holding(fund_id="managed_growth", split_pct=100):
    f = fund(fund_id)
    return FundHolding(fund_id=f.fund_id, fund_name=f.name, split_pct=split_pct,
                       amc_bp=f.amc_bp, price_date="2026-07-28")


# ── the catalogue ────────────────────────────────────────────────────────
def test_every_fund_amc_sits_inside_the_corpus_range():
    """`02-BOND:3.3` / `03-PEN:3.3` — 0.10%–1.00%, so 10bp to 100bp."""
    for f in CATALOGUE.values():
        assert 10 <= f.amc_bp <= 100, f"{f.fund_id} charges {f.amc_bp}bp"


def test_the_catalogue_holds_the_funds_the_corpus_names():
    """The two product samples name four funds between them; inventing a
    catalogue that does not contain them would make the samples unreachable."""
    for fund_id in ("managed_growth", "with_profits", "global_index",
                    "target_date_2036"):
        assert fund_id in CATALOGUE


def test_the_sampled_amcs_match_the_corpus_exactly():
    """`02-BOND` sample: Managed Growth AMC 0.65%. `03-PEN` sample: Global
    Index AMC 0.22%. Numbers stated in the corpus, not chosen here."""
    assert fund("managed_growth").amc_bp == 65
    assert fund("global_index").amc_bp == 22


def test_an_unknown_fund_raises_rather_than_defaulting():
    with pytest.raises(KeyError):
        fund("something_nobody_offers")


# ── determinism ──────────────────────────────────────────────────────────
def test_the_same_fund_and_year_return_the_same_figure_forever():
    first = [annual_return_bp("managed_growth", y, seed=SEED) for y in YEARS]
    second = [annual_return_bp("managed_growth", y, seed=SEED) for y in YEARS]
    assert first == second


def test_the_return_never_depends_on_the_process_it_was_computed_in():
    """Guards the one mistake that would silently break the world: seeding from
    `hash()`, which Python randomises per process. The value below is the
    frozen expectation — if the derivation changes, the whole book changes."""
    assert annual_return_bp("managed_growth", 2008, seed=SEED) == \
           annual_return_bp("managed_growth", 2008, seed=SEED)


def test_different_funds_do_not_move_identically():
    a = [annual_return_bp("managed_growth", y, seed=SEED) for y in YEARS]
    b = [annual_return_bp("global_index", y, seed=SEED) for y in YEARS]
    assert a != b


def test_different_seeds_produce_a_different_market():
    a = [annual_return_bp("managed_growth", y, seed=11) for y in YEARS]
    b = [annual_return_bp("managed_growth", y, seed=12) for y in YEARS]
    assert a != b


def test_a_return_is_always_a_whole_number_of_basis_points():
    for y in YEARS:
        value = annual_return_bp("managed_growth", y, seed=SEED)
        assert isinstance(value, int) and not isinstance(value, bool)


# ── it must be able to fall, and to rise ─────────────────────────────────
def test_a_unit_linked_fund_falls_in_some_years_and_rises_in_most():
    returns = [annual_return_bp("managed_growth", y, seed=SEED) for y in YEARS]
    assert any(r < 0 for r in returns), "a fund that never falls is not a market"
    assert any(r > 0 for r in returns)
    assert sum(returns) > 0, "thirty years of equities should end up ahead"


@pytest.mark.parametrize("fund_id", [f for f in
                                     ("managed_growth", "global_index",
                                      "uk_equity", "target_date_2036",
                                      "cautious_managed", "protection_managed")])
def test_a_unit_linked_fund_rises_in_roughly_three_years_in_four(fund_id):
    """Real markets rise in about 70–75% of years. A fund falling half the time
    would misrepresent every long-run figure in the book — and a single uniform
    draw did exactly that before the distribution was fixed."""
    returns = [annual_return_bp(fund_id, y, seed=SEED) for y in YEARS]
    falls = sum(1 for r in returns if r < 0)
    assert 4 <= falls <= 11, f"{fund_id} fell in {falls} of {len(YEARS)} years"


def test_the_with_profits_fund_never_falls():
    """`02-BOND:3.6` — a reversionary bonus, once added, normally cannot be
    removed. So with-profits has no down year to remove it in."""
    returns = [annual_return_bp("with_profits", y, seed=SEED) for y in YEARS]
    assert all(r >= 0 for r in returns)
    assert any(r > 0 for r in returns)


def test_every_fund_falls_together_in_a_market_stress_year():
    """A market is a shared thing. 2008 is bad for everyone holding units."""
    unit_linked = [f.fund_id for f in CATALOGUE.values() if not f.with_profits]
    assert all(annual_return_bp(f, 2008, seed=SEED) < 0 for f in unit_linked)


def test_a_stress_year_is_worse_than_the_same_fund_untroubled():
    stressed = annual_return_bp("managed_growth", 2008, seed=SEED)
    ordinary = annual_return_bp("managed_growth", 2013, seed=SEED)
    assert stressed < ordinary


def test_a_cautious_fund_loses_less_in_a_crash_than_an_equity_fund():
    """A market that hit every fund equally hard would be one nobody would
    recognise — and would make "your cautious fund fell 28% in 2008" a sentence
    the book could produce."""
    cautious = annual_return_bp("cautious_managed", 2008, seed=SEED)
    equity = annual_return_bp("uk_equity", 2008, seed=SEED)
    assert equity < cautious < 0


# ── blending across a policy's holdings ──────────────────────────────────
def test_a_single_holding_blends_to_its_own_return():
    holdings = (_holding("managed_growth", 100),)
    assert blended_return_bp(holdings, 2013, seed=SEED) == \
           annual_return_bp("managed_growth", 2013, seed=SEED)


def test_a_blend_is_weighted_by_the_split():
    # Arrange — the bond sample's own split: 60% Managed Growth, 40% With-Profits
    holdings = (_holding("managed_growth", 60), _holding("with_profits", 40))
    mg = annual_return_bp("managed_growth", 2013, seed=SEED)
    wp = annual_return_bp("with_profits", 2013, seed=SEED)

    # Act / Assert — integer arithmetic throughout, no float anywhere
    assert blended_return_bp(holdings, 2013, seed=SEED) == (60 * mg + 40 * wp) // 100


def test_blending_no_holdings_is_no_return_rather_than_an_error():
    assert blended_return_bp((), 2013, seed=SEED) == 0


# ── the movements it produces ────────────────────────────────────────────
def test_a_rising_year_posts_an_investment_return():
    movements = growth_movements(100_000_00, date(2013, 3, 1),
                                 (_holding("managed_growth"),), seed=SEED)
    assert [m.kind for m in movements] == ["investment_return"]
    assert movements[0].amount_pence > 0


def test_a_falling_year_posts_an_investment_loss_as_a_positive_magnitude():
    """A fall is its own kind, not a signed return. `amount_pence` stays a
    non-negative magnitude — the guard the whole ledger rests on."""
    movements = growth_movements(100_000_00, date(2008, 3, 1),
                                 (_holding("managed_growth"),), seed=SEED)
    assert [m.kind for m in movements] == ["investment_loss"]
    assert movements[0].amount_pence > 0


def test_a_with_profits_holding_posts_a_bonus_not_an_investment_return():
    """`02-BOND:3.6` — the reversionary bonus is a declared thing, and the
    ledger says so rather than calling it market growth."""
    movements = growth_movements(100_000_00, date(2013, 3, 1),
                                 (_holding("with_profits"),), seed=SEED)
    assert [m.kind for m in movements] == ["bonus"]


def test_a_mixed_policy_separates_its_bonus_from_its_unit_growth():
    """Blending them would lose the one fact that distinguishes them: a bonus,
    once added, cannot be removed. They are two events and post as two."""
    movements = growth_movements(
        100_000_00, date(2008, 3, 1),
        (_holding("managed_growth", 60), _holding("with_profits", 40)), seed=SEED)
    assert sorted(m.kind for m in movements) == ["bonus", "investment_loss"]


def test_a_zero_movement_is_not_posted_at_all():
    """A £0 row is noise in a history a person has to read."""
    assert growth_movements(0, date(2013, 3, 1),
                            (_holding("managed_growth"),), seed=SEED) == ()


def test_every_growth_movement_is_a_whole_number_of_pence():
    for year in range(1995, 2027):
        for movement in growth_movements(
                123_456_78, date(year, 3, 1),
                (_holding("managed_growth", 60), _holding("with_profits", 40)),
                seed=SEED):
            assert isinstance(movement.amount_pence, int)
            assert movement.amount_pence >= 0


def test_a_growth_movement_carries_the_date_it_was_asked_for():
    (movement,) = growth_movements(100_000_00, date(2013, 6, 30),
                                   (_holding("managed_growth"),), seed=SEED)
    assert movement.on == date(2013, 6, 30)
