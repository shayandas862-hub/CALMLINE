"""The operational skeleton — where calls and cases sit in time, with no words.

Two modules:

- `shapes`   — what a past contact and a past case are, before anyone writes
  the words. Every contact carries an empty `note_slot` for phase 4 to fill.
- `skeleton` — placing them in time, so the ordering guarantees are provable
  rather than assumed.

**Nothing here generates a sentence.** Intents, outcomes and channels are closed
vocabularies the schema already carries; what anybody actually said is a note,
and notes are phase 4's work, written by hand into a committed file.
"""

from __future__ import annotations

from world.operations.shapes import (
    CASE_TYPES,
    CHANNELS,
    INTENTS,
    OUTCOMES,
    PlannedCase,
    PlannedContact,
    PlannedEvidence,
    PolicyOperations,
)
from world.operations.skeleton import (
    CONTACT_WEIGHTS,
    MONEY_OUT_KINDS,
    REQUIREMENTS,
    contact_distribution,
    plan_operations,
)

__all__ = [
    "CASE_TYPES", "CHANNELS", "CONTACT_WEIGHTS", "INTENTS", "MONEY_OUT_KINDS",
    "OUTCOMES", "PlannedCase", "PlannedContact", "PlannedEvidence",
    "PolicyOperations", "REQUIREMENTS", "contact_distribution",
    "plan_operations",
]
