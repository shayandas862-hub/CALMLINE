#!/usr/bin/env python3
"""Fail the build if any committed file contains a term from the wordlist.

Some terms must never appear anywhere in this repository. The wordlist is
itself kept out of git: locally it lives in a gitignored `.banned-words.local`;
in CI it is supplied through a repository secret. This scanner reads whichever
source is available and greps every tracked text file for a case-insensitive
match, and reports the file but never the matched term — so a failing run is
safe to read in a public build log.

Run directly:  python scripts/check_banned_words.py   (exit 1 on any violation)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Mapping

LOCAL_LIST = ".banned-words.local"
# Never scan these — they legitimately contain the format/placeholder text.
_SELF_FILES = {LOCAL_LIST, ".banned-words.local.example"}


def load_banned_words(
    root: Path | str = ".",
    env: Mapping[str, str] | None = None,
) -> list[str]:
    """Load forbidden names from the local file, else the BANNED_WORDS env var.

    Returns lowercased words with blanks and `#` comments stripped. Returns an
    empty list when no source is configured — the caller decides whether that
    is a warning or a hard failure.
    """
    root = Path(root)
    env = os.environ if env is None else env

    local = root / LOCAL_LIST
    if local.exists():
        return _parse_words(local.read_text(encoding="utf-8").splitlines())

    raw = env.get("BANNED_WORDS")
    if raw:
        return _parse_words(raw.replace(",", "\n").splitlines())

    return []


def _parse_words(lines: Iterable[str]) -> list[str]:
    words = []
    for line in lines:
        word = line.strip().lower()
        if word and not word.startswith("#"):
            words.append(word)
    return words


def find_violations(
    files: Iterable[Path],
    banned_words: Iterable[str],
) -> list[tuple[Path, str]]:
    """Return (path, word) for every file containing a banned word.

    Case-insensitive. Binary and unreadable files are skipped, not fatal.
    """
    lowered = [w.lower() for w in banned_words if w]
    violations: list[tuple[Path, str]] = []
    for path in files:
        try:
            text = Path(path).read_text(encoding="utf-8").lower()
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError, OSError):
            continue
        for word in lowered:
            if word in text:
                violations.append((Path(path), word))
    return violations


def iter_repo_files(root: Path | str = ".") -> list[Path]:
    """Every git-tracked file, minus the banned-words list files themselves."""
    root = Path(root)
    try:
        out = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    files = []
    for rel in out.splitlines():
        if rel.strip() and rel not in _SELF_FILES:
            files.append(root / rel)
    return files


def main() -> int:
    root = Path(".")
    banned = load_banned_words(root=root)
    if not banned:
        print(
            "check-banned-words: no banned-words source configured "
            f"(set {LOCAL_LIST} locally or the BANNED_WORDS secret in CI). "
            "Skipping — enforcement is OFF until configured.",
            file=sys.stderr,
        )
        return 0

    violations = find_violations(iter_repo_files(root), banned)
    if violations:
        print("check-banned-words: wordlist match(es) found:", file=sys.stderr)
        for path, _ in violations:
            # Report the file, never the matched term — it stays out of logs.
            print(f"  - {path}", file=sys.stderr)
        return 1

    print("check-banned-words: clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
