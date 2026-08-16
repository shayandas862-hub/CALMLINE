#!/usr/bin/env python3
"""Freeze or verify the six-tier golden set.

    python scripts/freeze_goldens.py freeze     # record FROZEN.sha256 (a deliberate, visible commit)
    python scripts/freeze_goldens.py verify     # exit 1 if the set drifted from its fingerprint
    python scripts/freeze_goldens.py grow-only  # exit 1 only if a frozen case was edited or removed

`verify` is the strict check — additions included — and answers "is this exactly
the set the baseline scored?". `grow-only` enforces `06-RAGOPS §3.0`'s
append-only rule: new cases are how the set learns from production failures,
while editing or deleting one the agent keeps failing is tuning the exam to the
candidate.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.evals.freeze import (FrozenSetModified, case_fingerprints, freeze,  # noqa: E402
                              verify_frozen, verify_grow_only)

GOLDEN_PATH = (Path(__file__).resolve().parent.parent
               / "data" / "golden" / "golden_evals.jsonl")


def main(argv: list[str]) -> int:
    action = argv[1] if len(argv) > 1 else "verify"
    if action == "freeze":
        fingerprint = freeze(GOLDEN_PATH)
        n = len(case_fingerprints(GOLDEN_PATH))
        print(f"golden set frozen · {n} cases · {fingerprint[:16]}…")
        return 0
    if action in ("verify", "grow-only"):
        check = verify_frozen if action == "verify" else verify_grow_only
        try:
            check(GOLDEN_PATH)
        except FrozenSetModified as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        print(f"golden set passes {action}.")
        return 0
    print(f"unknown action {action!r}; use 'freeze', 'verify' or 'grow-only'",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
