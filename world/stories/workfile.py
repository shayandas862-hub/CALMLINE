"""What a writing session reads, and what it may append.

**There is deliberately no second copy of the world.** The persisted state is
`stories.jsonl` itself; the work list is derived from it. A workfile holding its
own idea of what has been written is a workfile that can disagree with the prose
sitting beside it, and then neither can be believed.

Three properties, and the third is this phase's own:

- **the brief.** One policy's numbers, dates, events and empty slots — everything
  a writer writes *from*, and nothing invented.
- **the outstanding list.** Which policies still need prose, derived by comparing
  the refs in `stories.jsonl` against the refs the policies carry. A policy is
  outstanding until **every** contact and case it holds has been written: half a
  history is a hole in the middle of somebody's file.
- **resuming never destroys.** An append that would overwrite a ref already
  written is refused whole, naming the ref. All of it or none of it, the same
  discipline as the reader's refusal — a partial append leaves prose on disk that
  no session knows it wrote.

`cast_for` is here rather than in `validate.py` because the writer and the
validator must agree on **who may be named on a policy**, and two definitions of
that are one that can drift. The writer reads it to know who exists; the
validator reads it to catch anyone who does not.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from world.dataset.manifest import DatasetError, digest_of

STORIES = "stories.jsonl"
MANIFEST = "manifest.json"

# An authority record's `type` against the role its holder carries in
# `people.jsonl`. An LPA and an EPA are both exercised by an **attorney**; the
# instrument differs, the person's role does not.
AUTHORITY_ROLES = {"LPA": "attorney", "EPA": "attorney", "deputy": "deputy",
                   "PR": "personal_representative"}


@dataclass(frozen=True)
class Cast:
    """Who may be named on one policy, by the role they hold **on it**.

    Being in `people.jsonl` is not enough: a trustee of somebody else's policy
    is a stranger to this one. 115 of the 200 policies have no third party at
    all, so on those the cast is one person and any other name is a failure.
    """

    policy_no: str
    by_role: Mapping[str, tuple[str, ...]]
    # The firm's **name**, not a party id. `AF-` is not a person and has no date
    # of birth; the people it has authorised are the `adviser` party ids above.
    adviser_firm: Optional[str] = None

    @property
    def holder(self) -> str:
        return self.by_role["policyholder"][0]

    @property
    def party_ids(self) -> frozenset[str]:
        return frozenset(pid for ids in self.by_role.values() for pid in ids)

    def roles_of(self, party_id: str) -> tuple[str, ...]:
        """Every role this party holds on this policy — empty if none, which is
        what makes "named in the wrong role" answerable."""
        return tuple(role for role, ids in self.by_role.items()
                     if party_id in ids)


@dataclass(frozen=True)
class PolicyWork:
    """One policy, as the writer sees it: the numbers, and the empty slots."""

    policy_no: str
    product: str
    status: str
    start: date
    band: str
    headline_value_pence: int
    holder: Mapping[str, Any]
    cast: Cast
    entries: tuple
    events: tuple
    contacts: tuple
    cases: tuple

    @property
    def pieces(self) -> int:
        """One note per contact, one narrative per case."""
        return len(self.contacts) + len(self.cases)

    @property
    def refs(self) -> tuple[str, ...]:
        return (tuple(c.cn_ref for c in self.contacts)
                + tuple(k.cw_ref for k in self.cases))


# ── the brief ────────────────────────────────────────────────────────────

def cast_for(world: Any, policy_no: str) -> Cast:
    """Who this policy's story may name, and in what role."""
    policy = _policy(world, policy_no)
    by_role: dict[str, tuple[str, ...]] = {
        "policyholder": (policy.holder_party_id,)}

    trust = world.trusts.get(policy_no)
    if trust is not None and trust.trustees:
        by_role["trustee"] = tuple(trust.trustees)

    loa = world.adviser_mandates.get(policy_no)
    if loa is not None and loa.individuals:
        by_role["adviser"] = tuple(loa.individuals)

    for record in world.authorities.get(policy_no, ()):
        role = AUTHORITY_ROLES.get(record.type)
        if role is None:
            raise DatasetError(
                f"{policy_no}: authority {record.authority_id} is of type "
                f"{record.type!r}, which no role in people.jsonl answers to")
        by_role[role] = by_role.get(role, ()) + (record.party_id,)

    return Cast(policy_no=policy_no, by_role=by_role,
                adviser_firm=loa.firm if loa is not None else None)


