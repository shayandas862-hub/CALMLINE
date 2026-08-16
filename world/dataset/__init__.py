"""The world, written down — and a reader that refuses what it does not understand.

Five files, and the world is all five of them together:

    people.jsonl     everyone, exactly as phase 1 wrote them
    policies.jsonl   the two hundred, each with its whole history
    stories.jsonl    the prose. Written in phase 4; hand-made, irreplaceable
    queue.jsonl      live work. Present while empty; refreshed by its own step
    manifest.json    the birth date, the seeds, the counts and the digests

**Why files rather than a database first.** The world has to be read and approved
before it becomes data. A file can be opened, diffed and reviewed by a person; a
table cannot. It is also what lets an outside reviewer confirm nobody real is in
the data without running anything.

**Why the reader refuses instead of coping.** A half-loaded world is two hundred
policies of which some number are wrong, and nothing downstream can say which.
Every check here fails the whole read, names the file, and says what did not add
up. There is no partial success.

`people.jsonl` is **carried, not regenerated** (correction 4). It was reviewed
and committed in phase 1 and its as-of date is three days earlier than the
world's birth date — a separate recorded input, not a stale copy of it. That is
why this module re-serialises it with JSON's default separators and no key
sorting, which reproduces phase 1's bytes exactly, while `policies.jsonl` is
written sorted: one is being preserved, the other is being created.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

from src.records.authorisations import BankMandate
from world import PEOPLE_AS_OF, WORLD_BIRTH_DATE
from world.dataset.carry import (
    carried_queue,
    carried_stories,
    refuse_to_lose_stories,
)
from world.dataset.manifest import (
    DATA_FILES,
    DatasetError,
    build_manifest,
    parse,
    verify_files,
    verify_manifest,
)
from world.dataset.queue_rows import validate_queue_row
from world.dataset.rows import decode_policy, encode_policy
from world.operations.shapes import PolicyOperations

MANIFEST = "manifest.json"
DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "data" / "world"

__all__ = ["DEFAULT_ROOT", "DatasetError", "World", "carried_queue",
           "carried_stories", "read_world", "write_world"]


@dataclass(frozen=True)
class World:
    """Everything the dataset holds, in memory. Compared by value, so a world
    read back from files either equals the one written or does not."""

    policies: tuple
    bank_mandates: dict[str, BankMandate]
    operations: dict[str, PolicyOperations]
    people: list[dict]
    memorable_holders: tuple[str, ...]
    seed: int
    born: date = WORLD_BIRTH_DATE
    people_as_of: date = PEOPLE_AS_OF
    stories: tuple = ()
    trusts: dict = field(default_factory=dict)
    adviser_mandates: dict = field(default_factory=dict)
    authorities: dict = field(default_factory=dict)
    queue: tuple = ()

    @classmethod
    def of(cls, book: Any, *, seed: int, born: date = WORLD_BIRTH_DATE,
           people_as_of: date = PEOPLE_AS_OF, stories: tuple = (),
           queue: tuple = ()) -> "World":
        """The world as `build_book` left it, plus the people it refers to.

        `stories` and `queue` must be **passed in**, because the builder does
        not produce them and never will: the numbers come back from a seed,
        the prose and the live work do not. A caller regenerating over an
        existing dataset carries both across; one that forgets the prose is
        refused by `write_world` rather than quietly emptying the file.
        """
        from world.lifetimes.build import load_people

        return cls(policies=book.policies, bank_mandates=book.bank_mandates,
                   operations=book.operations, people=load_people(),
                   memorable_holders=book.memorable_holders, seed=seed,
                   born=born, people_as_of=people_as_of, stories=stories,
                   trusts=dict(book.trusts),
                   adviser_mandates=dict(book.adviser_mandates),
                   authorities=dict(book.authorities), queue=queue)

    @property
    def movements(self) -> int:
        return sum(len(policy.entries) for policy in self.policies)


# ── writing ──────────────────────────────────────────────────────────────

def write_world(world: World, root: Path) -> None:
    """Write all five files. Deterministic — same world, same bytes, always."""
    root.mkdir(parents=True, exist_ok=True)
    refuse_to_lose_stories(world, root)

    bodies = {
        # Default separators and insertion order: this reproduces phase 1's
        # committed file byte-for-byte, which `sort_keys` would not.
        "people.jsonl": _jsonl(world.people, sort_keys=False),
        "policies.jsonl": _jsonl(
            [encode_policy(
                policy, world.bank_mandates.get(policy.policy_no),
                world.operations.get(policy.policy_no),
                trust=world.trusts.get(policy.policy_no),
                adviser_loa=world.adviser_mandates.get(policy.policy_no),
                authorities=world.authorities.get(policy.policy_no, ()))
             for policy in world.policies], sort_keys=True),
        "stories.jsonl": _jsonl(list(world.stories), sort_keys=True),
        "queue.jsonl": _jsonl(list(world.queue), sort_keys=True),
    }
    for name, body in bodies.items():
        (root / name).write_bytes(body)

    manifest = build_manifest(born=world.born.isoformat(),
                              people_as_of=world.people_as_of.isoformat(),
                              seed=world.seed, bodies=bodies,
                              movements=world.movements)
    manifest["memorable_holders"] = list(world.memorable_holders)
    (root / MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _jsonl(rows: list, *, sort_keys: bool) -> bytes:
    return "".join(json.dumps(row, sort_keys=sort_keys) + "\n"
                   for row in rows).encode("utf-8")


# ── reading ──────────────────────────────────────────────────────────────

def read_world(root: Path) -> World:
    """Read all five files, or refuse the lot. Never a partial world."""
    manifest = _read_manifest(root)
    verify_manifest(manifest)

    bodies = {}
    for name in DATA_FILES:
        path = root / name
        if not path.is_file():
            raise DatasetError(f"{name} is missing from {root}")
        bodies[name] = path.read_bytes()
    verify_files(manifest, bodies)

    born = date.fromisoformat(manifest["world_birth_date"])
    policies, mandates, operations = [], {}, {}
    trusts, loas, authorities = {}, {}, {}
    for number, line in enumerate(bodies["policies.jsonl"].decode().splitlines(),
                                  start=1):
        where = f"policies.jsonl line {number}"
        row = parse(line, where)
        built, mandate, ops, (trust, loa, held) = decode_policy(row, where)
        _reconcile(built, born)
        policies.append(built)
        if mandate is not None:
            mandates[built.policy_no] = mandate
        operations[built.policy_no] = ops
        if trust is not None:
            trusts[built.policy_no] = trust
        if loa is not None:
            loas[built.policy_no] = loa
        if held:
            authorities[built.policy_no] = held

    people = [parse(line, f"people.jsonl line {number}") for number, line
              in enumerate(bodies["people.jsonl"].decode().splitlines(), start=1)]
    stories = tuple(parse(line, f"stories.jsonl line {number}") for number, line
                    in enumerate(bodies["stories.jsonl"].decode().splitlines(),
                                 start=1))
    queue = _read_queue(bodies["queue.jsonl"], policies, operations)

    return World(policies=tuple(policies), bank_mandates=mandates,
                 operations=operations, people=people,
                 memorable_holders=tuple(manifest.get("memorable_holders", ())),
                 seed=manifest["seeds"]["book"], born=born,
                 people_as_of=date.fromisoformat(manifest["people_as_of"]),
                 stories=stories, trusts=trusts, adviser_mandates=loas,
                 authorities=authorities, queue=queue)


def _read_queue(body: bytes, policies: list, operations: dict) -> tuple:
    """The live work, held to the same standard as everything else: every row
    names a policy the book holds, carries an open status, and takes a
    reference nothing in history or the queue already owns."""
    policy_nos = {policy.policy_no for policy in policies}
    taken = {case.cw_ref for ops in operations.values() for case in ops.cases}
    rows = []
    for number, line in enumerate(body.decode().splitlines(), start=1):
        where = f"queue.jsonl line {number}"
        row = parse(line, where)
        validate_queue_row(row, policies=policy_nos, taken=taken, where=where)
        taken.add(row["cw_ref"])
        rows.append(row)
    return tuple(rows)


def _read_manifest(root: Path) -> Any:
    path = root / MANIFEST
    if not path.is_file():
        raise DatasetError(
            f"{MANIFEST} is missing from {root} — without it there is no birth "
            f"date, no seeds and nothing to check the other files against")
    return parse(path.read_text(encoding="utf-8"), MANIFEST)


def _reconcile(policy: Any, born: date) -> None:
    """Two properties every row must hold on its own, checked as it is read.

    The ledger is re-folded rather than trusted: a row carrying both its
    movements and the balances they left behind is a row that can disagree with
    itself, and value is a fold over movements everywhere else in the system.
    """
    balance = 0
    for entry in policy.entries:
        balance += entry.transaction.signed_pence
        if balance != entry.balance_after_pence:
            raise DatasetError(
                f"{policy.policy_no}: movement {entry.seq} leaves "
                f"{entry.balance_after_pence} pence, but its own movements reach "
                f"{balance}")
        if entry.transaction.at[:10] > born.isoformat():
            raise DatasetError(
                f"{policy.policy_no}: movement {entry.seq} is dated "
                f"{entry.transaction.at[:10]}, after the world's birth date of "
                f"{born.isoformat()}")
