"""Compare the live database against the committed world, and name what differs.

    .venv/bin/python -m world.load.verify
    .venv/bin/python -m world.load.verify --schema rehearsal

What makes "the database holds the approved world" checkable by somebody who
was not there: the world is projected into the loader's own shape, the live
tables are snapshotted whole, and every difference is reported by table, key
and field — a missing row, a stranger the dataset never wrote, a value that
moved. Counts alone would pass an edited amount; the fields are read.

Read-only against the database, always. The verify command fixes nothing and
never will — a difference is something a person decides about.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Optional

from src.records.models import DEBIT_KINDS
from world.dataset import DEFAULT_ROOT, read_world
from world.load.expected import project

_SCHEMA_RE = re.compile(r"[a-z_][a-z0-9_]{0,62}")


def _jsonb(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _day(stamp: Any) -> Optional[str]:
    return None if stamp is None else stamp.date().isoformat()


def _moment(stamp: Any) -> Optional[str]:
    if stamp is None:
        return None
    return stamp.replace(tzinfo=None).isoformat(timespec="seconds")


async def snapshot(conn: Any) -> dict:
    """Every loaded table, whole, in the projection's own shape."""
    snap: dict[str, Any] = {
        "parties": {}, "policies": {}, "mandates": {}, "authorities": {},
        "transactions": {}, "events": {}, "interactions": {}, "notes": {},
        "cases": {}, "narratives": {}, "evidence": {}, "values": {},
    }
    for row in await conn.fetch("select * from parties"):
        snap["parties"][row["party_id"]] = {
            "name": row["name"], "dob": row["dob"].isoformat(),
            "registered_address": row["registered_address"],
            "contact": _jsonb(row["contact"])}
    for row in await conn.fetch("select * from policies"):
        snap["policies"][row["policy_no"]] = {
            "product": row["product"], "status": row["status"],
            "start_date": row["start_date"].isoformat(),
            "holder_party_id": row["holder_party_id"],
            "trust": _jsonb(row["trust"]),
            "adviser_loa": _jsonb(row["adviser_loa"]),
            "bank_last4": row["bank_last4"]}
    for row in await conn.fetch("select * from bank_mandates"):
        snap["mandates"][row["policy_no"]] = {
            "account_last4": row["account_last4"],
            "verified": row["verified"],
            "hold_until": (row["hold_until"].isoformat()
                           if row["hold_until"] else None),
            "change_history": _jsonb(row["change_history"])}
    for row in await conn.fetch("select * from authority_records"):
        snap["authorities"][row["authority_id"]] = {
            "policy_no": row["policy_no"], "party_id": row["party_id"],
            "type": row["type"], "scope": list(row["scope"]),
            "status": row["status"]}
    for row in await conn.fetch("select * from transactions"):
        snap["transactions"][(row["policy_no"], row["seq"])] = {
            "txn_id": row["txn_id"], "kind": row["kind"],
            "amount_pence": row["amount_pence"],
            "balance_after_pence": row["balance_after_pence"],
            "reason": row["reason"], "actor": row["actor"],
            "at": _moment(row["at"])}
    for row in await conn.fetch(
            "select * from record_changes order by seq"):
        (delta,) = _jsonb(row["changes"])
        snap["events"].setdefault(row["entity_id"], []).append(
            {"field": delta["field"], "new": delta["new"],
             "on": _day(row["at"])})
    for row in await conn.fetch("select * from interactions"):
        snap["interactions"][row["cn_ref"]] = {
            "policy_no": row["policy_no"], "on": _day(row["opened_at"]),
            "channel": row["channel"], "intent": row["intent"],
            "outcome": row["outcome"]}
    for row in await conn.fetch("select * from contact_notes"):
        snap["notes"][row["cn_ref"]] = {
            "policy_no": row["policy_no"], "body": row["body"]}
    for row in await conn.fetch("select * from cases"):
        snap["cases"][row["cw_ref"]] = {
            "policy_no": row["policy_no"], "request": row["request"],
            "type": row["type"], "status": row["status"],
            "priority": row["priority"],
            "human_decision": row["human_decision"],
            "opened_on": _day(row["created_at"]),
            "sla_due": _moment(row["sla_due"])}
    for row in await conn.fetch("select * from case_narratives"):
        snap["narratives"][row["cw_ref"]] = {
            "policy_no": row["policy_no"], "body": row["body"]}
    for row in await conn.fetch("select * from evidence"):
        snap["evidence"][row["evidence_id"]] = {
            "cw_ref": row["cw_ref"], "policy_no": row["policy_no"],
            "requirement": row["requirement"],
            "requirement_source": row["requirement_source"],
            "received_via": row["received_via"],
            "received_on": _day(row["received_at"]),
            "satisfies": row["satisfies"]}
    for row in await conn.fetch(
            "select policy_no, coalesce(sum(case when kind = any($1) then "
            "-amount_pence else amount_pence end), 0) as value "
            "from transactions group by policy_no", sorted(DEBIT_KINDS)):
        snap["values"][row["policy_no"]] = row["value"]
    return snap


