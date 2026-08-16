"""`world/load/verify.py` — the database is checkable after the fact.

The claim "the database holds the approved world" must be checkable by
somebody who was not there when it was loaded. The verify command projects
the committed world into the same shape the loader writes, snapshots the
live tables, and reports **every difference by name** — a missing row, an
extra row, a field that moved. A verify that only counted would pass an
edited amount; this one reads the fields.

Offline, the projection and the comparison are pure functions, so tampering
is simulated on a snapshot copy. The live proof — a clean load verifies, a
row UPDATEd behind the system's back is caught and named — runs in the
integration half below.
"""

import copy
import dataclasses

import pytest

from world.load.expected import project
from world.load.verify import compare

AS_OF = "2026-07-28"


@pytest.fixture
def small_world(tiny_world):
    return dataclasses.replace(
        tiny_world,
        people=[{"party_id": "PH-0001", "name": "Theta Meridian 12",
                 "dob": "1954-02-11", "registered_address": "14 Lattice Way",
                 "contact": {"phone": "07700 900101",
                             "email": "ph-0001@example.org",
                             "registered": True}},
                {"party_id": "PH-0002", "name": "Argon Basalt 27",
                 "dob": "1961-04-08", "registered_address": "3 Weir Court",
                 "contact": {}}],
        stories=({"kind": "note", "policy_no": "LP-20000137",
                  "ref": "CN-2000013701", "text": "Rang for a value."},
                 {"kind": "narrative", "policy_no": "LP-20000137",
                  "ref": "CW-300000001", "text": "Raised off the call."}))


# ── clean is clean ───────────────────────────────────────────────────────


def test_a_faithful_snapshot_verifies_with_no_differences(small_world):
    snapshot = project(small_world)
    assert compare(small_world, snapshot) == ()


def test_the_projection_carries_the_prose_and_the_value(small_world):
    snapshot = project(small_world)
    assert snapshot["notes"]["CN-2000013701"]["body"] == "Rang for a value."
    assert snapshot["narratives"]["CW-300000001"]["body"] == \
        "Raised off the call."
    assert snapshot["values"]["LP-20000137"] == 400_00


# ── every kind of difference is named ────────────────────────────────────


def test_a_field_moved_behind_the_systems_back_is_named(small_world):
    snapshot = project(small_world)
    tampered = copy.deepcopy(snapshot)
    tampered["policies"]["LP-20000137"]["status"] = "surrendered"

    problems = compare(small_world, tampered)
    assert len(problems) == 1
    assert "LP-20000137" in problems[0] and "status" in problems[0]
    assert "surrendered" in problems[0]


def test_an_edited_amount_is_named_not_just_counted(small_world):
    snapshot = project(small_world)
    tampered = copy.deepcopy(snapshot)
    tampered["transactions"][("LP-20000137", 2)]["amount_pence"] += 1
    tampered["values"]["LP-20000137"] -= 1

    problems = compare(small_world, tampered)
    named = " ".join(problems)
    assert "TXN-LP-20000137-2" in named or "LP-20000137" in named
    assert any("amount_pence" in problem for problem in problems)
    assert any("value" in problem for problem in problems)


def test_a_missing_note_is_a_named_absence(small_world):
    snapshot = project(small_world)
    tampered = copy.deepcopy(snapshot)
    del tampered["notes"]["CN-2000013701"]

    problems = compare(small_world, tampered)
    assert any("CN-2000013701" in problem and "missing" in problem
               for problem in problems)


def test_a_row_the_dataset_never_wrote_is_a_named_stranger(small_world):
    snapshot = project(small_world)
    tampered = copy.deepcopy(snapshot)
    tampered["cases"]["CW-999999999"] = dict(
        tampered["cases"]["CW-300000001"])

    problems = compare(small_world, tampered)
    assert any("CW-999999999" in problem and "not in the dataset" in problem
               for problem in problems)


def test_a_tampered_queue_case_is_caught_too(small_world):
    from world.load.queue import open_queue
    from datetime import date

    rows = open_queue(small_world, as_of=date(2026, 7, 28), seed=7, count=1)
    world = dataclasses.replace(small_world, queue=tuple(rows))
    snapshot = project(world)
    tampered = copy.deepcopy(snapshot)
    tampered["cases"][rows[0]["cw_ref"]]["priority"] = "low"

    problems = compare(world, tampered)
    assert any(rows[0]["cw_ref"] in problem and "priority" in problem
               for problem in problems)


# ── against the real database ────────────────────────────────────────────


@pytest.mark.integration
class TestAgainstLivePostgres:
    """Opt-in. A clean load verifies; a row altered directly in the database
    is detected and named — proven by altering one, not by reasoning."""

    SCHEMA = "calmline_verify_selftest"
    # LP-20000137 carries contacts and notes; LP-20000959 carries a case, a
    # narrative and exactly one evidence item — between them every table the
    # tampering below touches is guaranteed occupied.
    SUBSET = frozenset({"LP-20000137", "LP-20000959"})

    def test_clean_load_verifies_and_a_direct_update_is_caught(self):
        import asyncio

        async def scenario():
            from scripts.migrate import apply_migrations
            from world.dataset import DEFAULT_ROOT, read_world
            from world.load import load_world
            from world.load.verify import verify_world

            from src.config import MissingConfigError, load_config
            try:
                config = load_config()
            except MissingConfigError:
                pytest.skip("no live DATABASE_URL")
            import asyncpg

            conn = await asyncpg.connect(config.DATABASE_URL,
                                         statement_cache_size=0)
            try:
                await conn.execute(
                    f"drop schema if exists {self.SCHEMA} cascade")
                await conn.execute(f"create schema {self.SCHEMA}")
                await conn.execute(
                    f"set search_path to {self.SCHEMA}, public, extensions")
                await apply_migrations(conn, out=lambda line: None)

                world = read_world(DEFAULT_ROOT)
                await load_world(conn, world, only=self.SUBSET,
                                 out=lambda line: None)

                clean = await verify_world(conn, world, only=self.SUBSET,
                                           out=lambda line: None)
                assert clean == ()

                # values the committed world cannot already hold: LP-20000137
                # is lapsed in the file, and the world's evidence only ever
                # says yes or no. LP-20000959's case carries exactly one
                # evidence item, so the second edit is guaranteed a row.
                await conn.execute(
                    "update policies set status = 'in_force' "
                    "where policy_no = 'LP-20000137'")
                await conn.execute(
                    "update evidence set satisfies = 'unverifiable' "
                    "where policy_no = 'LP-20000959'")

                problems = await verify_world(conn, world, only=self.SUBSET,
                                              out=lambda line: None)
                named = " ".join(problems)
                assert "LP-20000137" in named and "status" in named
                assert "satisfies" in named
            finally:
                await conn.execute(
                    f"drop schema if exists {self.SCHEMA} cascade")
                await conn.close()

        asyncio.run(scenario())
