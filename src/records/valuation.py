"""Point-in-time valuation — what a policy was worth on a given date.

A fold over the ledger entries dated on or before the moment asked about.

Deliberately **not** a schema feature: no stored snapshots, no as-at table, no
nightly job. The ledger is already append-only and already carries every
movement's own timestamp, so the past is not something to remember — it is
something to stop reading at. That also means a valuation can never drift out
of step with the transactions behind it, because it *is* those transactions.

Nothing here reads the wall clock; the caller supplies ``as_at``.
"""

from __future__ import annotations

from typing import Any

from src.records.models import LedgerEntry


def _inclusive_bound(as_at: str) -> str:
    """The upper bound to compare timestamps against.

    A bare date means the whole of that day: asked "what was it worth on 12
    April", a movement stamped that morning has happened. ISO strings sort
    chronologically, so extending the date to its last instant is all the
    comparison needs.
    """
    return f"{as_at}T23:59:59.999999" if len(as_at) == 10 else as_at


def entries_as_at(book: Any, policy_no: str, as_at: str) -> "tuple[LedgerEntry, ...]":
    """The policy's ledger rows that had happened by ``as_at``, in order.

    Raises ``RecordError`` (from the store) for a policy the book does not
    know — a silent empty history would read as "nothing ever happened".
    """
    bound = _inclusive_bound(as_at)
    return tuple(e for e in book.history(policy_no) if e.transaction.at <= bound)


def value_as_at(book: Any, policy_no: str, as_at: str) -> int:
    """The policy's value in pence as at ``as_at``.

    Sums the movements rather than reading the last row's ``balance_after``,
    so the answer is derived from the transactions themselves.
    """
    return sum(e.transaction.signed_pence for e in entries_as_at(book, policy_no, as_at))