def compare(world: Any, snap: dict, only: Any = None) -> tuple[str, ...]:
    """Every difference between the committed world and a snapshot, named."""
    expected = project(world, only=only)
    problems: list[str] = []

    for table, wanted in expected.items():
        found = snap.get(table, {})
        if table == "events":
            problems.extend(_diff_events(wanted, found))
            continue
        if table == "values":
            for policy_no, value in wanted.items():
                held = found.get(policy_no, 0)
                if held != value:
                    problems.append(f"{policy_no} value: database {held}p, "
                                    f"file {value}p")
            continue
        for key, fields in wanted.items():
            row = found.get(key)
            if row is None:
                problems.append(f"{table} {key}: missing from the database")
                continue
            for field, want in fields.items():
                have = row.get(field)
                if have != want:
                    problems.append(f"{table} {key} {field}: database "
                                    f"{have!r}, file {want!r}")
        for key in found:
            if key not in wanted:
                problems.append(f"{table} {key}: in the database but "
                                f"not in the dataset")
    return tuple(problems)


def _diff_events(wanted: dict, found: dict) -> list:
    problems = []
    for policy_no, events in wanted.items():
        held = found.get(policy_no, [])
        if held != events:
            problems.append(
                f"record_changes {policy_no}: the database journals "
                f"{len(held)} events, the file carries {len(events)}"
                if len(held) != len(events) else
                f"record_changes {policy_no}: an event differs — first at "
                f"position "
                f"{next(i for i, (a, b) in enumerate(zip(held, events)) if a != b)}")
    for policy_no in found:
        if policy_no not in wanted:
            problems.append(f"record_changes {policy_no}: in the database "
                            f"but not in the dataset")
    return problems


async def verify_world(conn: Any, world: Any, *, only: Any = None,
                       out: Callable[[str], None] = print) -> tuple[str, ...]:
    """Snapshot, compare, report. Returns the problems; prints every one."""
    snap = await snapshot(conn)
    problems = compare(world, snap, only=only)
    if problems:
        for problem in problems:
            out(f"  DIFFERS — {problem}")
        out(f"verify: {len(problems)} differences between the database and "
            f"the committed world")
    else:
        counted = sum(len(table) for table in snap.values())
        out(f"verify: clean — {counted} database rows match the committed "
            f"world exactly")
    return problems


async def _amain(args: argparse.Namespace) -> int:
    import asyncpg

    from src.config import load_config

    world = read_world(Path(args.root))
    conn = await asyncpg.connect(load_config().DATABASE_URL,
                                 statement_cache_size=0)
    try:
        if args.schema:
            if not _SCHEMA_RE.fullmatch(args.schema):
                raise SystemExit(f"{args.schema!r} is not a schema name")
            await conn.execute(
                f"set search_path to {args.schema}, public, extensions")
        only = frozenset(args.only.split(",")) if args.only else None
        problems = await verify_world(conn, world, only=only)
        return 1 if problems else 0
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--schema", default=None)
    parser.add_argument("--only", default=None,
                        help="comma-separated policy numbers (rehearsals)")
    return asyncio.run(_amain(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
