"""`world/load` — the approved world into Postgres, one policy per transaction.

The unit of loading is the **policy**: its cast, its row, its mandate and
authorities, its whole ledger, its events as journal rows, its contacts with
their notes, its cases with their evidence and narratives — committed together,
so every policy in the database is whole and a crash costs only the one in
flight.

These tests drive the loader against a fake connection that records every
statement. The live proofs — triggers actually refusing, a second run loading
nothing, a load killed mid-flight leaving nothing partial — are integration
tests in `tests/test_world_load_live.py`, split there at the 300-line rule.
"""

import asyncio
import dataclasses

import pytest

from src.records.models import Trust
from world.load import LoadError, load_world

# ── a fake connection that records everything ────────────────────────────


class FakeDb:
    """asyncpg's surface as the loader uses it: existence answered from a
    canned set of present policies, every write recorded in order."""

    def __init__(self, *, present=()):
        self.present = set(present)
        self.case_refs: set[str] = set()
        self.statements: list[tuple[str, tuple]] = []
        self.transactions_opened = 0

    async def fetchval(self, sql, *args):
        if "information_schema.tables" in sql:
            return 1  # the schema looks migrated
        raise AssertionError(f"unexpected fetchval: {sql}")

    async def fetch(self, sql, *args):
        if "select policy_no from policies" in sql:
            return [{"policy_no": policy_no} for policy_no in sorted(self.present)]
        if "select cw_ref from cases" in sql:
            return [{"cw_ref": ref} for ref in sorted(self.case_refs)]
        raise AssertionError(f"unexpected fetch: {sql}")

    async def execute(self, sql, *args):
        self.statements.append((sql, args))
        if sql.lower().lstrip().startswith("insert into policies"):
            self.present.add(args[0])
        if sql.lower().lstrip().startswith("insert into cases"):
            self.case_refs.add(args[0])

    async def executemany(self, sql, rows):
        for row in rows:
            self.statements.append((sql, tuple(row)))
            if sql.lower().lstrip().startswith("insert into cases"):
                self.case_refs.add(row[0])

    def transaction(self):
        self.transactions_opened += 1
        return _NullTx()


class _NullTx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _person(party_id, name):
    return {"party_id": party_id, "name": name, "dob": "1961-04-08",
            "registered_address": "3 Lattice Way, Demoford ZZ9 1AA",
            "contact": {"phone": "07700 900101",
                        "email": f"{party_id.lower()}@example.org",
                        "registered": True}}


@pytest.fixture
def small_world(tiny_world):
    """`tiny_world` with people the loader can actually transcribe."""
    return dataclasses.replace(
        tiny_world, people=[_person("PH-0001", "Theta Meridian 12"),
                            _person("PH-0002", "Argon Basalt 27")])


def _load(db, world, **kwargs):
    quiet = kwargs.pop("out", lambda line: None)
    return asyncio.run(load_world(db, world, out=quiet, **kwargs))


def _sql(db, fragment):
    return [(sql, args) for sql, args in db.statements
            if fragment in sql.lower()]


def _with_stories(world, *rows):
    return dataclasses.replace(world, stories=tuple(rows))


NOTE = {"kind": "note", "policy_no": "LP-20000137", "ref": "CN-2000013701",
        "text": "Rang for a value. Gave the figure and confirmed the basis."}
NARRATIVE = {"kind": "narrative", "policy_no": "LP-20000137",
             "ref": "CW-300000001",
             "text": "Raised off the call. Evidence arrived and was checked."}


# ── one policy, one transaction, everything hanging off it ───────────────


def test_each_policy_loads_inside_its_own_transaction(small_world):
    db = FakeDb()
    _load(db, small_world)
    # two policies, two transactions; every person was already in a cast,
    # so no sweep transaction is opened for an empty sweep
    assert db.transactions_opened == 2


def test_the_cast_is_written_before_the_policy_and_never_replaced(small_world):
    db = FakeDb()
    _load(db, small_world)
    first_party = min(i for i, (sql, _) in enumerate(db.statements)
                      if "insert into parties" in sql.lower())
    first_policy = min(i for i, (sql, _) in enumerate(db.statements)
                       if "insert into policies" in sql.lower())
    assert first_party < first_policy
    assert all("on conflict (party_id) do nothing" in sql.lower()
               for sql, _ in _sql(db, "insert into parties"))


def test_the_whole_ledger_is_written_with_injected_times(small_world):
    from datetime import datetime, timezone

    db = FakeDb()
    _load(db, small_world)
    movements = _sql(db, "insert into transactions")
    assert len(movements) == 3          # two LP entries + one on the bond
    sql, args = movements[0]
    assert "now()" not in sql.lower()
    # a real datetime, tz-aware, carrying the movement's own moment — the
    # shape asyncpg's binary codec actually accepts
    assert datetime(1998, 3, 1, tzinfo=timezone.utc) in args


def test_events_become_journal_rows_attributed_to_the_seed(small_world):
    db = FakeDb()
    _load(db, small_world)
    journal = _sql(db, "insert into record_changes")
    assert len(journal) == 1            # tiny_world carries one event
    sql, args = journal[0]
    written = sql + " " + " ".join(str(arg) for arg in args)
    assert "world" in written and "seed" in written
    assert "premium_review" in written


