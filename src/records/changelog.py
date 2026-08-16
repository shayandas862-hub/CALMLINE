"""The change journal — the ledger's non-money sibling (D-CL-026).

The ledger journals money. This journals everything else: an address change, a
mandate edit, a status flip. Together they make "every change is auditable"
literal across the whole store, and any past state reconstructable by replay.

Append-only, and deliberately **app-level rather than a database trigger** — so
the in-memory and Postgres stores behave identically and the guarantee is
testable offline. Every entry carries who did it, what it came from, and an
injected timestamp; nothing here reads the wall clock.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

# A change is always traceable to a case, an interaction, or the seed. Anything
# else is an unattributed edit, which is the thing this journal exists to make
# impossible.
SOURCE_REF_RE = re.compile(r"^(CW-\d{9}|CN-\d{10}|seed)$")


@dataclass(frozen=True)
class FieldDelta:
    """One field's before and after."""

    field: str
    old: Any
    new: Any


@dataclass(frozen=True)
class RecordChangeEntry:
    """One mutating store operation, recorded."""

    seq: int
    entity_type: str
    entity_id: str
    changes: tuple[FieldDelta, ...]
    actor: str
    source_ref: str
    at: str

    def __post_init__(self) -> None:
        if not SOURCE_REF_RE.match(self.source_ref):
            raise ValueError(
                f"source_ref {self.source_ref!r} must be a CW- case, a CN- interaction, "
                "or 'seed'"
            )


class ChangeJournal:
    """An append-only sequence of record changes.

    There is no delete, no update, and no clear — not by convention but by
    absence. ``entries()`` hands back a tuple, so a caller cannot reach in and
    edit the history it was given.
    """

    def __init__(self) -> None:
        self._entries: list[RecordChangeEntry] = []

    def append(
        self,
        *,
        entity_type: str,
        entity_id: str,
        changes: "tuple[FieldDelta, ...]",
        actor: str,
        source_ref: str,
        at: str,
    ) -> RecordChangeEntry:
        """Record one change and return the entry it created."""
        entry = RecordChangeEntry(
            seq=len(self._entries) + 1,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=tuple(changes),
            actor=actor,
            source_ref=source_ref,
            at=at,
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> "tuple[RecordChangeEntry, ...]":
        """An immutable snapshot of the whole journal, in order."""
        return tuple(self._entries)

    def for_entity(self, entity_type: str, entity_id: str) -> "tuple[RecordChangeEntry, ...]":
        """Every change recorded against one entity, in order."""
        return tuple(
            e for e in self._entries
            if e.entity_type == entity_type and e.entity_id == entity_id
        )

    def replay(self, entity_type: str, entity_id: str, at: str) -> dict[str, Any]:
        """The fields known to have changed on or before ``at``, as they then
        stood. The reconstruction half of "any past state is replayable"."""
        state: dict[str, Any] = {}
        for entry in self.for_entity(entity_type, entity_id):
            if entry.at > at:
                break
            for delta in entry.changes:
                state[delta.field] = delta.new
        return state


def diff(before: Any, after: Any, fields: "tuple[str, ...]") -> "tuple[FieldDelta, ...]":
    """Field deltas between two frozen records — empty when nothing moved."""
    deltas = []
    for name in fields:
        old, new = getattr(before, name), getattr(after, name)
        if old != new:
            deltas.append(FieldDelta(field=name, old=old, new=new))
    return tuple(deltas)
