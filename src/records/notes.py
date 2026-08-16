"""Contact notes — what was actually said, attributable and immutable.

The schema had nowhere to put this. `interactions` carries an ``intent`` and an
``outcome``, both short strings from closed vocabularies, and nothing that could
hold a sentence. Everything a handler would actually want to read back before
returning a call was missing.

**Append-only, and frozen.** A note editable after the call is not a record of
the call. A correction is a new note referencing the one it corrects, so the
original stays exactly as written and the sequence itself shows that somebody
changed their mind — which is more honest than a silently better version.

The database enforces the same thing with a trigger
(`0004_contact_notes.sql`), because a guarantee that lives only in Python is a
guarantee about one process rather than about the record.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from src.records.models import POLICY_NO_RE

import re

CN_REF_RE = re.compile(r"^CN-\d{10}$")


@dataclass(frozen=True)
class ContactNote:
    """One note written against one contact, about one policy."""

    cn_ref: str
    policy_no: str
    body: str
    author: str
    written_at: str
    corrects_id: Optional[int] = None
    note_id: Optional[int] = None

    def __post_init__(self) -> None:
        if not CN_REF_RE.match(self.cn_ref):
            raise ValueError(
                f"cn_ref {self.cn_ref!r} is not CN- plus ten digits")
        if not POLICY_NO_RE.match(self.policy_no):
            raise ValueError(
                f"policy_no {self.policy_no!r} does not match the reference "
                "grammar")
        if not self.body.strip():
            raise ValueError("a note body cannot be blank — a note with "
                             "nothing in it is not a record of anything")
        if not self.author.strip():
            raise ValueError("a note needs an author somebody can be held to")

    def as_dict(self) -> dict:
        """Everything needed to rebuild this note, and nothing else."""
        return {
            "cn_ref": self.cn_ref,
            "policy_no": self.policy_no,
            "body": self.body,
            "author": self.author,
            "written_at": self.written_at,
            "corrects_id": self.corrects_id,
            "note_id": self.note_id,
        }


class NoteLog:
    """An append-only log of contact notes.

    Offers exactly one way to change anything — ``record`` — because that is the
    whole point. There is no update, no edit and no delete, here or in the table.
    """

    def __init__(self) -> None:
        self._notes: list[ContactNote] = []

    def __len__(self) -> int:
        return len(self._notes)

    def record(self, note: ContactNote) -> ContactNote:
        """Append ``note``, numbering it, and hand back what was stored."""
        if note.corrects_id is not None and not any(
                n.note_id == note.corrects_id for n in self._notes):
            raise ValueError(
                f"this note corrects #{note.corrects_id}, which does not "
                "exist — a correction has to point at something")
        stored = replace(note, note_id=len(self._notes) + 1)
        self._notes.append(stored)
        return stored

    def all(self) -> tuple[ContactNote, ...]:
        """Every note, oldest first."""
        return tuple(self._notes)

    def for_contact(self, cn_ref: str) -> tuple[ContactNote, ...]:
        """This contact's notes, in the order they were written."""
        return tuple(n for n in self._notes if n.cn_ref == cn_ref)

    def for_policy(self, policy_no: str) -> tuple[ContactNote, ...]:
        """Every note ever written about this policy, oldest first."""
        return tuple(n for n in self._notes if n.policy_no == policy_no)
