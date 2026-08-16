"""The timeline engine — one policy, played forward, one checked movement at a time.

The engine before any product knows about it. It walks a policy from its start
date to the world's birth date, offering each proposed movement to the rulebook
and appending it only if accepted.

**A refused movement stops that policy and is recorded.** Never adjusted, never
retried, never skipped quietly. That is the whole architecture in one sentence:
generation is where correctness is decided, and the code that would refuse a
live handler is the code that builds the world.

The engine's own checks are the ones no product can waive — the world's calendar,
the order of history, the closed movement vocabulary and the money guard. What a
*bond* or a *pension* additionally refuses arrives through ``rules``, a seam each
product fills, so this file never learns what a segment or a benefit route is.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Iterable, Optional, Sequence

from src.records.ledger import LedgerError, PolicyLedger
from src.records.models import LedgerEntry, Policy, Transaction
from src.records.valuation import value_as_at
from world import WORLD_BIRTH_DATE
from world.lifetimes.report import Refusal, RefusalReport

# Who the world says made these movements. Honest rather than decorative: no
# handler took a 1998 premium, the builder did, and a made-up employee name on
# thirty years of ledger rows would be a fabricated fact in an audit trail.
WORLD_ACTOR = "world-builder"

# A product rule: given the policy, the movement being proposed and the balance
# it would land on, return a reason to refuse — or ``None`` to allow it.
Rule = Callable[[Policy, "Movement", int], Optional[str]]


@dataclass(frozen=True)
class Movement:
    """A movement the world proposes, before the rulebook has seen it.

    Deliberately not a ``Transaction``: a proposal has no sequence number, no
    resulting balance and no guarantee of being legal. It becomes a transaction
    only once every check has passed.
    """

    on: date
    kind: str
    amount_pence: int
    reason: str
    actor: str = WORLD_ACTOR


@dataclass(frozen=True)
class Lifetime:
    """A policy played to the world's birth date, and the ledger it left.

    Value is never stored — it is a fold over the movements, using the
    insurer's own valuation code rather than a second copy of it.
    """

    policy_no: str
    entries: tuple[LedgerEntry, ...]

    @property
    def value_pence(self) -> int:
        """What it is worth at the world's birth date."""
        return sum(e.transaction.signed_pence for e in self.entries)

    def history(self, policy_no: str) -> tuple[LedgerEntry, ...]:
        """The book protocol `src.records.valuation` folds over."""
        if policy_no != self.policy_no:
            raise ValueError(
                f"lifetime holds {self.policy_no}, was asked for {policy_no}")
        return self.entries

    def value_at(self, on: date) -> int:
        """What it was worth on ``on`` — the insurer's own point-in-time fold."""
        return value_as_at(self, self.policy_no, on.isoformat())


def _calendar_refusal(movement: Movement, start: date, born: date,
                      previous: Optional[date]) -> Optional[str]:
    """The world's own calendar, which no product may waive."""
    if movement.on < start:
        return (f"dated {movement.on.isoformat()}, before the policy start date "
                f"{start.isoformat()}")
    if movement.on > born:
        return (f"dated {movement.on.isoformat()}, after the world's birth date "
                f"{born.isoformat()}")
    if previous is not None and movement.on < previous:
        return (f"dated {movement.on.isoformat()}, out of order — the movement "
                f"before it is dated {previous.isoformat()}")
    return None


def _as_transaction(policy: Policy, movement: Movement,
                    seq: int) -> "Transaction | str":
    """Build the transaction, or say why the movement is not one.

    The closed vocabulary (`0003_world_movements.sql`) and the money guard both
    live in `Transaction.__post_init__`, so this asks the rulebook rather than
    re-stating it. A malformed movement becomes a refusal the report can show,
    not a traceback that takes the whole build down.
    """
    try:
        return Transaction(
            txn_id=f"{policy.policy_no}-{seq:04d}",
            policy_no=policy.policy_no,
            kind=movement.kind,
            amount_pence=movement.amount_pence,
            reason=movement.reason,
            actor=movement.actor,
            at=f"{movement.on.isoformat()}T00:00:00",
        )
    except (ValueError, TypeError) as exc:
        return str(exc)


def play(
    policy: Policy,
    movements: Iterable[Movement],
    *,
    report: RefusalReport,
    rules: Sequence[Rule] = (),
    born: date = WORLD_BIRTH_DATE,
) -> Optional[Lifetime]:
    """Play ``policy`` forward through ``movements``.

    Returns the finished `Lifetime`, or ``None`` if any movement was refused —
    and **``None`` means no partial policy**, not a shortened one. A policy that
    could not be built legally to the end was never a policy; handing back the
    part that happened to be legal would put a figure in the book that nothing
    reconciles to.

    Every refusal is recorded against ``report`` before returning.
    """
    ledger = PolicyLedger(policy.policy_no)
    start = date.fromisoformat(policy.start_date)
    previous: Optional[date] = None

    def refuse(movement: Movement, reason: str) -> None:
        report.record(Refusal(
            policy_no=policy.policy_no,
            on=movement.on,
            kind=movement.kind,
            amount_pence=movement.amount_pence,
            reason=reason,
        ))

    for seq, movement in enumerate(movements, start=1):
        reason = _calendar_refusal(movement, start, born, previous)
        if reason is not None:
            refuse(movement, reason)
            return None

        # The vocabulary and the money guard, asked of the rulebook itself.
        built = _as_transaction(policy, movement, seq)
        if isinstance(built, str):
            refuse(movement, built)
            return None

        # The product's own rules, asked before the ledger is touched — and
        # told the balance the movement *would* land on, not the one after it.
        balance = ledger.balance()
        for rule in rules:
            reason = rule(policy, movement, balance)
            if reason is not None:
                refuse(movement, reason)
                return None

        try:
            ledger.apply(built)
        except LedgerError as exc:
            refuse(movement, str(exc))
            return None
        previous = movement.on

    return Lifetime(policy_no=policy.policy_no, entries=ledger.history())
