"""The world written down — the format, and what it promises.

The card's done-when, minus the refusals, which are their own file because they
are their own subject:

- a world written and read back is **identical to the one generated**
- the manifest's counts **match the file contents**

Plus the two properties that make a file worth having at all: writing twice
produces the same bytes, and phase 1's people file is **carried, not
regenerated** (correction 4 — it is reviewed and committed, and its as-of date
is a separate recorded input rather than the world's birth date).

``world_book`` and ``tiny_world`` are session fixtures in ``conftest.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

from world.dataset import World, read_world, write_world

SEED = 11


# ── the world written and read back ──────────────────────────────────────
def test_a_world_written_and_read_back_is_identical(tmp_path: Path, world_book):
    """The whole claim of task 0, on the real two hundred."""
    written = World.of(world_book, seed=SEED)
    write_world(written, tmp_path)
    assert read_world(tmp_path) == written


def test_the_tiny_world_round_trips_every_field(tmp_path: Path, tiny_world):
    """Every shape the format carries, including the ones the real book uses
    rarely — a held mandate, a change history, evidence against a requirement."""
    write_world(tiny_world, tmp_path)
    assert read_world(tmp_path) == tiny_world


def test_writing_twice_produces_byte_identical_files(tmp_path: Path, world_book):
    """Determinism is the whole reason the world is a file rather than a run."""
    first, second = tmp_path / "a", tmp_path / "b"
    write_world(World.of(world_book, seed=SEED), first)
    write_world(World.of(world_book, seed=SEED), second)
    for name in ("policies.jsonl", "manifest.json", "stories.jsonl"):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_the_people_file_is_copied_not_regenerated(tmp_path: Path, world_book):
    """Phase 1's file is reviewed and committed. The dataset carries it
    byte-for-byte or it is not the same world (correction 4)."""
    source = Path("data/world/people.jsonl").read_bytes()
    write_world(World.of(world_book, seed=SEED), tmp_path)
    assert (tmp_path / "people.jsonl").read_bytes() == source


# ── the manifest ─────────────────────────────────────────────────────────
def test_the_manifest_carries_the_worlds_birth_date(tmp_path: Path, tiny_world):
    """`2026-07-28`, and never the wall clock. A dataset whose birth date is not
    written down is one that shifts the next time anything runs."""
    write_world(tiny_world, tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["world_birth_date"] == "2026-07-28"


def test_the_manifest_records_the_people_files_own_as_of(tmp_path: Path,
                                                         tiny_world):
    """Three days earlier than the birth date, and recorded as the separate
    input it is rather than quietly conflated with it (correction 4)."""
    write_world(tiny_world, tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["people_as_of"] == "2026-07-25"
    assert manifest["people_as_of"] != manifest["world_birth_date"]


def test_the_manifest_carries_every_seed(tmp_path: Path, tiny_world):
    write_world(tiny_world, tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["seeds"]["book"] == SEED


def test_the_manifests_counts_match_the_file_contents(tmp_path: Path, world_book):
    """Counted from what was actually written, never asserted alongside it."""
    write_world(World.of(world_book, seed=SEED), tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    lines = (tmp_path / "policies.jsonl").read_text().splitlines()
    assert manifest["counts"]["policies"] == len(lines) == 200
    assert manifest["counts"]["people"] == 299
    assert manifest["counts"]["movements"] == sum(
        len(json.loads(line)["entries"]) for line in lines)


def test_the_stories_file_is_written_and_empty(tmp_path: Path, world_book):
    """Phase 4 fills it. Present and empty, rather than absent — a reader that
    tolerates a missing file cannot tell "not written yet" from "lost"."""
    write_world(World.of(world_book, seed=SEED), tmp_path)
    assert (tmp_path / "stories.jsonl").read_text() == ""
    assert json.loads((tmp_path / "manifest.json").read_text())["counts"][
        "stories"] == 0


def test_no_movement_is_dated_after_the_worlds_birth_date(tmp_path: Path,
                                                          world_book):
    write_world(World.of(world_book, seed=SEED), tmp_path)
    for line in (tmp_path / "policies.jsonl").read_text().splitlines():
        for entry in json.loads(line)["entries"]:
            assert entry["at"][:10] <= "2026-07-28"


def test_every_policys_value_survives_the_round_trip_to_the_penny(
        tmp_path: Path, world_book):
    """The reason the format keeps whole entries rather than a stored balance:
    value is a fold over movements on both sides of the file."""
    write_world(World.of(world_book, seed=SEED), tmp_path)
    read_back = {p.policy_no: p.value_pence for p in read_world(tmp_path).policies}
    assert read_back == {p.policy_no: p.value_pence for p in world_book.policies}
