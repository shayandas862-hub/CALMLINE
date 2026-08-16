"""What a rerun must carry across, and the one thing it must never do.

The numbers come back from a seed byte-identically; **the prose and the live
queue do not**. A caller about to write over an existing dataset reads both
from disk first and carries them through — and for the prose, forgetting is
refused rather than forgiven, because hand-written words cannot be
regenerated. The queue is regenerable (run the step again), so it is carried
without a guard: losing it costs a command, not two hundred policies of
writing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from world.dataset.manifest import DatasetError, parse


def _rows(root: Path, name: str) -> tuple:
    path = root / name
    if not path.is_file():
        return ()
    return tuple(json.loads(line) for line
                 in path.read_text(encoding="utf-8").splitlines() if line)


def carried_stories(root: Path) -> tuple:
    """The prose already on disk, for a caller about to write over it.

    Read raw rather than through `read_world`, because the point of asking is
    usually that the rest of the world is being rebuilt and the manifest is
    about to be replaced.
    """
    return _rows(root, "stories.jsonl")


def carried_queue(root: Path) -> tuple:
    """The live work already on disk, carried for the same reason."""
    return _rows(root, "queue.jsonl")


def refuse_to_lose_stories(world: Any, root: Path) -> None:
    """The one thing a rerun must never do.

    Before this guard, `python -m world.dataset` took a `stories.jsonl`
    carrying prose to zero bytes and rebuilt the manifest around the empty
    file — so every count tied, every digest verified, and nothing downstream
    noticed. A world that has quietly lost its stories is worse than one that
    refuses to be written, because only the second is discovered on the day
    it happens.

    Compared on **references**, not on raw lines. Comparing the text refuses a
    file somebody has re-indented or key-ordered differently, which is a false
    alarm on a file that is hand-written by design — and a guard that cries
    wolf on ordinary edits is one that gets removed. What is actually being
    asked is whether any piece of prose would stop existing.
    """
    path = root / "stories.jsonl"
    if not path.is_file():
        return
    existing = [line for line
                in path.read_text(encoding="utf-8").splitlines() if line]
    if not existing:
        return

    keeping = {row.get("ref") for row in world.stories}
    lost = [ref for ref in _refs(existing) if ref not in keeping]
    if lost:
        raise DatasetError(
            f"stories.jsonl already holds prose against {len(existing)} "
            f"references and this world carries {len(world.stories)}, so "
            f"writing it would lose {len(lost)} of them, starting at "
            f"{lost[0]}. Prose is hand-written and cannot be regenerated — "
            f"read the file and carry it, or move it aside deliberately")


def _refs(lines: list[str]) -> list[str]:
    refs = []
    for number, line in enumerate(lines, start=1):
        row = parse(line, f"stories.jsonl line {number}")
        ref = row.get("ref") if isinstance(row, dict) else None
        if not ref:
            raise DatasetError(
                f"stories.jsonl line {number} carries no 'ref', so there is no "
                f"saying whether writing over it would lose anything")
        refs.append(ref)
    return refs
