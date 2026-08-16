"""The world's two hundred policies, read from `data/world/` into a book.

This is the console's book from v4.5 phase 3 onwards. It replaces nothing: the
generator in `synthetic_history` is still there and is still what the suite
builds books with. **The dataset becomes what the console uses; the generator
becomes what tests use.**

**`src/` does not import `world/`.** The world-builder imports the rulebook so
it can check every movement it generates; importing it back would make the
console depend on the builder and ship one with the other. What crosses the line
is the committed *file* — the same arrangement `synthetic_history` already has
with `data/synthetic/policyholders.jsonl`. This module reads bytes and knows
nothing about how they were made.

**Nothing here is asserted; it is all replayed.** Every movement goes through
`apply_transaction`, so the append-only rule, the overdraw refusal and the change
journal apply to the world exactly as they do to a handler's instruction. A world
that could not be replayed through the store is a world the store would not have
allowed, and finding that out at boot is the point.

The manifest is checked before anything is built — counts, then digests. A
console that boots on a truncated book serves wrong policies silently, which is
worse than one that refuses to boot and says why.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator, Optional

from src.records.authorisations import AuthorityRecord
from src.records.models import (
    AdviserLoa,
    Contact,
    Party,
    Policy,
    Transaction,
    Trust,
    VulnerabilityFlag,
)
from src.records.store import InMemoryRecordBook

WORLD_ROOT = Path(__file__).resolve().parents[2] / "data" / "world"

MANIFEST = "manifest.json"
PEOPLE = "people.jsonl"
POLICIES = "policies.jsonl"
QUEUE = "queue.jsonl"
DATA_FILES = (PEOPLE, POLICIES, "stories.jsonl", QUEUE)

# Kept in step with `world/dataset/manifest.py` by
# `test_the_console_reads_exactly_what_the_world_writer_wrote`, which writes
# with one and reads with the other. Sharing the code would mean `src/`
# importing `world/`; sharing a test proves the same thing without the import.
# 2: `queue.jsonl` joined the dataset (v4.5 phase 5).
FORMAT_VERSION = 2
DIGEST_CHARS = 16


class WorldSeedError(Exception):
    """The dataset will not be loaded, and why. Raised before any policy is
    built, so a refused world leaves no half-populated book behind."""


def _digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()[:DIGEST_CHARS]


def read_manifest(root: Path) -> dict:
    """The manifest, verified against the files sitting beside it."""
    path = root / MANIFEST
    if not path.is_file():
        raise WorldSeedError(
            f"{MANIFEST} is missing from {root} — the console will not boot on "
            f"a dataset it cannot check")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise WorldSeedError(f"{MANIFEST}: not valid JSON — {error.msg}") from error

    if manifest.get("format_version") != FORMAT_VERSION:
        raise WorldSeedError(
            f"{MANIFEST} claims format_version {manifest.get('format_version')}, "
            f"but this reader understands {FORMAT_VERSION}")

    for name in DATA_FILES:
        file_path = root / name
        if not file_path.is_file():
            raise WorldSeedError(f"{name} is missing from {root}")
        body = file_path.read_bytes()
        recorded = manifest.get("files", {}).get(name)
        if recorded is None:
            raise WorldSeedError(f"{MANIFEST} records nothing for {name}")

        lines = len(body.splitlines())
        if lines != recorded["lines"]:
            raise WorldSeedError(
                f"{name}: {lines} lines, but the manifest records "
                f"{recorded['lines']}")
        if _digest(body) != recorded["sha256"]:
            raise WorldSeedError(
                f"{name}: contents do not match the manifest — the file has "
                f"been edited since the world was written")
    return manifest


def _rows(root: Path, name: str) -> Iterator[tuple[int, dict]]:
    text = (root / name).read_text(encoding="utf-8")
    for number, line in enumerate(text.splitlines(), start=1):
        try:
            yield number, json.loads(line)
        except json.JSONDecodeError as error:
            raise WorldSeedError(
                f"{name} line {number}: not valid JSON — {error.msg}"
            ) from error


def seed_world(book: Any, *, root: Path = WORLD_ROOT) -> dict:
    """Replay the committed dataset into ``book``. Returns the manifest.

    People before policies, because a policy names its holder and the store
    will not accept one whose party it has never heard of.
    """
    manifest = read_manifest(root)
    born = manifest["world_birth_date"]

    for number, row in _rows(root, PEOPLE):
        _seed_party(book, row, born=born, where=f"{PEOPLE} line {number}")

    for number, row in _rows(root, POLICIES):
        where = f"{POLICIES} line {number}"
        policy_no = row.get("policy_no")
        _seed_policy(book, row, born=born,
                     where=f"{where} {policy_no}" if policy_no else where)
    return manifest


def _seed_party(book: Any, row: dict, *, born: str, where: str) -> None:
    """One person. The twelve adviser **firms** carry no ``party_id`` and are
    not parties — a firm is verified by name and reference, never as a person
    (`05-OPS:5.1`), so seeding one here would put an entity in the book that
    the identity gate could then be asked to verify."""
    if "party_id" not in row:
        return

    contact = row.get("contact") or {}
    flag = row.get("vulnerability_flag")
    try:
        party = Party(
            party_id=row["party_id"], name=row["name"], dob=row["dob"],
            registered_address=row["registered_address"],
            contact=Contact(phone=contact.get("phone", ""),
                            email=contact.get("email", ""),
                            registered=bool(contact.get("registered"))),
            scottish_taxpayer=bool(row.get("scottish_taxpayer")),
            vulnerability_flag=VulnerabilityFlag(
                support_needs_ref=flag["support_needs_ref"],
                category=flag["category"]) if flag else None)
    except (KeyError, ValueError) as error:
        raise WorldSeedError(f"{where}: {error}") from error

    book.add_party(party, actor="world", source_ref="seed",
                   at=f"{born}T00:00:00")


def _seed_policy(book: Any, row: dict, *, born: str, where: str) -> None:
    for key in ("policy_no", "product", "status", "start", "holder_party_id",
                "entries"):
        if key not in row:
            raise WorldSeedError(f"{where}: missing field {key!r}")

    policy_no = row["policy_no"]
    stamp = {"actor": "world", "source_ref": "seed", "at": f"{born}T00:00:00"}
    book.add_policy(Policy(policy_no=policy_no, product=row["product"],
                           status=row["status"], start_date=row["start"],
                           holder_party_id=row["holder_party_id"],
                           bank_last4=_last4(row),
                           trust=_trust(row), adviser_loa=_loa(row)), **stamp)

    # Attorneys, deputies and personal representatives. Held beside the policy
    # rather than on it, because a policy can carry several and each is checked
    # separately at the gate.
    for held in row.get("authorities", ()):
        book.add_authority(AuthorityRecord(
            authority_id=held["authority_id"], policy_no=policy_no,
            party_id=held["party_id"], type=held["type"],
            scope=tuple(held["scope"]), evidence_ref=held["evidence_ref"],
            verified_date=held["verified_date"], status=held["status"]),
            **stamp)

    for entry in row["entries"]:
        try:
            book.apply_transaction(policy_no, Transaction(
                txn_id=entry["txn_id"], policy_no=policy_no, kind=entry["kind"],
                amount_pence=entry["amount_pence"], reason=entry["reason"],
                actor=entry["actor"], at=entry["at"]))
        except KeyError as error:
            raise WorldSeedError(f"{where}: movement missing {error}") from error
        except ValueError as error:
            # The store refused a movement the world claims to have made. That
            # is a fault in the dataset, not a reason to skip the row.
            raise WorldSeedError(f"{where}: {error}") from error


def _last4(row: dict) -> Any:
    mandate = row.get("bank_mandate")
    return mandate["account_last4"] if mandate else None


def _trust(row: dict) -> Optional[Trust]:
    trust = row.get("trust")
    if not trust:
        return None
    return Trust(kind=trust["kind"], executed=trust["executed"],
                 trustees=tuple(trust["trustees"]),
                 registrable=trust["registrable"], urn=trust["urn"])


def _loa(row: dict) -> Optional[AdviserLoa]:
    loa = row.get("adviser_loa")
    if not loa:
        return None
    return AdviserLoa(firm=loa["firm"], frn=loa["frn"],
                      scope=tuple(loa["scope"]), expiry=loa["expiry"],
                      individuals=tuple(loa["individuals"]))


def read_queue(root: Path = WORLD_ROOT) -> "list[dict]":
    """The dataset's live work, manifest-verified, as raw rows.

    Raw dicts rather than `Case` objects, because building a case is the
    casework layer's business and this module's is reading committed bytes
    the manifest vouches for. The book never holds these — open work belongs
    to the queue screen, not to the system of record's history.
    """
    read_manifest(root)
    return [row for _, row in _rows(root, QUEUE)]


def build_world_book(root: Path = WORLD_ROOT) -> InMemoryRecordBook:
    """A book holding the world's two hundred policies and their histories."""
    book = InMemoryRecordBook()
    seed_world(book, root=root)
    return book
