"""v3 phase 2 · Task 6 — record_transaction PROPOSES a movement; it never writes.

This is the structural guarantee that the AI cannot move money: the tool has no
store to write to, and returns a proposal a human must later commit.
"""

import pytest

from src.agent.tools.money_tools import ProposedTransaction, record_transaction
from src.records.models import Transaction, gbp
from src.records.seed import build_seed_book


def test_record_transaction_returns_a_human_gated_proposal():
    prop = record_transaction(policy_no="LP-20419876", kind="withdrawal",
                              amount_pence=gbp(20_000), reason="partial surrender",
                              actor="Reviewer B", at="2026-07-02T10:00:00")
    assert isinstance(prop, ProposedTransaction)
    assert prop.requires_human is True
    assert prop.kind == "withdrawal"
    assert prop.amount_pence == gbp(20_000)
    assert prop.policy_no == "LP-20419876"


def test_record_transaction_does_not_change_the_ledger():
    book = build_seed_book()
    before = book.current_value("LP-20419876")
    record_transaction(policy_no="LP-20419876", kind="withdrawal", amount_pence=gbp(5_000),
                       reason="test", actor="x", at="2026-07-02T10:00:00")
    # proposing a movement leaves the balance untouched — only a human commit moves it
    assert book.current_value("LP-20419876") == before


def test_record_transaction_validates_the_movement():
    with pytest.raises(ValueError):
        record_transaction(policy_no="LP-20419876", kind="teleport", amount_pence=1,
                           reason="?", actor="x", at="2026-07-02T10:00:00")
    with pytest.raises(ValueError):
        record_transaction(policy_no="LP-20419876", kind="withdrawal", amount_pence=-1,
                           reason="?", actor="x", at="2026-07-02T10:00:00")


def test_proposal_converts_to_a_committable_transaction():
    prop = record_transaction(policy_no="LP-20419876", kind="withdrawal",
                              amount_pence=gbp(20_000), reason="partial surrender",
                              actor="Reviewer B", at="2026-07-02T10:00:00")
    txn = prop.to_transaction("TXN-1")
    assert isinstance(txn, Transaction)
    assert txn.txn_id == "TXN-1"
    assert txn.amount_pence == gbp(20_000)