def test_a_present_policy_is_reported_not_reloaded_not_overwritten(small_world):
    db = FakeDb(present={"LP-20000137"})
    report = _load(db, small_world)

    assert report.already_present == ("LP-20000137",)
    assert report.loaded == ("HB-20000274",)
    assert not any(args and args[0] == "LP-20000137"
                   for sql, args in _sql(db, "insert into policies"))
    assert not any(sql.lower().lstrip().startswith(("update", "delete"))
                   for sql, _ in db.statements)


def test_a_second_run_loads_nothing_and_says_so(small_world):
    db = FakeDb()
    _load(db, small_world)
    lines = []
    second = _load(db, small_world, out=lines.append)
    assert second.loaded == ()
    assert set(second.already_present) == {"LP-20000137", "HB-20000274"}
    assert any("nothing to load" in line for line in lines)


# ── the prose, the easiest thing to silently drop ────────────────────────


def test_a_note_is_written_against_its_contact_with_the_calls_own_date(small_world):
    db = FakeDb()
    report = _load(db, _with_stories(small_world, NOTE))
    notes = _sql(db, "insert into contact_notes")
    assert len(notes) == 1
    _, args = notes[0]
    assert "CN-2000013701" in args
    assert any("2024-04-02" in str(arg) for arg in args)   # the call's date
    assert report.notes == 1


def test_a_narrative_is_written_against_its_case_dated_at_closure(small_world):
    db = FakeDb()
    report = _load(db, _with_stories(small_world, NOTE, NARRATIVE))
    narratives = _sql(db, "insert into case_narratives")
    assert len(narratives) == 1
    _, args = narratives[0]
    assert "CW-300000001" in args
    assert any("2024-04-09" in str(arg) for arg in args)   # closed_on
    assert report.narratives == 1


def test_a_story_against_no_contact_is_refused_and_named(small_world):
    orphan = dict(NOTE, ref="CN-9999999999")
    with pytest.raises(LoadError) as refusal:
        _load(FakeDb(), _with_stories(small_world, orphan))
    assert "CN-9999999999" in str(refusal.value)


def test_prose_for_an_already_present_policy_is_not_rewritten(small_world):
    db = FakeDb(present={"LP-20000137"})
    report = _load(db, _with_stories(small_world, NOTE, NARRATIVE))
    assert _sql(db, "insert into contact_notes") == []
    assert report.notes == 0 and report.narratives == 0


# ── everything else hanging off the policy ───────────────────────────────


def test_mandate_authorities_contacts_cases_and_evidence_all_land(small_world):
    db = FakeDb()
    _load(db, small_world)
    for table, expected in (("bank_mandates", 2), ("interactions", 1),
                            ("cases", 1), ("evidence", 1)):
        assert len(_sql(db, f"insert into {table}")) == expected, table


def test_the_trust_is_transcribed_as_is_including_its_executed_field(small_world):
    trust_world = dataclasses.replace(
        small_world,
        trusts={"LP-20000137": Trust(kind="discretionary", executed="no",
                                     trustees=("PH-6001",), registrable=False,
                                     urn=None)},
        people=small_world.people + [_person("PH-6001", "Alpha Feldspar 2")])
    db = FakeDb()
    _load(db, trust_world)
    policy_rows = _sql(db, "insert into policies")
    trust_json = [arg for _, args in policy_rows for arg in args
                  if isinstance(arg, str) and "executed" in arg]
    assert trust_json and '"executed": "no"' in trust_json[0]


def test_the_sweep_completes_the_people_table_after_the_policies(small_world):
    world = dataclasses.replace(
        small_world,
        people=small_world.people + [_person("PH-6001", "Alpha Feldspar 2")])
    db = FakeDb()
    report = _load(db, world)
    assert db.transactions_opened == 3          # two policies + the sweep
    swept = [args for sql, args in _sql(db, "insert into parties")
             if args and args[0] == "PH-6001"]
    assert swept, "the unreferenced trustee never reached the parties table"
    assert report.people == 3


def test_a_person_with_no_party_id_is_a_firm_and_is_not_a_party(small_world):
    world = dataclasses.replace(
        small_world, people=small_world.people + [{"firm_id": "AF-001",
                                                   "name": "Braid & Mantle"}])
    db = FakeDb()
    report = _load(db, world)
    assert report.people == 2
    assert not any("AF-001" in str(args) for _, args in db.statements)


def test_a_holder_missing_from_the_people_file_is_refused_and_named(small_world):
    short = dataclasses.replace(small_world, people=small_world.people[:1])
    with pytest.raises(LoadError) as refusal:
        _load(FakeDb(), short)
    assert "PH-0002" in str(refusal.value)


# ── the live queue rides the same load ───────────────────────────────────


def test_queue_rows_load_as_open_cases_and_never_twice(small_world):
    from datetime import date as _date

    from world.load.queue import open_queue

    rows = open_queue(small_world, as_of=_date(2026, 7, 28), seed=7, count=2)
    world = dataclasses.replace(small_world, queue=tuple(rows))

    db = FakeDb()
    first = _load(db, world)
    assert first.queue == 2
    open_cases = [args for sql, args in _sql(db, "insert into cases")
                  if args[4] in ("pending_review", "blocked",
                                 "held_for_review")]
    assert len(open_cases) == 2

    lines = []
    second = _load(db, world, out=lines.append)
    assert second.queue == 0
    assert any("0 live cases added" in line and "2 already present" in line
               for line in lines)
