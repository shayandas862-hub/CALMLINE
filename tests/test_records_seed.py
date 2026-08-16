"""The seeded book ties out — anchors and synthetics together.

The detail of each half lives in `test_records_anchors.py` and
`test_synthetic_history.py`. This file asserts what the *whole* book must be
true of: it reconciles, it spans the directed age range, and it is the same
book every time it is built.
"""

from datetime import date

import pytest

from src.records.models import format_gbp, gbp
from src.records.seed import SPECIMEN_IDS, SEED_AS_AT, build_seed_book

ANCHOR_VALUES = {
    "LP-20419876": gbp(46_210),    # stated fund value
    "HB-40582213": gbp(151_240),   # stated current value
    "RA-77103428": gbp(212_400),   # stated fund value
}


@pytest.fixture(scope="module")
def book():
    return build_seed_book()


def test_the_book_holds_the_anchors_and_the_synthetic_holders(book):
    assert len(book.list_policies()) == 83
    assert len(book.list_parties()) == 83
    assert set(SPECIMEN_IDS) <= {p.policy_no for p in book.list_policies()}


def test_the_as_of_date_is_the_knowledge_base_date_not_the_clock():
    # A property of the corpus, so the book is identical whenever it is built.
    assert SEED_AS_AT == "2026-07-13"


def test_anchors_only_is_available_for_tests_that_want_just_the_kb(book):
    just_specimens = build_seed_book(with_synthetics=False)
    assert {p.policy_no for p in just_specimens.list_policies()} == set(SPECIMEN_IDS)


# ── the anchors still state what the KB states ───────────────────────────
def test_each_anchor_balance_matches_its_sample_record(book):
    for policy_no, expected in ANCHOR_VALUES.items():
        assert book.current_value(policy_no) == expected


def test_the_bond_value_renders_as_the_stated_figure(book):
    assert format_gbp(book.current_value("HB-40582213")) == "£151,240.00"


# ── the whole book reconciles ────────────────────────────────────────────
def test_every_ledger_reconciles_against_its_own_history(book):
    # The ops self-check, applied to all 83 — anchors and synthetics alike.
    for policy in book.list_policies():
        summed = sum(e.transaction.signed_pence for e in book.history(policy.policy_no))
        assert book.current_value(policy.policy_no) == summed


def test_no_policy_carries_a_negative_balance(book):
    assert all(book.current_value(p.policy_no) >= 0 for p in book.list_policies())


def test_every_policy_number_is_unique(book):
    numbers = [p.policy_no for p in book.list_policies()]
    assert len(numbers) == len(set(numbers))


def test_every_policy_has_a_party_behind_it(book):
    for policy in book.list_policies():
        assert book.get_party(policy.holder_party_id) is not None


# ── the directed age range, across the whole book ────────────────────────
def _age(policy) -> float:
    return (date.fromisoformat(SEED_AS_AT)
            - date.fromisoformat(policy.start_date)).days / 365.25


def test_the_synthetic_book_spans_the_directed_age_range(book):
    # D-CL-029 directs the range for the *generated* book. The three anchors
    # carry the KB's own dates instead — they state what the corpus states,
    # which is the whole point of parsing them (D-CL-028).
    synthetic = [p for p in book.list_policies() if p.policy_no not in SPECIMEN_IDS]
    ages = [_age(p) for p in synthetic]
    assert sum(1 for a in ages if a > 40) >= 3
    assert sum(1 for a in ages if 3 <= a <= 5) >= 3
    assert min(ages) >= 3.0
    assert max(ages) <= 60.0


def test_every_holder_in_the_book_was_an_adult_at_inception(book):
    for policy in book.list_policies():
        party = book.get_party(policy.holder_party_id)
        years = (date.fromisoformat(policy.start_date)
                 - date.fromisoformat(party.dob)).days / 365.25
        assert years >= 18.0, f"{policy.policy_no}: holder was {years:.1f}"


# ── determinism ──────────────────────────────────────────────────────────
def test_building_the_book_twice_gives_the_same_book():
    first, second = build_seed_book(), build_seed_book()
    assert ([p.policy_no for p in first.list_policies()]
            == [p.policy_no for p in second.list_policies()])
    for policy in first.list_policies():
        assert (first.current_value(policy.policy_no)
                == second.current_value(policy.policy_no))


# ── everything went through the real store API ───────────────────────────
def test_every_write_is_journalled_as_seed(book):
    assert all(e.source_ref == "seed" for e in book.changes.entries())
    assert len(book.changes.for_entity("policy", "HB-40582213")) > 1
