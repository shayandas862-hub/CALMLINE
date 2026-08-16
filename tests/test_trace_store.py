"""v4 phase 5 · Task 2 — the trace store: append-only, queryable, two backends.

Append-only is the point, not a convenience. A trace is evidence: gate-bypass
doubles as a data-breach detector (`06-RAGOPS:4.2`), and evidence you can edit
after the fact is not evidence. So there is no update and no delete, and reads
hand back immutable snapshots — the same idiom `GateEventLog` already uses.

The Postgres table lives in its own migration (`0002_traces.sql`) rather than in
`0001_init.sql`: that file is already 357 lines, over the repo's 300-line rule,
and it is the migration deliberately not applied yet. Adding to
it would widen a pending decision. The SQL guards here are text assertions, no
database needed, matching `tests/test_migration.py`; the applied-schema check is
marker-gated below.
"""

import re
from pathlib import Path

import pytest

from src.traces.schema import TraceRecord
from src.traces.store import InMemoryTraceStore

MIGRATION = (Path(__file__).resolve().parent.parent
             / "src" / "db" / "migrations" / "0002_traces.sql")


def _rec(trace_id="TR-1", *, cn_ref="CN-2026041201", ts="2026-04-12T10:00:00",
         user_role="front_office", mode="live", model_id="claude-sonnet-5",
         **over):
    kw = dict(trace_id=trace_id, cn_ref=cn_ref, ts=ts, user_role=user_role,
              mode=mode, model_id=model_id)
    kw.update(over)
    return TraceRecord(**kw)


# ── append and read back ───────────────────────────────────────────────

def test_a_stored_trace_comes_back():
    store = InMemoryTraceStore()
    store.append(_rec("TR-1"))
    assert [r.trace_id for r in store.all()] == ["TR-1"]


def test_traces_keep_the_order_they_arrived_in():
    store = InMemoryTraceStore()
    for i in (1, 2, 3):
        store.append(_rec(f"TR-{i}"))
    assert [r.trace_id for r in store.all()] == ["TR-1", "TR-2", "TR-3"]


def test_an_empty_store_reads_as_empty_not_as_an_error():
    assert InMemoryTraceStore().all() == ()


# ── append-only ────────────────────────────────────────────────────────

def test_the_store_offers_no_way_to_change_or_remove_a_trace():
    # A trace is evidence — gate-bypass doubles as a data-breach detector. An
    # editable record of a breach is not a record of a breach.
    store = InMemoryTraceStore()
    for forbidden in ("update", "delete", "remove", "clear", "pop"):
        assert not hasattr(store, forbidden), (
            f"{forbidden!r} exists — the store must be append-only")


def test_mutating_a_snapshot_cannot_reach_the_store():
    store = InMemoryTraceStore()
    store.append(_rec("TR-1"))
    snapshot = store.all()
    assert isinstance(snapshot, tuple)
    assert [r.trace_id for r in store.all()] == ["TR-1"]


# ── querying ───────────────────────────────────────────────────────────

def test_query_by_interaction():
    # The headline done criterion: one conversation's traces, found by its CN-.
    store = InMemoryTraceStore()
    store.append(_rec("TR-1", cn_ref="CN-2026041201"))
    store.append(_rec("TR-2", cn_ref="CN-2026041202"))
    store.append(_rec("TR-3", cn_ref="CN-2026041201"))
    got = store.query(cn_ref="CN-2026041201")
    assert [r.trace_id for r in got] == ["TR-1", "TR-3"]


def test_query_by_role():
    store = InMemoryTraceStore()
    store.append(_rec("TR-1", user_role="front_office"))
    store.append(_rec("TR-2", user_role="ops"))
    assert [r.trace_id for r in store.query(user_role="ops")] == ["TR-2"]


def test_query_by_time_window_is_inclusive_at_both_ends():
    store = InMemoryTraceStore()
    store.append(_rec("TR-1", ts="2026-04-11T09:00:00"))
    store.append(_rec("TR-2", ts="2026-04-12T09:00:00"))
    store.append(_rec("TR-3", ts="2026-04-13T09:00:00"))
    got = store.query(since="2026-04-12T09:00:00", until="2026-04-13T09:00:00")
    assert [r.trace_id for r in got] == ["TR-2", "TR-3"]


def test_filters_combine_rather_than_replace_each_other():
    store = InMemoryTraceStore()
    store.append(_rec("TR-1", cn_ref="CN-2026041201", user_role="front_office"))
    store.append(_rec("TR-2", cn_ref="CN-2026041201", user_role="ops"))
    got = store.query(cn_ref="CN-2026041201", user_role="ops")
    assert [r.trace_id for r in got] == ["TR-2"]


def test_no_filter_returns_everything():
    store = InMemoryTraceStore()
    store.append(_rec("TR-1"))
    store.append(_rec("TR-2"))
    assert len(store.query()) == 2


def test_a_filter_matching_nothing_returns_empty_not_everything():
    # The failure that turns a filtered dashboard into an unfiltered one.
    store = InMemoryTraceStore()
    store.append(_rec("TR-1", cn_ref="CN-2026041201"))
    assert store.query(cn_ref="CN-9999999999") == ()


# ── both paths, one shape ──────────────────────────────────────────────

def test_a_keyword_trace_and_a_live_trace_sit_in_the_same_store():
    # The five metrics stay pure folds over ONE record type; the paths differ
    # only by mode and model_id.
    store = InMemoryTraceStore()
    store.append(_rec("TR-1", mode="live", model_id="claude-sonnet-5"))
    store.append(_rec("TR-2", mode="keyword", model_id=None))
    modes = [(r.mode, r.model_id) for r in store.all()]
    assert modes == [("live", "claude-sonnet-5"), ("keyword", None)]


# ── the migration, as text ─────────────────────────────────────────────

def sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_the_traces_migration_exists_separately_from_0001():
    assert MIGRATION.exists(), (
        "0002_traces.sql must exist: 0001_init.sql is already over the "
        "300-line rule and is the migration the operator has not applied")


def test_it_creates_the_traces_table():
    assert re.search(r"create table if not exists\s+traces", sql())


def test_the_table_holds_every_field_the_record_carries():
    body = sql()
    for column in ("trace_id", "cn_ref", "ts", "channel", "user_role",
                   "resolved_intent", "filters_applied", "retrieved",
                   "reranked", "cited", "answer_text", "abstained",
                   "guardrail_events", "handoff", "latency_ms", "model_id",
                   "mode", "kb_version", "feedback"):
        assert re.search(rf"\b{column}\b", body), f"traces is missing {column}"


def test_the_trace_id_is_the_primary_key():
    assert re.search(r"trace_id\s+text\s+primary key", sql())


def test_it_is_indexed_for_the_queries_the_screen_actually_makes():
    body = sql()
    for column in ("cn_ref", "ts", "user_role", "model_id"):
        assert re.search(rf"create index if not exists.*\({column}\)", body), (
            f"no index on {column} — the ops screen filters by it")


def test_it_does_not_touch_the_tables_0001_owns():
    # Blast radius, in SQL. This migration adds; it must not drop or alter.
    body = sql().lower()
    assert "drop table" not in body
    assert "alter table" not in body


# ── the applied schema (needs the live database) ───────────────────────

@pytest.mark.integration
def test_the_traces_table_exists_in_the_applied_schema():
    import asyncio

    from src.config import load_config
    from src.db.pool import get_pool

    async def _check():
        pool = await get_pool(load_config())
        async with pool.acquire() as conn:
            return await conn.fetchval(
                "select to_regclass('public.traces') is not null")

    assert asyncio.run(_check()) is True
