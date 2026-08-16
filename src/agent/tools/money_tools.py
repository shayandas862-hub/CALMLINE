"""The money tool — record_transaction PROPOSES a movement, never commits it.

This is where "the AI never moves money" is made structural: the tool takes no
store, so it cannot write. It validates the movement (reusing the Transaction
rules) and returns a ``ProposedTransaction`` that a named human commits later
via the ledger. Committing is a separate, human-gated step (a later phase).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.records.models import Transaction


@dataclass(frozen=True)
class ProposedTransaction:
    """A validated but UNCOMMITTED movement, awaiting a human decision."""

    policy_no: str
    kind: str
    amount_pence: int
    reason: str
    actor: str
    at: str
    requires_human: bool = True

    def to_transaction(self, txn_id: str) -> Transaction:
        """Turn the proposal into a committable Transaction (used at approval)."""
        return Transaction(
            txn_id=txn_id,
            policy_no=self.policy_no,
            kind=self.kind,
            amount_pence=self.amount_pence,
            reason=self.reason,
            actor=self.actor,
            at=self.at,
        )


def record_transaction(*, policy_no: str, kind: str, amount_pence: int, reason: str,
                       actor: str, at: str) -> ProposedTransaction:
    """Validate a movement and return it as a human-gated proposal (no write)."""
    # Reuse the Transaction rules to reject bad kinds/amounts up front.
    Transaction(txn_id="PROPOSED", policy_no=policy_no, kind=kind,
                amount_pence=amount_pence, reason=reason, actor=actor, at=at)
    return ProposedTransaction(policy_no=policy_no, kind=kind, amount_pence=amount_pence,
                               reason=reason, actor=actor, at=at)