def work_for(world: Any, policy_no: str) -> PolicyWork:
    """One policy's brief — read this, write its prose, move on."""
    policy = _policy(world, policy_no)
    operations = world.operations.get(policy_no)
    return PolicyWork(
        policy_no=policy_no, product=policy.product, status=policy.status,
        start=policy.start, band=policy.band,
        headline_value_pence=policy.headline_value_pence,
        holder=_person(world, policy.holder_party_id),
        cast=cast_for(world, policy_no),
        entries=policy.entries, events=policy.events,
        contacts=operations.contacts if operations else (),
        cases=operations.cases if operations else ())


def plan_work(world: Any) -> tuple[PolicyWork, ...]:
    """Every policy in the book, in the order the dataset holds them."""
    return tuple(work_for(world, policy.policy_no) for policy in world.policies)


# ── what is left ─────────────────────────────────────────────────────────

def written_refs(world: Any) -> frozenset[str]:
    """Every contact and case reference that already has prose against it."""
    return frozenset(row["ref"] for row in world.stories if "ref" in row)


def outstanding(world: Any) -> tuple[str, ...]:
    """Policy numbers still needing prose. A policy with no contacts is never
    outstanding — eleven get nothing, and a list demanding words for them can
    never empty."""
    done = written_refs(world)
    return tuple(work.policy_no for work in plan_work(world)
                 if work.pieces and not set(work.refs) <= done)


def progress(world: Any) -> tuple[int, int]:
    """``(pieces written, pieces the world needs)``.

    Counted in pieces rather than policies: one policy needing twenty notes and
    one needing a single note are not the same amount of work.
    """
    done = written_refs(world)
    work = plan_work(world)
    return (sum(len(set(w.refs) & done) for w in work),
            sum(w.pieces for w in work))


# ── appending, without ever destroying ───────────────────────────────────

def append_stories(root: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Add prose to `stories.jsonl` and refresh the manifest around it.

    Refuses whole — on a missing ref, or on one already written, whether the
    duplicate is on disk or elsewhere in the same call. Nothing is written
    until every row has passed, because a half-applied append leaves prose
    behind that no session knows it wrote.

    The manifest is refreshed here rather than left to a later step: it is what
    the files are checked against, so an append that skips it leaves a world its
    own reader refuses.
    """
    rows = list(rows)
    path = root / STORIES
    existing = _lines(path)
    seen = {json.loads(line)["ref"] for line in existing}

    encoded = []
    for position, row in enumerate(rows, start=1):
        ref = row.get("ref")
        if not ref:
            raise DatasetError(
                f"{STORIES}: row {position} carries no 'ref', so there is "
                f"nothing to attach it to")
        if ref in seen:
            raise DatasetError(
                f"{STORIES}: {ref} already has prose against it — refusing "
                f"rather than overwriting it. Prose is hand-written and cannot "
                f"be regenerated")
        seen.add(ref)
        encoded.append(json.dumps(row, sort_keys=True))

    body = "".join(line + "\n" for line in existing + encoded).encode("utf-8")
    path.write_bytes(body)
    _refresh_manifest(root, body)


def _refresh_manifest(root: Path, body: bytes) -> None:
    path = root / MANIFEST
    manifest = json.loads(path.read_text(encoding="utf-8"))
    lines = len(body.splitlines())
    manifest["files"][STORIES] = {"lines": lines, "sha256": digest_of(body)}
    manifest["counts"]["stories"] = lines
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def _lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line]


# ── small readers ────────────────────────────────────────────────────────

def _policy(world: Any, policy_no: str) -> Any:
    for policy in world.policies:
        if policy.policy_no == policy_no:
            return policy
    raise DatasetError(f"{policy_no} is not in the book")


def _person(world: Any, party_id: str) -> Mapping[str, Any]:
    for person in world.people:
        if person.get("party_id") == party_id:
            return person
    raise DatasetError(f"{party_id} is not in people.jsonl")
