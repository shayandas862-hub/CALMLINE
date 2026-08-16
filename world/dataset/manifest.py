"""The manifest, and the refusal.

**The manifest is what makes the world reproducible and auditable.** It records
the world's birth date, every seed that went into it, the counts, and a digest
per file. A dataset whose birth date is not written down is one that shifts the
next time anything runs; a dataset with no digests is one that cannot tell a
review from an edit.

Two layers of checking, deliberately not one:

- **counts** catch a file that is short — the truncation, the interrupted write.
  They give the better message, because "150 lines, but the manifest records
  200" says what to go and look for.
- **digests** catch a file that is intact but changed. A single digit edited
  leaves every count tying and only the hash disagrees.

Neither is redundant. A count with no digest passes an edit; a digest with no
count says only "this differs", which is true and useless.

The manifest cannot digest itself, so it is checked by shape instead: the fields
it must carry, and the format version it claims. **A reader that guesses at a
format it has never seen is exactly the half-load task 0 exists to prevent**, so
an unknown version is refused rather than attempted.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

# Bumped when the *shape* of the files changes, never when their contents do.
# 2: `queue.jsonl` joins the dataset (v4.5 phase 5) — live work, present while
# empty, the stories.jsonl precedent.
FORMAT_VERSION = 2

# The four files that carry data. `manifest.json` is the fifth and is not in
# this list because it is what the others are checked against.
DATA_FILES = ("people.jsonl", "policies.jsonl", "stories.jsonl", "queue.jsonl")

REQUIRED_KEYS = ("format_version", "world_birth_date", "people_as_of", "seeds",
                 "counts", "files")


class DatasetError(Exception):
    """A world that will not be loaded, and the reason, naming what is wrong.

    Always raised before anything is handed back. A partially-loaded world is
    two hundred policies of which some number are wrong and nothing downstream
    can say which — which is worse than no world at all.
    """


def parse(text: str, where: str) -> Any:
    """JSON, or a refusal that names where the bad line lives."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise DatasetError(f"{where}: not valid JSON — {error.msg}") from error


def digest_of(body: bytes) -> str:
    """The integrity key: sixteen hex characters of SHA-256 over the raw bytes.

    Over bytes rather than over parsed rows, because what is being checked is
    that **this file** is the file that was reviewed — not that it happens to
    parse to something equivalent.
    """
    return hashlib.sha256(body).hexdigest()[:16]


def build_manifest(*, born: str, people_as_of: str, seed: int,
                   bodies: Mapping[str, bytes], movements: int) -> dict[str, Any]:
    """Everything needed to reproduce this world and to prove it arrived whole.

    Counts are taken from the bytes actually written, never asserted alongside
    them — a count computed from the same variable the file was written from
    proves nothing about the file.
    """
    files = {name: {"lines": len(bodies[name].splitlines()),
                    "sha256": digest_of(bodies[name])}
             for name in DATA_FILES}
    return {
        "format_version": FORMAT_VERSION,
        "world_birth_date": born,
        "people_as_of": people_as_of,
        "seeds": {"book": seed},
        "counts": {name.split(".")[0]: files[name]["lines"] for name in DATA_FILES}
                  | {"movements": movements},
        "files": files,
    }


def verify_manifest(manifest: Any) -> None:
    """The manifest's own shape, before anything is checked against it."""
    if not isinstance(manifest, dict):
        raise DatasetError("manifest.json does not hold an object")

    missing = [key for key in REQUIRED_KEYS if key not in manifest]
    if missing:
        raise DatasetError(
            "manifest.json is missing " + ", ".join(repr(k) for k in missing))

    version = manifest["format_version"]
    if version != FORMAT_VERSION:
        raise DatasetError(
            f"manifest.json claims format_version {version}, but this reader "
            f"understands {FORMAT_VERSION} — refusing rather than guessing")


def verify_files(manifest: Mapping[str, Any],
                 bodies: Mapping[str, bytes]) -> None:
    """Every data file against the manifest: its length, then its digest."""
    recorded = manifest["files"]
    counts = manifest["counts"]

    for name in DATA_FILES:
        if name not in recorded:
            raise DatasetError(f"manifest.json records nothing for {name}")

        body = bodies[name]
        lines = len(body.splitlines())
        stem = name.split(".")[0]

        # Counted first: it gives the message somebody can act on.
        for label, expected in (("manifest", recorded[name]["lines"]),
                                (f"counts.{stem}", counts.get(stem))):
            if expected is not None and lines != expected:
                raise DatasetError(
                    f"{name}: {lines} lines, but the {label} records {expected}")

        found = digest_of(body)
        if found != recorded[name]["sha256"]:
            raise DatasetError(
                f"{name}: contents do not match the manifest — recorded "
                f"{recorded[name]['sha256']}, found {found}. The file has been "
                f"edited since the world was written")
