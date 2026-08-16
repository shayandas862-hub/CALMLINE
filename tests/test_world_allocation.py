"""Deciding what the two hundred policies are — every partition, met exactly.

A book generated without a plan is two hundred near-copies. The point of the
world is that it can be *asked things*, including things it must refuse, so the
shape of it is designed before a single policy is played.

Split from `test_world_book.py`, which proves the finished book reconciles.
This proves the plan it was built to.
"""

from __future__ import annotations

from datetime import date

import pytest

from world import WORLD_BIRTH_DATE
from world.lifetimes.allocation import (
    BAND_COUNTS,
    BAND_TARGET_RANGES,
    HISTORY_SPANS,
    PRODUCT_STATUS_COUNTS,
    allocate_book,
    band_of,
)

SEED = 11


def _specs():
    return allocate_book(seed=SEED, born=WORLD_BIRTH_DATE)


def test_the_book_is_two_hundred_policies():
    assert len(_specs()) == 200


def test_the_product_and_status_partition_is_met_exactly():
    """§2 — 70 + 65 + 65, and every status cell.

    The empty cells are deliberate: a bond is a single-premium contract and
    cannot lapse or be made paid up; a pension is not surrendered, it pays out
    through a benefit route.
    """
    seen: dict[tuple[str, str], int] = {}
    for spec in _specs():
        key = (spec.product, spec.status)
        seen[key] = seen.get(key, 0) + 1
    assert seen == PRODUCT_STATUS_COUNTS


def test_fifty_policies_are_not_in_force():
    """§2 — which is what makes "policy in force", the first row of the
    money-out checklist, a control that can actually fail."""
    assert sum(1 for s in _specs() if s.status != "in_force") == 50


def test_the_lives_partition_is_met_exactly():
    """§3 — 162 single, 38 joint last survivor."""
    specs = _specs()
    joint = [s for s in specs if s.lives_basis == "joint_last_survivor"]
    assert len(joint) == 38
    assert len(specs) - len(joint) == 162


def test_every_joint_policy_names_a_second_life_who_holds_nothing():
    """§1/§3 — the 38 second lives are the 38 people who hold no policy of
    their own. That is what makes the arithmetic close at 200 people."""
    specs = _specs()
    holders = {s.holder_party_id for s in specs}
    seconds = {s.second_life_party_id for s in specs
               if s.lives_basis == "joint_last_survivor"}
    assert len(seconds) == 38
    assert not (seconds & holders)


def test_a_single_life_policy_names_no_second_life():
    for spec in _specs():
        if spec.lives_basis == "single":
            assert spec.second_life_party_id is None


def test_the_holder_mapping_is_met_exactly():
    """§1 — 132 people hold one policy, 22 hold two, 8 hold three."""
    held: dict[str, int] = {}
    for spec in _specs():
        held[spec.holder_party_id] = held.get(spec.holder_party_id, 0) + 1
    counts = sorted(held.values())
    assert counts.count(1) == 132
    assert counts.count(2) == 22
    assert counts.count(3) == 8
    assert len(held) == 162
    assert sum(held.values()) == 200


def test_the_cover_basis_partition_is_met_exactly():
    """§9 — 22 guaranteed, 20 reviewable without units, 28 unit-linked. Forty-
    two Lifelong Protection policies cannot pay cash out at all."""
    specs = [s for s in _specs() if s.product == "lifelong_protection"]
    unit_linked = [s for s in specs if "unit_linked" in s.cover_basis]
    guaranteed = [s for s in specs if s.cover_basis == ("guaranteed",)]
    assert len(unit_linked) == 28
    assert len(guaranteed) == 22
    assert len(specs) - len(unit_linked) - len(guaranteed) == 20


def test_every_policy_that_was_paid_up_or_surrendered_had_a_fund_to_do_it_with():
    """`01-WOL:3.3` — a protection-only plan has no surrender value and cannot
    be made paid up. Allocating one would raise at build time, so the nine have
    to be drawn from the twenty-eight unit-linked."""
    for spec in _specs():
        if spec.product == "lifelong_protection" and spec.status in {
                "paid_up", "surrendered"}:
            assert "unit_linked" in spec.cover_basis


def test_only_products_that_can_hold_a_status_are_given_it():
    for spec in _specs():
        if spec.product == "horizon_bond":
            assert spec.status not in {"lapsed", "paid_up"}
        if spec.product == "retirement_account":
            assert spec.status != "surrendered"


def test_every_policy_starts_inside_its_products_history_span():
    """§10 — the product decides how far back the book goes, which is the
    PRD's own recommendation and the only one that survives the products."""
    for spec in _specs():
        earliest, latest = HISTORY_SPANS[spec.product]
        assert earliest <= spec.start.year <= latest


def test_the_oldest_policy_reaches_back_to_the_nineties():
    """Whole of life is a policy taken out at 35 and still running at 67."""
    assert min(s.start.year for s in _specs()) <= 1996


def test_no_policy_starts_after_the_worlds_birth_date():
    for spec in _specs():
        assert spec.start <= WORLD_BIRTH_DATE


def test_every_policy_number_matches_its_products_prefix():
    prefix = {"lifelong_protection": "LP", "horizon_bond": "HB",
              "retirement_account": "RA"}
    for spec in _specs():
        assert spec.policy_no[:2] == prefix[spec.product]


def test_no_two_policies_share_a_number():
    numbers = [s.policy_no for s in _specs()]
    assert len(set(numbers)) == len(numbers) == 200


def test_the_allocation_is_deterministic():
    assert _specs() == _specs()


# ── the value bands ──────────────────────────────────────────────────────
def test_the_band_counts_total_two_hundred():
    assert sum(BAND_COUNTS.values()) == 200


def test_band_of_puts_a_figure_in_the_right_band():
    assert band_of(0) == "under_25k"
    assert band_of(24_999_99) == "under_25k"
    assert band_of(25_000_00) == "25k_to_100k"
    assert band_of(99_999_99) == "25k_to_100k"
    assert band_of(100_000_00) == "100k_to_250k"
    assert band_of(249_999_99) == "100k_to_250k"
    assert band_of(250_000_00) == "over_250k"


def test_every_band_target_range_sits_inside_its_own_band():
    """A target that straddled a boundary would let the two-pass scaling land
    a policy in the band next door, and the partition would stop being met."""
    for band, (low, high) in BAND_TARGET_RANGES.items():
        assert band_of(low) == band
        assert band_of(high) == band
        assert low < high, "a range with no width is a single target again"


def test_the_band_partition_is_allocated_exactly():
    seen: dict[str, int] = {}
    for spec in _specs():
        seen[spec.band] = seen.get(spec.band, 0) + 1
    assert seen == BAND_COUNTS


def test_a_world_with_no_room_for_its_own_history_is_refused():
    with pytest.raises(ValueError):
        allocate_book(seed=SEED, born=date(1990, 1, 1))
