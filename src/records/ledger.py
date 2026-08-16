"""The ledger engine — append-only, exact, overdraw-safe.

A ``PolicyLedger`` holds one policy's ordered history. Applying a transaction
appends a new immutable row with the resulting balance; it never edits or
removes an existing row, and it refuses a debit that would take the balance
below zero. The current value is simply the last row's balance.
"""

from __future__ import annotations

from src.records.models import LedgerEntry, Transaction


class LedgerError(RuntimeError):
    """Raised when a transaction cannot be applied (wrong policy, or overdraw)."""


class PolicyLedger:
    """One policy's append-only transaction history."""

    def __init__(self, policy_no: str) -> None:
        self._policy_no = policy_no
        self._entries: list[LedgerEntry] = []

    @property
    def policy_no(self) -> str:
        return self._policy_no

    def balance(self) -> int:
        """Current value in pence — the last row's balance, or 0 if empty."""
        return self._entries[-1].balance_after_pence if self._entries else 0

    def history(self) -> tuple[LedgerEntry, ...]:
        """An immutable snapshot of every row, in order."""
        return tuple(self._entries)

    def apply(self, txn: Transaction) -> LedgerEntry:
        """Append ``txn`` to the history and return the new row.

        Raises ``LedgerError`` if the transaction belongs to another policy or
        if it is a debit that would overdraw the balance.
        """
        if txn.policy_no != self._policy_no:
            raise LedgerError(
                f"transaction {txn.txn_id} is for {txn.policy_no}, not {self._policy_no}"
            )
        new_balance = self.balance() + txn.signed_pence
        if new_balance < 0:
            raise LedgerError(
                f"{txn.kind} of {txn.amount_pence}p would overdraw {self._policy_no} "
                f"(balance {self.balance()}p)"
            )
        entry = LedgerEntry(
            seq=len(self._entries) + 1,
            transaction=txn,
            balance_after_pence=new_balance,
        )
        self._entries.append(entry)
        return entry

    @classmethod
    def from_transactions(cls, policy_no: str, txns: "list[Transaction]") -> "PolicyLedger":
        """Rebuild a ledger by applying ``txns`` in order (used by the store/seed)."""
        ledger = cls(policy_no)
        for txn in txns:
            ledger.apply(txn)
        return ledger
