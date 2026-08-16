"""The shape a story must take, and the refusal when it does not.

**Rejected and reported, never patched** — phase 2's discipline for a refused
movement, applied to prose. A story quietly repaired is one whose text no longer
describes the contact it hangs off, and nothing downstream can say which ones
those are. Every refusal names the row, the reference and what did not add up,
because "stories.jsonl is wrong" is not something anybody can act on.

A story is four fields and no more. It carries **no date, no channel and no
outcome**: those are already on the contact, and a second copy is a copy that can
disagree. What the story adds is the one thing the skeleton has none of — the
words.

The reference grammars are imported rather than restated. `CN-` and `CW-` are
enforced on the way into the running system already, and a second regular
expression here is one that can drift from the one that matters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from src.casework.models import CW_REF_RE
from src.records.interactions import CN_REF_RE
from world.dataset.manifest import DatasetError
from world.operations.shapes import INTENTS, OUTCOMES

KINDS = ("note", "narrative")
FIELDS = ("policy_no", "ref", "kind", "text")

# `intent` and `outcome` are closed categories, not sentences. A note carrying
# one verbatim was filled in rather than written — and the underscore is what
# makes this checkable without touching ordinary English, which uses the same
# words constantly and must be able to.
CATEGORY_TOKENS = tuple(sorted(
    {token for token in INTENTS + OUTCOMES if "_" in token}))


@dataclass(frozen=True)
class Story:
    """One piece of prose, tied to the one thing it is about."""

    policy_no: str
    ref: str
    kind: str
    text: str


def parse_story(row: Mapping[str, Any], world: Any, where: str) -> Story:
    """One story, checked against the world it claims to belong to."""
    if not isinstance(row, Mapping):
        raise DatasetError(f"{where}: a story must be an object")

    for field in FIELDS:
        if field not in row:
            raise DatasetError(f"{where}: missing field {field!r}")

    kind = row["kind"]
    if kind not in KINDS:
        raise DatasetError(
            f"{where}: {kind!r} is not a kind of story — expected one of "
            f"{', '.join(KINDS)}")

    text = row["text"]
    if not isinstance(text, str) or not text.strip():
        raise DatasetError(f"{where}: the prose is empty, so there is nothing "
                           f"to attach to {row['ref']}")

    leaked = [token for token in CATEGORY_TOKENS if token in text]
    if leaked:
        raise DatasetError(
            f"{where}: the prose carries the category {leaked[0]!r} verbatim. "
            f"Those are closed vocabularies, not sentences — write what was "
            f"actually said")

    _check_reference(row, world, where)
    return Story(policy_no=row["policy_no"], ref=row["ref"], kind=kind,
                 text=text)


def parse_queue(rows: Iterable[Mapping[str, Any]], world: Any,
                where: str = "stories.jsonl") -> tuple[Story, ...]:
    """Every story, or none of them — naming the row that failed."""
    stories, seen = [], set()
    for number, row in enumerate(rows, start=1):
        at = f"{where} line {number}"
        story = parse_story(row, world, at)
        if story.ref in seen:
            raise DatasetError(
                f"{at}: {story.ref} already has prose earlier in this batch — "
                f"one note per contact, one narrative per case")
        seen.add(story.ref)
        stories.append(story)
    return tuple(stories)


# ── the reference, and the policy it must belong to ──────────────────────

def _check_reference(row: Mapping[str, Any], world: Any, where: str) -> None:
    ref, kind, policy_no = row["ref"], row["kind"], row["policy_no"]
    pattern = CN_REF_RE if kind == "note" else CW_REF_RE
    expected = "CN-" if kind == "note" else "CW-"

    if not isinstance(ref, str) or not pattern.match(ref):
        raise DatasetError(
            f"{where}: {ref!r} is not a {expected} reference, so it is not "
            f"something a {kind} can be written against")

    operations = world.operations.get(policy_no)
    if operations is None:
        raise DatasetError(
            f"{where}: {policy_no} is not a policy in the book, so {ref} "
            f"cannot belong to it")

    here = ({c.cn_ref for c in operations.contacts} if kind == "note"
            else {k.cw_ref for k in operations.cases})
    if ref in here:
        return

    # Real reference, wrong file — the mistake a careless writer actually
    # makes, and the one worth naming precisely.
    owner = _owner(world, ref, kind)
    if owner is not None:
        raise DatasetError(
            f"{where}: {ref} belongs to {owner}, not to {policy_no} — a story "
            f"filed against the wrong policy is one nobody will find again")
    raise DatasetError(
        f"{where}: {ref} is not a {'contact' if kind == 'note' else 'case'} "
        f"anywhere in the book")


def _owner(world: Any, ref: str, kind: str) -> Any:
    for policy_no, operations in world.operations.items():
        found = ({c.cn_ref for c in operations.contacts} if kind == "note"
                 else {k.cw_ref for k in operations.cases})
        if ref in found:
            return policy_no
    return None
