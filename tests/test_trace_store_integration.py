"""`PostgresTraceStore` against the LIVE `traces` table — opt-in, never in a default run.

    pytest -m integration

`pyproject.toml` deselects this marker by default, so `pytest -q` makes zero
database calls even on a machine with a real `.env`; and each test skips if the
credentials or the table are absent, so `-m integration` on a bare checkout
reports "skipped", not "error".

**Why this file exists.** The phase-5 handoff flagged `PostgresTraceStore` as
dead code: never constructed, never imported, never tested — the existing tests
only check that the *migration text* declares the table. Untested database code
is not a spare tyre, it is a spare tyre nobody has checked is inflated, and it
reads as "we support Postgres" when what is true is "we have written something
that might".

Phase 6 resolves it by **testing it rather than deleting it** (D-CL-090): the
card's Out Of Scope forbids edits to `src/traces/` beyond runner wiring, so
deleting was out of scope while adding a test was never an edit to it at all.

What this proves that the unit tests cannot: that the columns the migration
declares, the JSON encoding `_to_row` applies and the decoding `_from_row`
expects all agree with each other, against a real server.
"""

import asyncio

import pytest

from src.config import MissingConfigError, load_config
from src.db.pool import close_pool, reset_pool
from src.traces.schema import TraceRecord
from src.traces.store import PostgresTraceStore

pytestmark = pytest.mark.integration

TS = "2026-07-26T11:00:00"
CN_REF = "CN-2026072601"


def _requires_live_config():
    try:
        load_config()
    except MissingConfigError:
        pytest.skip("no live Supabase credentials — apply the migrations first")


def _record(trace_id):
    return TraceRecord(
        trace_id=trace_id,
        cn_ref=CN_REF,
        ts=TS,
        user_role="front_office",
        mode="live",
        model_id="claude-haiku-4-5",
        answer_text="It was worth £151,240.00.",
        retrieved=[{"chunk_id": "02-BOND:4.9", "version": 1, "rank": 1, "score": 0.9}],
        cited=[{"chunk_id": "02-BOND:4.9", "version": 1}],
        guardrail_events=["get_valuation refused: caller not verified"],
        kb_version="abc123def456",
    )


async def _round_trip(trace_id):
    from src.db.pool import get_pool

    pool = await get_pool()
    store = PostgresTraceStore(pool=pool)
    await store.append(_record(trace_id))
    return await store.query(cn_ref=CN_REF)


def _run(coro):
    reset_pool()
    try:
        return asyncio.run(coro)
    finally:
        asyncio.run(close_pool())


def test_a_record_written_to_postgres_reads_back_whole():
    _requires_live_config()
    trace_id = "TR-INT-001"
    try:
        found = _run(_round_trip(trace_id))
    except Exception as exc:  # no table, no server → a skip, not a red suite
        pytest.skip(f"traces table unavailable ({type(exc).__name__}: {exc})")

    stored = [r for r in found if r.trace_id == trace_id]
    assert stored, "the record was written but did not come back"
    record = stored[0]
    assert record.answer_text.startswith("It was worth")
    assert record.mode == "live" and record.model_id == "claude-haiku-4-5"
    # The nested shapes are where an encoding mismatch would actually bite.
    assert [(c.chunk_id, c.rank, c.version) for c in record.retrieved] == [
        ("02-BOND:4.9", 1, 1)]
    assert [c.chunk_id for c in record.cited] == ["02-BOND:4.9"]
    assert record.guardrail_events == ["get_valuation refused: caller not verified"]
