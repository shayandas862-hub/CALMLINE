"""The data-protection gate — present, tick, record.

The system presents the `05-OPS:3.2` panel — held details for the handler's
eyes, prompts for the caller's ears — and the **handler ticks** each check the
caller states correctly (D-CL-114). The outcome is a ``VerificationRecord``
(D-CL-019). The AI never decides that someone is who they say they are — its
existence, not its judgement, is what unlocks disclosure.

A record is scoped to exactly one ``(cn_ref, policy_no)`` pair and stops
unlocking when the interaction closes (AD-CL-029). It is never deleted: an
expired verification still happened, and the audit needs to say so.

Failed and abandoned attempts are recorded alongside the passes. A gate that
only remembers its successes cannot evidence a refusal, which is the one thing
a regulator will ask it to do.

Time is injected everywhere. Nothing here reads the clock.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Optional

from src.identity.questions import (
    SV_THRESHOLD,
    HeldCheck,
    askable_kinds,
    held_checks,
)
from src.records.models import require_in

VERIFICATION_OUTCOMES = frozenset({"passed", "failed", "abandoned"})

# `05-OPS:3.5` — what to do when verification fails. Held as a data literal
# carrying its source, like every other cited rule in the repo (AD-CL-028).
CANNOT_VERIFY_SOURCE = "05-OPS:3.5"
_CANNOT_VERIFY_LINE = (
    "I'm not able to verify enough detail to continue on this call."
)
_SECURE_ALTERNATIVES = (
    "write to the correspondence details we hold",
    "use the secure portal",
)


@dataclass(frozen=True)
class VerificationRecord:
    """The machine-recorded outcome of one gate attempt.

    ``matched`` keeps which checks passed — the audit needs that detail. The
    caller-facing route (``cannot_verify_route``) deliberately does not: see
    `07-RUNBOOK:4.1`, where naming the failing element is itself a disclosure.
    """

    verification_id: str
    cn_ref: str
    policy_no: str
    outcome: str
    presented: tuple[str, ...]
    matched: tuple[str, ...]
    actor: str
    at: str
    expired_at: Optional[str] = None

    def __post_init__(self) -> None:
        require_in(self.verification_id, "verification outcome", self.outcome,
                   VERIFICATION_OUTCOMES)

    @property
    def unlocks(self) -> bool:
        """Whether this record currently permits disclosure."""
        return self.outcome == "passed" and self.expired_at is None


def cannot_verify_route(failed_kinds: tuple[str, ...] = ()) -> dict:
    """The `05-OPS:3.5` route when verification cannot be completed.

    ``failed_kinds`` is accepted so callers can pass what they know without
    having to remember not to — and is deliberately **ignored**. The route is
    identical whatever failed, so there is nothing here to leak. Disclosing
    which element was wrong lets a caller iterate towards a pass, and
    "helpfully" correcting a wrong detail is disclosure in its own right
    (`07-RUNBOOK:4.1`).
    """
    return {
        "source": CANNOT_VERIFY_SOURCE,
        "disclose": False,
        "say": _CANNOT_VERIFY_LINE,
        "alternatives": _SECURE_ALTERNATIVES,
        "log": "failed verification attempt recorded",
    }


class VerificationGate:
    """The verification records, in the order they were taken.

    Append-only by absence: there is no delete, update, edit or clear. Expiry
    marks a record spent rather than removing it.
    """

    def __init__(self) -> None:
        self._records: list[VerificationRecord] = []
        self._seq = 0

    # ── presenting ───────────────────────────────────────────────────────
    def present(self, *, cn_ref: str, policy_no: str, party: Any, policy: Any,
                at: str) -> tuple[HeldCheck, ...]:
        """The panel for the handler: prompts to read aloud, held values shown.

        Presenting verifies nothing — it is the handler's view of the record,
        not the caller's (D-CL-114).
        """
        return held_checks(party, policy)

    # ── confirming ───────────────────────────────────────────────────────
    def confirm(self, *, cn_ref: str, policy_no: str, party: Any, policy: Any,
                ticked: Any, actor: str, at: str) -> VerificationRecord:
        """Record which checks the handler confirmed, and the outcome.

        ``ticked`` names the checks the caller stated correctly — the
        handler's judgement, made against the held values on the screen
        (D-CL-019, literally). A tick for a check this record does not hold
        counts for nothing. Passing needs ``SV_THRESHOLD`` confirmed checks
        outright — not "three, or all of them if there are fewer". A record
        holding only two checkable items cannot satisfy "three of four", and
        saying so is the honest answer.
        """
        presented = askable_kinds(party, policy)
        chosen = set(ticked)
        matched = tuple(kind for kind in presented if kind in chosen)
        outcome = "passed" if len(matched) >= SV_THRESHOLD else "failed"
        return self._append(
            cn_ref=cn_ref, policy_no=policy_no, outcome=outcome,
            presented=presented, matched=matched, actor=actor, at=at)

    def abandon(self, *, cn_ref: str, policy_no: str, actor: str,
                at: str) -> VerificationRecord:
        """The caller rang off, or the handler stopped. Recorded, not dropped."""
        return self._append(cn_ref=cn_ref, policy_no=policy_no, outcome="abandoned",
                            presented=(), matched=(), actor=actor, at=at)

    # ── reading ──────────────────────────────────────────────────────────
    def is_verified(self, cn_ref: str, policy_no: str) -> bool:
        """Whether this exact interaction/policy pair is currently unlocked."""
        return self.active_record(cn_ref, policy_no) is not None

    def active_record(self, cn_ref: str,
                      policy_no: str) -> Optional[VerificationRecord]:
        """The live passed record for this pair, newest first, or ``None``."""
        for record in reversed(self._records):
            if (record.cn_ref == cn_ref and record.policy_no == policy_no
                    and record.unlocks):
                return record
        return None

    def records(self) -> tuple[VerificationRecord, ...]:
        """An immutable snapshot — mutating it cannot reach the gate."""
        return tuple(self._records)

    def for_interaction(self, cn_ref: str) -> tuple[VerificationRecord, ...]:
        return tuple(r for r in self._records if r.cn_ref == cn_ref)

    # ── expiry (AD-CL-029) ───────────────────────────────────────────────
    def expire_for_interaction(self, cn_ref: str, *, at: str) -> int:
        """Close out every live verification on an interaction.

        Called when the `CN-` closes. Returns how many were spent. The records
        stay; they simply stop unlocking anything.
        """
        spent = 0
        for index, record in enumerate(self._records):
            if record.cn_ref == cn_ref and record.unlocks:
                self._records[index] = replace(record, expired_at=at)
                spent += 1
        return spent

    # ── internals ────────────────────────────────────────────────────────
    def _append(self, *, cn_ref: str, policy_no: str, outcome: str,
                presented: tuple[str, ...], matched: tuple[str, ...], actor: str,
                at: str) -> VerificationRecord:
        self._seq += 1
        record = VerificationRecord(
            verification_id=f"VR-{self._seq:09d}", cn_ref=cn_ref,
            policy_no=policy_no, outcome=outcome, presented=presented,
            matched=matched, actor=actor, at=at)
        self._records.append(record)
        return record
