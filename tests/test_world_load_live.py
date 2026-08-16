"""The loader against the real database — the proofs that need a live server.

Split from `tests/test_world_load.py` at the 300-line rule. All of it opt-in
(`pytest -m integration`), all of it inside throwaway schemas the tests create
and drop; the default schema is never touched.

Three proofs live here, and each is the specialist verification the phase card
asked for, folded into the suite so it holds forever rather than only on the
day somebody ran it:

- the **append-only triggers actually refuse** an UPDATE and a DELETE, on the
  ledger, the journal, the notes and the narratives — asked of the real
  database, not of the SQL text;
- **foreign keys hold in the load order** — a subset load succeeds with every
  reference satisfied inside its own policy's transaction;
- **a load killed mid-flight leaves every committed policy whole and none
  partial** — proved by SIGKILLing a real subprocess load, not by reasoning.
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts.migrate import apply_migrations
from world.dataset import DEFAULT_ROOT, read_world
from world.load import load_world

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[1]
SCHEMA = "calmline_load_selftest"
KILL_SCHEMA = "calmline_kill_selftest"

# Three real policies that carry one of everything between them: LP-20000137
# has contacts and notes; LP-20000959 has a never-executed trust and a case
# with a narrative (`CW-100959501`); LP-20005343 carries live work in the
# committed queue, so the open-case write path is proven here too.
SUBSET = frozenset({"LP-20000137", "LP-20000959", "LP-20005343"})


def _quiet(line):
    pass


async def _connect():
    from src.config import MissingConfigError, load_config
    try:
        config = load_config()
    except MissingConfigError:
        pytest.skip("no live DATABASE_URL")
    import asyncpg

    return await asyncpg.connect(config.DATABASE_URL, statement_cache_size=0)


async def _fresh_schema(conn, name):
    await conn.execute(f"drop schema if exists {name} cascade")
    await conn.execute(f"create schema {name}")
    await conn.execute(f"set search_path to {name}, public, extensions")
    await apply_migrations(conn, out=_quiet)


def _stories_for(world, policy_no, kind):
    return [row for row in world.stories
            if row["policy_no"] == policy_no and row["kind"] == kind]


def test_a_subset_loads_whole_twice_and_the_triggers_refuse():
    async def scenario():
        import asyncpg

        conn = await _connect()
        try:
            await _fresh_schema(conn, SCHEMA)
            world = read_world(DEFAULT_ROOT)

            first = await load_world(conn, world, only=SUBSET, out=_quiet)
            assert set(first.loaded) == SUBSET
            assert first.notes == sum(
                len(_stories_for(world, p, "note")) for p in SUBSET)
            assert first.narratives == sum(
                len(_stories_for(world, p, "narrative")) for p in SUBSET)
            # the sweep completed the people table despite the subset
            assert await conn.fetchval("select count(*) from parties") == \
                sum(1 for person in world.people if "party_id" in person)
            # the live queue rode the same load, open statuses and all
            live_rows = [row for row in world.queue
                         if row["policy_no"] in SUBSET]
            assert first.queue == len(live_rows)
            open_in_db = await conn.fetchval(
                "select count(*) from cases where status <> 'completed'")
            assert open_in_db == len(live_rows)

            second = await load_world(conn, world, only=SUBSET, out=_quiet)
            assert second.loaded == ()
            assert set(second.already_present) == SUBSET
            assert second.notes == 0 and second.narratives == 0
            assert second.queue == 0

            for statement in (
                    "update transactions set actor = actor",
                    "delete from transactions",
                    "update record_changes set actor = actor",
                    "update contact_notes set body = 'edited'",
                    "delete from contact_notes",
                    "update case_narratives set body = 'edited'",
                    "delete from case_narratives"):
                with pytest.raises(asyncpg.PostgresError) as refusal:
                    await conn.execute(statement)
                assert "append-only" in str(refusal.value), statement
        finally:
            await conn.execute(f"drop schema if exists {SCHEMA} cascade")
            await conn.close()

    asyncio.run(scenario())


def test_a_load_killed_mid_flight_leaves_every_committed_policy_whole():
    async def scenario():
        conn = await _connect()
        process = None
        try:
            await _fresh_schema(conn, KILL_SCHEMA)
            world = read_world(DEFAULT_ROOT)

            process = subprocess.Popen(
                [sys.executable, "-m", "world.load", "--schema", KILL_SCHEMA],
                cwd=str(REPO), stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)

            deadline = time.monotonic() + 180
            committed = 0
            while committed < 3:
                if time.monotonic() > deadline:
                    process.kill()
                    output = process.communicate()[0].decode()
                    pytest.fail(f"loader never committed 3 policies: {output}")
                if process.poll() is not None:
                    output = process.communicate()[0].decode()
                    pytest.fail(f"loader exited before the kill: {output}")
                await asyncio.sleep(0.25)
                committed = await conn.fetchval(
                    f"select count(*) from {KILL_SCHEMA}.policies")

            os.kill(process.pid, signal.SIGKILL)
            process.wait(timeout=30)

            present = [row["policy_no"] for row in await conn.fetch(
                f"select policy_no from {KILL_SCHEMA}.policies")]
            assert 0 < len(present) < len(world.policies), \
                "the kill arrived after the whole book loaded"

            by_no = {policy.policy_no: policy for policy in world.policies}
            for policy_no in present:
                policy = by_no[policy_no]
                operations = world.operations.get(policy_no)
                expected = {
                    "transactions": len(policy.entries),
                    "record_changes": len(policy.events),
                    "interactions": len(operations.contacts) if operations else 0,
                    "cases": len(operations.cases) if operations else 0,
                    "evidence": sum(len(k.evidence) for k in operations.cases)
                                if operations else 0,
                    "contact_notes": len(_stories_for(world, policy_no, "note")),
                    "case_narratives": len(_stories_for(world, policy_no,
                                                        "narrative")),
                }
                for table, count in expected.items():
                    key = ("entity_id" if table == "record_changes" else
                           "policy_no")
                    found = await conn.fetchval(
                        f"select count(*) from {KILL_SCHEMA}.{table} "
                        f"where {key} = $1", policy_no)
                    assert found == count, (
                        f"{policy_no} is partial: {table} holds {found}, "
                        f"the file carries {count}")
        finally:
            if process is not None and process.poll() is None:
                process.kill()
            await conn.execute(
                f"drop schema if exists {KILL_SCHEMA} cascade")
            await conn.close()

    asyncio.run(scenario())
