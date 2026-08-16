"""Inventing people from reserved ranges.

The only place in the entire system where a person is invented. Deterministic:
the same seed and the same injected as-of date produce the same people forever.

    python -m world.identities --seed 11 --as-of 2026-07-25
"""

from __future__ import annotations

import json
from pathlib import Path

from world.identities.people import (
    ADVISER,
    ADVISER_FIRM,
    ATTORNEY,
    DEPUTY,
    PERSON_ROLES,
    PERSONAL_REPRESENTATIVE,
    POLICYHOLDER,
    TRUSTEE,
    generate_identities,
)

__all__ = [
    "ADVISER", "ADVISER_FIRM", "ATTORNEY", "DEPUTY", "PERSONAL_REPRESENTATIVE",
    "PERSON_ROLES", "POLICYHOLDER", "TRUSTEE", "generate_identities",
    "write_jsonl",
]


def write_jsonl(records: list[dict], path: "Path | str") -> None:
    """Write the world's people, one JSON object per line.

    Byte-for-byte stable for the same records, because the file is committed
    and read by a person before it becomes data — a rerun that shuffled bytes
    would make the diff unreadable.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=False) + "\n"
                for r in records),
        encoding="utf-8")
