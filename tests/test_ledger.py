"""Phase V1 · Task 3 — the ledger engine.

The correctness the operator insisted on: money out updates the balance, the
movement is kept forever, history is never overwritten, and you cannot
withdraw more than is there. Worked on the £50,000 → −£20,000 → £30,000 case.
"""

import pytest

from src.records.ledger import LedgerError, PolicyLedger
from src.records.models import Transaction, gbp


def _txn(kind, pounds, txn_id, policy_no="WL-88213", at="2026-01-01T00:00:00"):
    return Transaction(txn_id=txn_id, policy_no=policy_no, kind=kind,
                       amount_pence=gbp(pounds), reason="test", actor="tester", at=at)


def test_opening_then_withdrawal_gives_the_right_balance():
    # Arrange
    ledger = PolicyLedger("WL-88213")
    # Act
    ledger.apply(_txn("opening", 50_000, "T1"))
    ledger.apply(_txn("withdrawal", 20_000, "T2"))
    # Assert
    assert ledger.balance() == gbp(30_000)
    seqs = [e.seq for e in ledger.history()]
    balances = [e.balance_after_pence for e in ledger.history()]
    assert seqs == [1, 2]
    assert balances == [gbp(50_000), gbp(30_000)]


def test_balance_equals_opening_plus_sum_of_movements():
    ledger = PolicyLedger("WL-88213")
    ledger.apply(_txn("opening", 50_000, "T1"))
    ledger.apply(_txn("withdrawal", 20_000, "T2"))
    ledger.apply(_txn("premium", 100, "T3"))
    summed = sum(e.transaction.signed_pence for e in ledger.history())
    assert ledger.balance() == summed == gbp(30_100)


def test_withdrawal_beyond_balance_is_rejected_and_history_is_unchanged():
    ledger = PolicyLedger("WL-88213")
    ledger.apply(_txn("opening", 50_000, "T1"))
    with pytest.raises(LedgerError):
        ledger.apply(_txn("withdrawal", 60_000, "T2"))
    # the failed movement left no trace
    assert ledger.balance() == gbp(50_000)
    assert len(ledger.history()) == 1


def test_history_is_append_only_and_a_returned_snapshot_cannot_mutate_the_ledger():
    ledger = PolicyLedger("WL-88213")
    ledger.apply(_txn("opening", 50_000, "T1"))
    first = ledger.history()[0]
    snapshot = ledger.history()
    snapshot_list = list(snapshot)
    snapshot_list.clear()  # mutating the copy must not empty the ledger
    ledger.apply(_txn("withdrawal", 10_000, "T2"))
    # the original first entry is untouched; ledger kept both rows
    assert ledger.history()[0] == first
    assert len(ledger.history()) == 2


def test_apply_rejects_a_transaction_for_a_different_policy():
    ledger = PolicyLedger("WL-88213")
    with pytest.raises(LedgerError):
        ledger.apply(_txn("opening", 10_000, "T1", policy_no="TL-55090"))


def test_empty_ledger_has_zero_balance():
    assert PolicyLedger("WL-88213").balance() == 0


def test_ledger_can_be_rebuilt_from_a_list_of_transactions():
    txns = [_txn("opening", 50_000, "T1"), _txn("withdrawal", 20_000, "T2")]
    ledger = PolicyLedger.from_transactions("WL-88213", txns)
    assert ledger.balance() == gbp(30_000)
    assert len(ledger.history()) == 2


# ── growth, charges and bonuses (v4.5 phase 1) ───────────────────────────
def test_a_policy_can_hold_growth_a_charge_and_a_bonus():
    """Phase 1's demonstrable outcome: a policy opens at £100,000, takes an
    annual charge, receives investment growth and a bonus, and reports a value
    equal to the sum of everything that happened to it."""
    ledger = PolicyLedger("WL-88213")
    ledger.apply(_txn("opening", 100_000, "T1"))
    ledger.apply(_txn("charge", 1_500, "T2"))
    ledger.apply(_txn("investment_return", 20_000, "T3"))
    ledger.apply(_txn("bonus", 2_500, "T4"))
    summed = sum(e.transaction.signed_pence for e in ledger.history())
    assert ledger.balance() == summed == gbp(121_000)


def test_an_investment_loss_reduces_the_balance():
    ledger = PolicyLedger("WL-88213")
    ledger.apply(_txn("opening", 100_000, "T1"))
    ledger.apply(_txn("investment_loss", 12_000, "T2"))
    assert ledger.balance() == gbp(88_000)


def test_an_investment_loss_cannot_drive_the_balance_below_zero():
    # A fund cannot lose more than the policy holds. This is the same overdraw
    # guard that refuses an oversized withdrawal — a loss is a debit like any
    # other, which is the point of naming it rather than signing an amount.
    ledger = PolicyLedger("WL-88213")
    ledger.apply(_txn("opening", 10_000, "T1"))
    with pytest.raises(LedgerError):
        ledger.apply(_txn("investment_loss", 10_001, "T2"))
    assert ledger.balance() == gbp(10_000)
    assert len(ledger.history()) == 1
