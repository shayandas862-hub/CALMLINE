"""Where traces live — one interface, two backends.

**Append-only, deliberately.** There is no update and no delete on either
backend. A trace is evidence: `06-RAGOPS:4.2` makes gate-bypass double as a
data-breach detector, and a record of a breach that can be edited afterwards is
not a record of a breach. Reads hand back immutable snapshots, the same idiom
``GateEventLog`` already uses for the same reason.

Filters **combine**. Passing two narrows to the intersection rather than the
last one winning — a screen that silently widens its own filter is how a
dashboard starts describing traffic nobody asked about.

The in-memory store is what the console and every test use. ``PostgresTraceStore``
answers the same questions over the ``traces`` table for a deployment that wants
history beyond one process; it is exercised only by the marker-gated integration
test, like the rest of the live layer.
"""

from __future__ import annotations

import json
from typing import Any, Optional, Protocol, runtime_checkable

from src.traces.schema import TraceRecord

_TABLE = "traces"

# Every field of the record, in the order the table declares them. One list, so
# the columns and the placeholders can never drift apart.
_COLUMNS = ("trace_id", "cn_ref", "ts", "channel", "user_role",
            "resolved_intent", "filters_applied", "retrieved", "reranked",
            "cited", "answer_text", "abstained", "guardrail_events",
            "handoff", "latency_ms", "model_id", "mode", "kb_version",
            "feedback")

# Which of those are stored as jsonb rather than scalars.
_JSON_COLUMNS = frozenset({"filters_applied", "retrieved", "reranked", "cited",
                           "abstained", "guardrail_events", "latency_ms",
                           "feedback"})


@runtime_checkable
class TraceStore(Protocol):
    """What both backends answer. No mutation beyond appending."""

    def append(self, record: TraceRecord) -> TraceRecord: ...

    def all(self) -> tuple[TraceRecord, ...]: ...

    def query(self, *, cn_ref: Optional[str] = None,
              user_role: Optional[str] = None,
              since: Optional[str] = None,
              until: Optional[str] = None) -> tuple[TraceRecord, ...]: ...


def _matches(record: TraceRecord, *, cn_ref: Optional[str],
             user_role: Optional[str], since: Optional[str],
             until: Optional[str]) -> bool:
    """Every supplied filter must hold — they narrow together, never replace."""
    if cn_ref is not None and record.cn_ref != cn_ref:
        return False
    if user_role is not None and record.user_role != user_role:
        return False
    if since is not None and record.ts < since:
        return False
    return not (until is not None and record.ts > until)


class InMemoryTraceStore:
    """The store the console runs on. Append-only; reads are snapshots."""

    def __init__(self) -> None:
        self._records: list[TraceRecord] = []

    def append(self, record: TraceRecord) -> TraceRecord:
        """Add one trace and return it. There is no counterpart to this."""
        self._records.append(record)
        return record

    def all(self) -> tuple[TraceRecord, ...]:
        """An immutable snapshot — mutating it cannot reach the store."""
        return tuple(self._records)

    def query(self, *, cn_ref: Optional[str] = None,
              user_role: Optional[str] = None,
              since: Optional[str] = None,
              until: Optional[str] = None) -> tuple[TraceRecord, ...]:
        """The traces matching **every** filter given, in arrival order.

        ``since``/``until`` are inclusive at both ends: a window that quietly
        drops its boundary rows makes two adjacent reports disagree about the
        same trace.
        """
        return tuple(r for r in self._records
                     if _matches(r, cn_ref=cn_ref, user_role=user_role,
                                 since=since, until=until))


def _to_row(record: TraceRecord) -> list[Any]:
    """The record as positional parameters, json-encoding the nested fields."""
    data = record.model_dump()
    return [json.dumps(data[c]) if c in _JSON_COLUMNS else data[c]
            for c in _COLUMNS]


def _from_row(row: Any) -> TraceRecord:
    """A database row back into a record, decoding the jsonb columns."""
    data = {c: (json.loads(row[c]) if c in _JSON_COLUMNS and isinstance(row[c], str)
                else row[c])
            for c in _COLUMNS}
    return TraceRecord(**{k: v for k, v in data.items() if v is not None})


class PostgresTraceStore:
    """The same questions, over the ``traces`` table.

    Async, because the pool is (``src/db/pool.py``). Parameterised throughout —
    no value is ever interpolated into the SQL, and the filter columns are a
    fixed allow-list rather than anything a caller names.
    """

    def __init__(self, *, pool: Any) -> None:
        self._pool = pool

    async def append(self, record: TraceRecord) -> TraceRecord:
        placeholders = ", ".join(f"${i}" for i in range(1, len(_COLUMNS) + 1))
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"insert into {_TABLE} ({', '.join(_COLUMNS)}) "
                f"values ({placeholders})",
                *_to_row(record))
        return record

    async def all(self) -> tuple[TraceRecord, ...]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"select {', '.join(_COLUMNS)} from {_TABLE} order by ts, trace_id")
        return tuple(_from_row(r) for r in rows)

    async def query(self, *, cn_ref: Optional[str] = None,
                    user_role: Optional[str] = None,
                    since: Optional[str] = None,
                    until: Optional[str] = None) -> tuple[TraceRecord, ...]:
        clauses, params = [], []
        for column, op, value in (("cn_ref", "=", cn_ref),
                                  ("user_role", "=", user_role),
                                  ("ts", ">=", since),
                                  ("ts", "<=", until)):
            if value is not None:
                params.append(value)
                clauses.append(f"{column} {op} ${len(params)}")
        where = f" where {' and '.join(clauses)}" if clauses else ""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"select {', '.join(_COLUMNS)} from {_TABLE}{where} "
                "order by ts, trace_id", *params)
        return tuple(_from_row(r) for r in rows)
