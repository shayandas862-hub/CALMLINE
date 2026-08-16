"""The agent's memory, scoped to the interaction (AD-CL-037).

Before this, every question started cold: ``run_console_agent`` seeded
``messages`` fresh per request, so a handler's follow-up knew nothing of their
first. Phase 4's demo only appeared to work because ``policy_no`` and
``verification_id`` travel as request context — a workaround for missing memory,
not memory.

**Why the interaction is the boundary.** AD-CL-029 already spends a verification
when the `CN-` closes. Making the interaction the conversation container means
the conversation's lifetime and the right to see what is in it become the same
fact: a transcript holding disclosed personal data cannot outlive the permission
that unlocked it, because they end together. Nothing extra has to be invented to
make that true — it falls out of the boundary. No session- or handler-scoped
alternative has that property.

**Scoped to `(cn_ref, policy_no)`, not to `cn_ref` alone.** A verification is
scoped to the pair. A handler who verifies policy A, converses, then opens
policy B inside the same interaction leaves A's record in the model's context
while the gate correctly demands a fresh verification for B — the agent could
then answer about B using A's data. That is D-CL-052's hole one layer up, and
the endpoint gate cannot see it because nothing crosses the endpoint. Keying on
the pair closes it structurally rather than by remembering to.

**Pruned, never summarised** (`P-CL-001` §3). A long call accumulates records,
ledger history and clauses. Summarising them would put a derived figure in
context — "the policy is worth about £150k" traces to no ledger row and breaks
the two-store rule outright. Old turns are dropped **whole**, so every number
still in context is one the record produced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: How many exchanges to keep per conversation. Generous for a phone call, and
#: bounded so a long one cannot grow the context without limit.
_DEFAULT_MAX_TURNS = 12


@dataclass(frozen=True)
class Turn:
    """One exchange: what the handler asked, and what the agent answered."""

    question: str
    answer: str


class ConversationStore:
    """Conversations, keyed by ``(cn_ref, policy_no)`` and ending with the `CN-`.

    Deliberately **not** a general cache: there is no eviction by age, no size
    budget in tokens and no lookup that crosses an interaction. The only way a
    conversation ends is the interaction ending, which is the point.
    """

    def __init__(self, *, max_turns: int = _DEFAULT_MAX_TURNS) -> None:
        self._turns: dict[tuple[str, str], list[Turn]] = {}
        self._max_turns = max_turns

    # ── writing ──────────────────────────────────────────────────────────
    def record(self, cn_ref: str, policy_no: str, *, question: str,
               answer: str) -> Turn:
        """Append one exchange, dropping the oldest whole turns past the cap."""
        turn = Turn(question=question, answer=answer)
        held = self._turns.setdefault(self._key(cn_ref, policy_no), [])
        held.append(turn)
        if len(held) > self._max_turns:
            # Whole turns, from the front. Never a summary — see the module
            # docstring: a summarised policy record is a fabricated number.
            del held[:len(held) - self._max_turns]
        return turn

    # ── reading ──────────────────────────────────────────────────────────
    def turns(self, cn_ref: str, policy_no: str) -> tuple[Turn, ...]:
        """An immutable snapshot of this conversation, oldest first."""
        return tuple(self._turns.get(self._key(cn_ref, policy_no), ()))

    def messages(self, cn_ref: str, policy_no: str) -> list[dict[str, Any]]:
        """The conversation as Anthropic ``messages``, ready to seed a run.

        Empty when there is nothing to say. A placeholder turn would be a
        fabricated exchange sitting in the model's context.
        """
        out: list[dict[str, Any]] = []
        for turn in self.turns(cn_ref, policy_no):
            out.append({"role": "user", "content": turn.question})
            out.append({"role": "assistant", "content": turn.answer})
        return out

    # ── expiry (AD-CL-029's boundary, mirrored) ──────────────────────────
    def expire_for_interaction(self, cn_ref: str) -> int:
        """End every conversation on ``cn_ref``. Returns how many ended.

        Mirrors ``VerificationGate.expire_for_interaction`` deliberately: the
        two must end together, or a transcript of disclosed data outlives the
        verification that permitted it.

        Unlike the gate, the turns are **removed** rather than marked spent. The
        gate keeps its records because they are the audit trail of a decision;
        this holds the personal data itself, and there is no reason to keep it
        once nobody may read it.
        """
        doomed = [key for key in self._turns if key[0] == cn_ref]
        for key in doomed:
            del self._turns[key]
        return len(doomed)

    @staticmethod
    def _key(cn_ref: str, policy_no: str) -> tuple[str, str]:
        return (cn_ref or "", policy_no or "")
