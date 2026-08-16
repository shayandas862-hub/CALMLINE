"""Interactions — one row per inbound or outbound contact (`CN-` + 10).

An interaction is the container a verification lives in and a case is raised
from: who made contact, on what, and what came of it.

Seeded historical rows carry only what their source states. A sample record's
``recent:`` line says *what happened and when*, not through which channel, so
``channel`` is absent rather than guessed — the store would rather hold a gap
than a plausible invention.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Optional

from src.records.models import require_in

CHANNELS = frozenset({"phone", "portal", "email", "post", "adviser_portal"})
CN_REF_RE = re.compile(r"^CN-\d{10}$")


class InteractionError(RuntimeError):
    """Raised for an interaction the store cannot honour."""


@dataclass(frozen=True)
class Interaction:
    """One contact. ``opened_at`` is injected; nothing here reads the clock."""

    cn_ref: str
    policy_no: str
    opened_at: str
    channel: Optional[str] = None
    caller_party_id: Optional[str] = None
    claimed_relationship: str = ""
    verification_ref: Optional[str] = None
    intent: str = ""
    outcome: str = ""
    closed_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not CN_REF_RE.match(self.cn_ref):
            raise ValueError(f"cn_ref {self.cn_ref!r} is not CN- plus ten digits")
        if self.channel is not None:
            require_in(self.cn_ref, "channel", self.channel, CHANNELS)

    @property
    def is_open(self) -> bool:
        return self.closed_at is None


class InteractionStore:
    """The `CN-` rows, in the order they were opened.

    Three operations: ``open`` starts a contact, ``log`` records what it was
    about while it is live, and ``close`` ends it. A closed interaction is a
    historical record — logging against one is refused rather than allowed to
    quietly rewrite what happened.
    """

    def __init__(self) -> None:
        self._rows: dict[str, Interaction] = {}
        self._seq = 0

    def add(self, interaction: Interaction) -> Interaction:
        """Record an already-built interaction (used by the seed)."""
        if interaction.cn_ref in self._rows:
            raise InteractionError(f"{interaction.cn_ref} already exists")
        self._rows[interaction.cn_ref] = interaction
        return interaction

    def open(self, *, policy_no: str, at: str, channel: Optional[str] = None,
             caller_party_id: Optional[str] = None,
             claimed_relationship: str = "") -> Interaction:
        """Start a contact and mint its `CN-` reference."""
        self._seq += 1
        return self.add(Interaction(
            cn_ref=f"CN-{self._seq:010d}", policy_no=policy_no, opened_at=at,
            channel=channel, caller_party_id=caller_party_id,
            claimed_relationship=claimed_relationship))

    def log(self, cn_ref: str, *, intent: Optional[str] = None,
            outcome: Optional[str] = None,
            verification_ref: Optional[str] = None) -> Interaction:
        """Record what a live contact was about."""
        row = self._require(cn_ref)
        if not row.is_open:
            raise InteractionError(f"{cn_ref} is closed; it cannot be logged against")
        updated = replace(
            row,
            intent=row.intent if intent is None else intent,
            outcome=row.outcome if outcome is None else outcome,
            verification_ref=(row.verification_ref if verification_ref is None
                              else verification_ref))
        self._rows[cn_ref] = updated
        return updated

    def close(self, cn_ref: str, *, at: str,
              outcome: Optional[str] = None) -> Interaction:
        """End a contact at the injected time."""
        row = self._require(cn_ref)
        if not row.is_open:
            raise InteractionError(f"{cn_ref} is already closed")
        if at < row.opened_at:
            raise InteractionError(
                f"{cn_ref}: cannot close at {at} — it opened at {row.opened_at}")
        updated = replace(row, closed_at=at,
                          outcome=row.outcome if outcome is None else outcome)
        self._rows[cn_ref] = updated
        return updated

    def get(self, cn_ref: str) -> Optional[Interaction]:
        return self._rows.get(cn_ref)

    def open_interactions(self) -> "tuple[Interaction, ...]":
        return tuple(r for r in self._rows.values() if r.is_open)

    def _require(self, cn_ref: str) -> Interaction:
        row = self._rows.get(cn_ref)
        if row is None:
            raise InteractionError(f"unknown interaction {cn_ref!r}")
        return row

    def all(self) -> "tuple[Interaction, ...]":
        return tuple(self._rows.values())

    def for_policy(self, policy_no: str) -> "tuple[Interaction, ...]":
        return tuple(r for r in self._rows.values() if r.policy_no == policy_no)
