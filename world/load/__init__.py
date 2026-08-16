"""The approved world into Postgres — transcription, one policy per transaction.

The loader writes SQL directly and does not go through the application's
storage layer: by the time it runs, every row has been proved valid by the
rules that govern the live system, and the database's own constraints are the
backstop. **It adds and never replaces** — a policy number already present is
reported as already present, never overwritten and never re-counted as a load.

The unit of loading is the **policy**. Each transaction writes the policy's
cast (insert-if-absent), the policy row, its mandate and authorities, the whole
ledger, its events as journal rows, its contacts with their notes, and its
cases with their evidence and narratives. A crash therefore costs the one
policy in flight; everything committed is whole.

The prose is the easiest thing to silently drop — it arrives from
`stories.jsonl` rather than the policy rows — so the counts written are
asserted against the counts the dataset carries, and a shortfall is a refusal,
not a warning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional

from world.load.policy_rows import (
    PolicyCounts,
    sweep_people,
    write_policy,
    write_queue_case,
)

__all__ = ["LoadError", "LoadReport", "load_world"]


class LoadError(RuntimeError):
    """A load that will not proceed, and the reason, naming what is wrong."""


@dataclass(frozen=True)
class LoadReport:
    """What one run actually did — skips are named, never counted as loads."""

    loaded: tuple[str, ...]
    already_present: tuple[str, ...]
    people: int
    movements: int
    events: int
    contacts: int
    notes: int
    cases: int
    narratives: int
    evidence: int
    queue: int = 0


async def load_world(conn: Any, world: Any, *,
                     out: Callable[[str], None] = print,
                     only: Optional[Iterable[str]] = None) -> LoadReport:
    """Load ``world`` through ``conn``. ``only`` narrows to named policies —
    the rehearsal and test seam; a real load takes the whole book."""
    await _require_migrated(conn)

    wanted = frozenset(only) if only is not None else None
    people_by_id = {person["party_id"]: person for person in world.people
                    if "party_id" in person}
    notes, narratives = _stories_by_policy(world)

    # One question, asked once: what is already there. Add-never-replace is
    # still enforced row-by-row underneath — the primary key refuses a
    # duplicate loudly if another writer lands one mid-run.
    already = {row["policy_no"] for row in
               await conn.fetch("select policy_no from policies")}

    loaded: list[str] = []
    present: list[str] = []
    totals = PolicyCounts()
    written_people: set[str] = set()

    for policy in world.policies:
        policy_no = policy.policy_no
        if wanted is not None and policy_no not in wanted:
            continue
        if policy_no in already:
            present.append(policy_no)
            continue

        async with conn.transaction():
            counts = await write_policy(
                conn, world, policy, people_by_id,
                notes=notes.get(policy_no, ()),
                narratives=narratives.get(policy_no, ()),
                written_people=written_people)
        totals = totals.plus(counts)
        loaded.append(policy_no)
        if len(loaded) % 25 == 0:
            out(f"  {len(loaded)} policies committed…")

    swept = 0
    if loaded:
        pending = [person for party_id, person in people_by_id.items()
                   if party_id not in written_people]
        if pending:
            async with conn.transaction():
                swept = await sweep_people(conn, pending)
            written_people.update(person["party_id"] for person in pending)

    _assert_prose_carried(loaded, notes, narratives, totals)
    queue_added = await _load_queue(conn, world, wanted=wanted,
                                    in_database=already | set(loaded), out=out)

    if not loaded:
        out(f"nothing to load — {len(present)} policies already present, "
            f"0 loaded")
    else:
        out(f"loaded {len(loaded)} policies · {len(present)} already present "
            f"· {len(written_people)} people · {totals.movements} movements · "
            f"{totals.notes} notes · {totals.narratives} narratives")

    return LoadReport(
        loaded=tuple(loaded), already_present=tuple(present),
        people=len(written_people), movements=totals.movements,
        events=totals.events, contacts=totals.contacts, notes=totals.notes,
        cases=totals.cases, narratives=totals.narratives,
        evidence=totals.evidence, queue=queue_added)


async def _load_queue(conn: Any, world: Any, *, wanted, in_database: set,
                      out: Callable[[str], None]) -> int:
    """The live work, after history: adds only, each case its own transaction.

    A queue row whose policy is not in the database (a narrowed rehearsal) is
    held back and said so — loading it would only bounce off the foreign key
    with a worse message.
    """
    rows = [row for row in getattr(world, "queue", ())
            if wanted is None or row["policy_no"] in wanted]
    if not rows:
        return 0
    existing = {record["cw_ref"] for record in
                await conn.fetch("select cw_ref from cases")}
    added = held_back = 0
    for row in rows:
        if row["policy_no"] not in in_database:
            held_back += 1
            continue
        if row["cw_ref"] in existing:
            continue
        async with conn.transaction():
            await write_queue_case(conn, row)
        added += 1
    skipped = len(rows) - added - held_back
    out(f"queue: {added} live cases added · {skipped} already present"
        + (f" · {held_back} held back (policy not in the database)"
           if held_back else ""))
    return added


async def _require_migrated(conn: Any) -> None:
    applied = await conn.fetchval(
        "select 1 from information_schema.tables "
        "where table_schema = current_schema() and table_name = 'policies'")
    if not applied:
        raise LoadError(
            "the target schema has no policies table — apply the migrations "
            "first (scripts/migrate.py), nothing was loaded")


def _stories_by_policy(world: Any) -> tuple[dict, dict]:
    """The prose, grouped by the policy it belongs to and split by kind."""
    notes: dict[str, tuple] = {}
    narratives: dict[str, tuple] = {}
    for row in world.stories:
        kind, policy_no = row.get("kind"), row.get("policy_no")
        if kind == "note":
            notes[policy_no] = notes.get(policy_no, ()) + (row,)
        elif kind == "narrative":
            narratives[policy_no] = narratives.get(policy_no, ()) + (row,)
        else:
            raise LoadError(f"stories.jsonl carries kind {kind!r} against "
                            f"{row.get('ref')}, which this loader does not "
                            f"understand — refusing rather than dropping it")
    return notes, narratives


def _assert_prose_carried(loaded: list, notes: dict, narratives: dict,
                          totals: PolicyCounts) -> None:
    """The explicit count the card demands: what was written equals what the
    dataset carries for the policies this run loaded. A shortfall is a load
    that reported success while dropping prose, and it is refused."""
    expected_notes = sum(len(notes.get(p, ())) for p in loaded)
    expected_narratives = sum(len(narratives.get(p, ())) for p in loaded)
    if totals.notes != expected_notes:
        raise LoadError(f"wrote {totals.notes} contact notes but the dataset "
                        f"carries {expected_notes} for these policies")
    if totals.narratives != expected_narratives:
        raise LoadError(f"wrote {totals.narratives} case narratives but the "
                        f"dataset carries {expected_narratives} for these "
                        f"policies")
