"""Cryptographic freeze for the golden set — the agent may not be tuned to its exam.

Once the cases are confirmed, `freeze()` records a fingerprint per case plus one
over the whole set. `verify_frozen()` recomputes and raises if anything moved.

**Fingerprints are per CASE, keyed by id, not per file byte.** Three things fall
out of that and all three matter: reordering the file is not a modification (the
set is a set), the error names *which* case changed rather than just saying the
digest moved, and `06-RAGOPS §3.0`'s **append-only** rule becomes checkable
rather than aspirational.

Two verifications, because there are two different rules:

  * `verify_frozen`    — nothing changed at all, additions included. Answers
                         "is this exactly the set the baseline scored?"
  * `verify_grow_only` — no frozen case was edited or removed; additions pass.
                         Answers "has anyone been tuning the exam?"

Growing the set is legitimate — production failures become new cases. Quietly
rewording a case the agent keeps failing is not, and neither is deleting it.

**This module used to glob `*.json`.** The six-tier set is one `.jsonl` file, so
the freeze would have hashed zero files, recorded the digest of nothing, and
verified forever against anything (D-CL-092). A freeze that cannot detect a
change is worse than none, because it is reported as protection.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

FINGERPRINT_FILE = "FROZEN.sha256"


class FrozenSetModified(Exception):
    """Raised when the golden set no longer matches its recorded fingerprint."""


def _fingerprint_path(golden_path: Path | str) -> Path:
    return Path(golden_path).parent / FINGERPRINT_FILE


def case_fingerprints(golden_path: Path | str) -> dict[str, str]:
    """One SHA-256 per case, keyed by id, over its canonical JSON.

    Canonicalised (sorted keys, no incidental whitespace) so that reformatting
    the file is not mistaken for editing the exam.
    """
    prints: dict[str, str] = {}
    for line in Path(golden_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        canonical = json.dumps(case, sort_keys=True, ensure_ascii=False)
        prints[case["id"]] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return prints


def compute_fingerprint(golden_path: Path | str) -> str:
    """One digest over the whole set — every case id and its fingerprint, sorted."""
    prints = case_fingerprints(golden_path)
    digest = hashlib.sha256()
    for case_id in sorted(prints):
        digest.update(f"{case_id}:{prints[case_id]}".encode("utf-8"))
    return digest.hexdigest()


def freeze(golden_path: Path | str) -> str:
    """Record the set fingerprint and every case's. Returns the set fingerprint.

    The per-case lines are what make the failure message useful and the
    append-only check possible; they also make a re-freeze readable in a diff,
    which is the point of requiring it to be a visible commit.
    """
    prints = case_fingerprints(golden_path)
    overall = compute_fingerprint(golden_path)
    body = [overall] + [f"{case_id} {prints[case_id]}" for case_id in sorted(prints)]
    _fingerprint_path(golden_path).write_text("\n".join(body) + "\n", encoding="utf-8")
    return overall


def read_fingerprint(golden_path: Path | str) -> str | None:
    """The recorded set fingerprint, or ``None`` if the set has never been frozen."""
    path = _fingerprint_path(golden_path)
    if not path.exists():
        return None
    first = path.read_text(encoding="utf-8").splitlines()
    return first[0].strip() if first else None


def read_case_fingerprints(golden_path: Path | str) -> dict[str, str]:
    """The recorded per-case fingerprints, or empty if the set has never been frozen."""
    path = _fingerprint_path(golden_path)
    if not path.exists():
        return {}
    recorded: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        if line.strip():
            case_id, _, digest = line.partition(" ")
            recorded[case_id] = digest.strip()
    return recorded


def _require_frozen(golden_path: Path | str) -> str:
    recorded = read_fingerprint(golden_path)
    if recorded is None:
        raise FrozenSetModified(
            f"{golden_path} has no {FINGERPRINT_FILE} — not frozen")
    return recorded


def verify_frozen(golden_path: Path | str) -> None:
    """Raise unless the set is byte-for-byte the one that was frozen."""
    recorded = _require_frozen(golden_path)
    actual = compute_fingerprint(golden_path)
    if actual == recorded:
        return
    raise FrozenSetModified(
        "golden set changed since it was frozen — "
        f"{_describe(golden_path)}. If this is intentional, re-freeze "
        "deliberately: `python scripts/freeze_goldens.py freeze`.")


def verify_grow_only(golden_path: Path | str) -> None:
    """Raise if any frozen case was edited or removed. Additions are allowed.

    `06-RAGOPS §3.0`: the set is append-only. Adding a case that a production
    failure taught you is the set working; editing or deleting one the agent
    keeps failing is tuning the exam to the candidate.
    """
    _require_frozen(golden_path)
    recorded = read_case_fingerprints(golden_path)
    current = case_fingerprints(golden_path)

    removed = sorted(set(recorded) - set(current))
    edited = sorted(case_id for case_id, digest in recorded.items()
                    if case_id in current and current[case_id] != digest)
    if not removed and not edited:
        return
    parts = []
    if edited:
        parts.append(f"edited: {', '.join(edited)}")
    if removed:
        parts.append(f"removed: {', '.join(removed)}")
    raise FrozenSetModified(
        "the golden set is append-only and frozen cases changed — "
        + "; ".join(parts)
        + ". The agent must not be tuned to pass its own exam.")


def _describe(golden_path: Path | str) -> str:
    """What actually moved, for the error message."""
    recorded = read_case_fingerprints(golden_path)
    current = case_fingerprints(golden_path)
    added = sorted(set(current) - set(recorded))
    removed = sorted(set(recorded) - set(current))
    edited = sorted(case_id for case_id, digest in recorded.items()
                    if case_id in current and current[case_id] != digest)
    parts = [f"{label}: {', '.join(ids)}"
             for label, ids in (("edited", edited), ("added", added),
                                ("removed", removed)) if ids]
    return "; ".join(parts) if parts else "the set digest moved"
