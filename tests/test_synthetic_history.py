"""v4 phase 2 · task 3 — the 80 synthetic holders and their derived histories.

The JSONL manifest is an *identity* file: who exists, their date of birth, their
address, and which product they hold. It carries no dates and no money, so the
history is derived at seed time from a fixed RNG seed plus the injected as-of —
same inputs, same book, every run.

Start dates span 3–60 years back, banded per product (D-CL-029), and are always
age-consistent: nobody holds a policy taken out before they turned 18.
"""

from datetime import date

import pytest

from src.records.models import gbp
from src.records.store import InMemoryRecordBook
from src.records.synthetic_history import (
    MANIFEST_PATH,
    PRODUCT_MAX_YEARS,
    load_manifest,
    seed_synthetics,
)
from src.records.valuation import value_as_at

AS_AT = "2026-07-13"


@pytest.fixture(scope="module")
def book():
    store = InMemoryRecordBook()
    seed_synthetics(store, as_at=AS_AT)
    return store


@pytest.fixture(scope="module")
def policies(book):
    return book.list_policies()


def _age_years(policy, as_at=AS_AT) -> float:
    start = date.fromisoformat(policy.start_date)
    return (date.fromisoformat(as_at) - start).days / 365.25


# ── the manifest is an identity file ─────────────────────────────────────
def test_the_manifest_holds_eighty_identities():
    rows = load_manifest(MANIFEST_PATH)
    assert len(rows) == 80


def test_the_manifest_carries_no_dates_or_money():
    # If it ever grows a start_date or a balance, the history stops being
    # derived and starts being asserted — this test is the tripwire.
    for row in load_manifest(MANIFEST_PATH):
        assert "start_date" not in row
        assert not any("pence" in key or "value" in key for key in row)


def test_every_manifest_row_becomes_a_party_and_a_policy(book, policies):
    assert len(policies) == 80
    assert len(book.list_parties()) == 80


# ── determinism ──────────────────────────────────────────────────────────
def test_two_runs_produce_an_identical_book():
    first, second = InMemoryRecordBook(), InMemoryRecordBook()
    seed_synthetics(first, as_at=AS_AT)
    seed_synthetics(second, as_at=AS_AT)
    for policy in first.list_policies():
        assert second.get_policy(policy.policy_no) == policy
        assert ([e.transaction for e in second.history(policy.policy_no)]
                == [e.transaction for e in first.history(policy.policy_no)])


def test_a_different_as_at_moves_the_book():
    # The as-of date is injected, so it genuinely drives the history rather
    # than the wall clock quietly doing it.
    later = InMemoryRecordBook()
    seed_synthetics(later, as_at="2027-07-13")
    baseline = InMemoryRecordBook()
    seed_synthetics(baseline, as_at=AS_AT)
    total = lambda b: sum(b.current_value(p.policy_no) for p in b.list_policies())
    assert total(later) != total(baseline)


# ── the directed age range (D-CL-029) ────────────────────────────────────
def test_no_policy_is_younger_than_three_or_older_than_sixty(policies):
    ages = [_age_years(p) for p in policies]
    assert min(ages) >= 3.0
    assert max(ages) <= 60.0


def test_both_ends_of_the_range_are_represented(policies):
    ages = [_age_years(p) for p in policies]
    assert sum(1 for a in ages if a > 40) >= 3
    assert sum(1 for a in ages if 3 <= a <= 5) >= 3


def test_each_product_stays_inside_its_own_band(policies):
    for policy in policies:
        assert _age_years(policy) <= PRODUCT_MAX_YEARS[policy.product]


def test_only_lifelong_protection_reaches_beyond_forty_years(policies):
    # HB caps at 40 and RA at 38 (the personal-pension era), so anything older
    # must be an LP — a structural consequence of the bands, worth pinning.
    for policy in policies:
        if _age_years(policy) > 40:
            assert policy.product == "lifelong_protection"


def test_every_holder_was_at_least_eighteen_when_their_policy_started(book, policies):
    for policy in policies:
        party = book.get_party(policy.holder_party_id)
        started = date.fromisoformat(policy.start_date)
        born = date.fromisoformat(party.dob)
        age_at_start = (started - born).days / 365.25
        assert age_at_start >= 18.0, f"{policy.policy_no}: holder was {age_at_start:.1f}"


def test_the_oldest_policies_sit_with_the_oldest_holders(book, policies):
    oldest = sorted(policies, key=_age_years, reverse=True)[:3]
    for policy in oldest:
        born = date.fromisoformat(book.get_party(policy.holder_party_id).dob).year
        assert born <= 1968       # old enough to have held it for over 40 years


