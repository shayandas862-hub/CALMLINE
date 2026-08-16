"""v4 phase 2 · task 2 — point-in-time valuation.

"What was this bond worth on 12 April?" is a fold over the ledger entries dated
on or before that moment. It is a pure function, not a schema feature: no stored
snapshots, no as-at table, nothing to keep in step. The ledger is already the
truth; this just stops reading it at a date.
"""

import pytest

from src.records.models import Contact, Party, Policy, Transaction, gbp
from src.records.seed import build_seed_book
from src.records.store import InMemoryRecordBook, RecordError
from src.records.valuation import entries_as_at, value_as_at

SEED = dict(actor="seed", source_ref="seed", at="2019-03-01T00:00:00")


def _bond_book() -> InMemoryRecordBook:
    """A bond with an opening and two dated withdrawals — the shape task 3
    seeds for real from `02-BOND:III.4`."""
    book = InMemoryRecordBook()
    book.add_party(Party(party_id="PH-0002", name="Argon Basalt 27", dob="1962-09-30",
                         registered_address="8 Cornice Row, Sampleton",
                         contact=Contact(phone="07700 900102",
                                         email="ph-0002@example.org", registered=True)),
                   **SEED)
    book.add_policy(Policy(policy_no="HB-40582213", product="horizon_bond",
                           status="in_force", start_date="2019-03-01",
                           holder_party_id="PH-0002"), **SEED)
    for txn_id, kind, pounds, at in (
        ("TXN-1", "opening", 120_000, "2019-03-01T00:00:00"),
        ("TXN-2", "regular_withdrawal", 6_000, "2020-03-01T00:00:00"),
        ("TXN-3", "regular_withdrawal", 6_000, "2021-03-01T00:00:00"),
    ):
        book.apply_transaction("HB-40582213", Transaction(
            txn_id=txn_id, policy_no="HB-40582213", kind=kind,
            amount_pence=gbp(pounds), reason="seeded", actor="seed", at=at))
    return book


# ── the fold ─────────────────────────────────────────────────────────────
def test_value_before_the_first_entry_is_zero():
    assert value_as_at(_bond_book(), "HB-40582213", "2019-02-28") == 0


def test_value_on_the_opening_date_includes_that_days_entry():
    # A date-only as-at means the whole of that day, so an entry stamped at
    # midnight on the 1st counts on the 1st.
    assert value_as_at(_bond_book(), "HB-40582213", "2019-03-01") == gbp(120_000)


def test_value_between_two_withdrawals_sees_only_the_first():
    assert value_as_at(_bond_book(), "HB-40582213", "2020-06-30") == gbp(114_000)


def test_value_after_both_withdrawals_sees_both():
    assert value_as_at(_bond_book(), "HB-40582213", "2026-04-12") == gbp(108_000)


def test_two_dates_spanning_a_withdrawal_give_different_answers():
    # The phase's done criterion, stated directly.
    book = _bond_book()
    before = value_as_at(book, "HB-40582213", "2020-02-29")
    after = value_as_at(book, "HB-40582213", "2020-03-02")
    assert before == gbp(120_000)
    assert after == gbp(114_000)
    assert before != after


def test_a_far_future_date_equals_the_current_value():
    book = _bond_book()
    assert value_as_at(book, "HB-40582213", "2099-12-31") == book.current_value("HB-40582213")


def test_a_timestamped_as_at_cuts_within_the_day():
    book = _bond_book()
    assert value_as_at(book, "HB-40582213", "2020-03-01T00:00:00") == gbp(114_000)
    # one microsecond earlier, the withdrawal has not happened yet
    assert value_as_at(book, "HB-40582213", "2020-02-29T23:59:59") == gbp(120_000)


# ── growth, charges and bonuses (v4.5 phase 1) ───────────────────────────
def _bond_book_with_fund_movements() -> InMemoryRecordBook:
    """The bond above, plus what a real book carries between the phone calls:
    what the fund did, the annual charge, and a bonus added at an interval."""
    book = _bond_book()
    for txn_id, kind, pounds, at in (
        ("TXN-4", "investment_return", 9_000, "2022-03-01T00:00:00"),
        ("TXN-5", "charge", 1_200, "2022-03-01T00:00:00"),
        ("TXN-6", "bonus", 3_000, "2023-03-01T00:00:00"),
    ):
        book.apply_transaction("HB-40582213", Transaction(
            txn_id=txn_id, policy_no="HB-40582213", kind=kind,
            amount_pence=gbp(pounds), reason="seeded", actor="seed", at=at))
    return book


def test_a_valuation_before_a_bonus_excludes_it():
    # 120,000 − 6,000 − 6,000 + 9,000 − 1,200, with the bonus still a year off.
    book = _bond_book_with_fund_movements()
    assert value_as_at(book, "HB-40582213", "2022-12-31") == gbp(115_800)


def test_a_valuation_after_the_bonus_includes_it():
    book = _bond_book_with_fund_movements()
    assert value_as_at(book, "HB-40582213", "2023-03-01") == gbp(118_800)


# ── the entries behind the number ────────────────────────────────────────
def test_entries_as_at_returns_only_what_had_happened():
    entries = entries_as_at(_bond_book(), "HB-40582213", "2020-06-30")
    assert [e.transaction.txn_id for e in entries] == ["TXN-1", "TXN-2"]


def test_entries_as_at_is_ordered_and_immutable():
    entries = entries_as_at(_bond_book(), "HB-40582213", "2099-01-01")
    assert isinstance(entries, tuple)
    assert [e.seq for e in entries] == [1, 2, 3]


# ── it is a pure read ────────────────────────────────────────────────────
def test_valuation_does_not_touch_the_book():
    book = _bond_book()
    changes_before = len(book.changes.entries())
    history_before = book.history("HB-40582213")
    value_as_at(book, "HB-40582213", "2020-06-30")
    assert book.current_value("HB-40582213") == gbp(108_000)
    assert book.history("HB-40582213") == history_before
    assert len(book.changes.entries()) == changes_before   # a read journals nothing


def test_repeated_calls_give_the_same_answer():
    book = _bond_book()
    first = value_as_at(book, "HB-40582213", "2020-06-30")
    assert value_as_at(book, "HB-40582213", "2020-06-30") == first


# ── errors ───────────────────────────────────────────────────────────────
def test_unknown_policy_raises_rather_than_returning_zero():
    # A silent zero would read as "this policy is worth nothing".
    with pytest.raises(RecordError):
        value_as_at(_bond_book(), "HB-99999999", "2026-04-12")


# ── against the seeded anchors ───────────────────────────────────────────
def test_an_anchor_is_worth_nothing_before_its_first_entry():
    book = build_seed_book()
    assert value_as_at(book, "LP-20419876", "2016-04-30") == 0
    assert value_as_at(book, "LP-20419876", "2016-05-01") == gbp(46_210)