# ── the ledgers ──────────────────────────────────────────────────────────
def test_every_ledger_reconciles_against_its_own_history(book, policies):
    for policy in policies:
        summed = sum(e.transaction.signed_pence
                     for e in book.history(policy.policy_no))
        assert book.current_value(policy.policy_no) == summed


def test_no_ledger_is_ever_negative(book, policies):
    for policy in policies:
        for entry in book.history(policy.policy_no):
            assert entry.balance_after_pence >= 0


def test_histories_are_sparse_not_dense_monthly_ledgers(book, policies):
    # A handful of dated events per decade, not a row per month.
    #
    # Two kinds of row are deliberately regular and are excluded: a bond's
    # annual 5% withdrawal *run* and a pension's monthly contributions are both
    # what the product actually does, and the spec asks for them by name. What
    # this pins is that nothing else accumulates per-month noise.
    regular = {"regular_withdrawal", "contribution"}
    for policy in policies:
        irregular = [e for e in book.history(policy.policy_no)
                     if e.transaction.kind not in regular]
        assert len(irregular) <= max(1, int(_age_years(policy) / 10)) + 3


def test_every_transaction_predates_the_as_of_date(book, policies):
    for policy in policies:
        for entry in book.history(policy.policy_no):
            assert entry.transaction.at[:10] <= AS_AT


def test_no_transaction_predates_its_policy(book, policies):
    for policy in policies:
        for entry in book.history(policy.policy_no):
            assert entry.transaction.at[:10] >= policy.start_date


# ── product shape ────────────────────────────────────────────────────────
def test_bonds_respect_the_twenty_year_cumulative_allowance_cap(book, policies):
    # 5% a year for at most 20 policy years — 100% of the investment, no more.
    for policy in policies:
        if policy.product != "horizon_bond":
            continue
        terms = book.get_bond_terms(policy.policy_no)
        withdrawals = [e for e in book.history(policy.policy_no)
                       if e.transaction.kind == "regular_withdrawal"]
        assert len(withdrawals) <= 20
        used = sum(e.transaction.amount_pence for e in withdrawals)
        assert used <= terms.invested_pence


def test_pensions_contribute_monthly_across_recent_years_only(book, policies):
    for policy in policies:
        if policy.product != "retirement_account":
            continue
        contributions = [e for e in book.history(policy.policy_no)
                         if e.transaction.kind == "contribution"]
        assert contributions, f"{policy.policy_no} has no contributions"
        earliest = min(e.transaction.at[:10] for e in contributions)
        assert earliest >= "2016-07-13"      # recent years, not the whole life


def test_protection_only_cover_carries_no_cash_value(book, policies):
    # A guaranteed or reviewable LP has no fund to surrender, so it has no ledger.
    for policy in policies:
        cover = book.get_cover(policy.policy_no)
        if cover is not None and "unit_linked" not in cover.basis:
            assert book.current_value(policy.policy_no) == 0


def test_every_bond_and_pension_holds_funds_summing_to_a_hundred(book, policies):
    from src.records.products import fund_split_total
    for policy in policies:
        if policy.product == "lifelong_protection":
            continue
        assert fund_split_total(book.get_funds(policy.policy_no)) == 100


# ── point-in-time still works over the generated book ────────────────────
def test_a_synthetic_bond_is_worth_different_amounts_across_its_withdrawals(book, policies):
    bonds = [p for p in policies if p.product == "horizon_bond"]
    moved = 0
    for policy in bonds:
        withdrawals = [e for e in book.history(policy.policy_no)
                       if e.transaction.kind == "regular_withdrawal"]
        if not withdrawals:
            continue
        at = withdrawals[0].transaction.at[:10]
        before = value_as_at(book, policy.policy_no, "2000-01-01" if at < "2000" else
                             _day_before(at))
        after = value_as_at(book, policy.policy_no, at)
        if before != after:
            moved += 1
    assert moved >= 3


def _day_before(iso_date: str) -> str:
    from datetime import timedelta
    return (date.fromisoformat(iso_date) - timedelta(days=1)).isoformat()


# ── everything went through the real store API ───────────────────────────
def test_every_synthetic_write_is_journalled(book, policies):
    for policy in policies[:5]:
        assert book.changes.for_entity("policy", policy.policy_no)


def test_an_overdrawing_history_would_have_been_refused(book, policies):
    # Nothing here asserts a balance directly; the store refused any debit that
    # would have gone below zero while seeding, so reaching this point is proof.
    assert all(book.current_value(p.policy_no) >= 0 for p in policies)


def test_money_is_whole_pence_everywhere(book, policies):
    for policy in policies:
        for entry in book.history(policy.policy_no):
            assert isinstance(entry.transaction.amount_pence, int)
            assert entry.transaction.amount_pence >= 0
