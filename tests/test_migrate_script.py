"""`scripts/migrate.py` — ordered, idempotent, recorded, and refusing the unknown.

Applying SQL has been a manual paste into a web editor; this runner ends that.
The hard part is not applying files — it is that the live database is
**half-applied and unrecorded**: the corpus and trace tables were pasted by
hand across two versions, nothing wrote down what ran, and 0001 has already
been rewritten in place once (D-CL-006). So the runner keeps its own ledger,
records a digest per applied file, and refuses any database it cannot identify
rather than guessing.

The offline tests drive the runner against a fake connection that records every
statement. The integration tests apply the real files into a **throwaway
schema** on the real database — created, migrated twice, dropped — so the
default schema is never touched by a test.
"""

import asyncio
import re

import pytest

from scripts.migrate import (
    MigrateError,
    Report,
    apply_migrations,
    migration_files,
)

# ── a fake connection that answers introspection and records writes ─────


class FakeDb:
    """Enough of asyncpg's surface for the runner: introspection answered
    from canned state, every write recorded, tracking rows kept live so a
    second run against the same fake sees what the first one did."""

    def __init__(self, *, schema="public", tables=(), tracked=None):
        self.schema = schema
        self.tables = set(tables)
        # None → no schema_migrations table; dict filename→sha256 otherwise.
        self.tracked = dict(tracked) if tracked is not None else None
        self.executed: list[str] = []
        self.transactions_opened = 0

    async def fetchval(self, sql, *args):
        if "current_schema" in sql:
            return self.schema
        raise AssertionError(f"unexpected fetchval: {sql}")

    async def fetch(self, sql, *args):
        if "information_schema.tables" in sql:
            names = set(self.tables)
            if self.tracked is not None:
                names.add("schema_migrations")
            return [{"table_name": name} for name in sorted(names)]
        if "from schema_migrations" in sql:
            return [{"filename": name, "sha256": digest}
                    for name, digest in sorted((self.tracked or {}).items())]
        raise AssertionError(f"unexpected fetch: {sql}")

    async def execute(self, sql, *args):
        self.executed.append(sql)
        lowered = sql.lower()
        if "create table if not exists schema_migrations" in lowered:
            self.tracked = self.tracked or {}
        elif "insert into schema_migrations" in lowered:
            self.tracked[args[0]] = args[1]

    def transaction(self):
        self.transactions_opened += 1
        return _NullTx()


class _NullTx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _apply(db, **kwargs):
    quiet = kwargs.pop("out", lambda line: None)
    return asyncio.run(apply_migrations(db, out=quiet, **kwargs))


# ── the files themselves ─────────────────────────────────────────────────


def test_migration_files_come_back_ordered_by_filename(tmp_path):
    for name in ("0003_c.sql", "0001_a.sql", "0002_b.sql"):
        (tmp_path / name).write_text(f"-- {name}\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not sql", encoding="utf-8")

    files = migration_files(tmp_path)
    assert [f.name for f in files] == ["0001_a.sql", "0002_b.sql", "0003_c.sql"]
    assert all(re.fullmatch(r"[0-9a-f]{16}", f.digest) for f in files)


def test_the_repos_own_migrations_are_found_and_ordered():
    files = migration_files()
    names = [f.name for f in files]
    assert names == sorted(names)
    assert "0001_init.sql" in names
    assert all(name.endswith(".sql") for name in names)


# ── a virgin database ────────────────────────────────────────────────────


def test_a_virgin_database_gets_every_file_in_order(tmp_path):
    for name in ("0001_a.sql", "0002_b.sql"):
        (tmp_path / name).write_text(f"create table {name[5]}x (id int);\n",
                                     encoding="utf-8")
    db = FakeDb(tables=())
    report = _apply(db, directory=tmp_path)

    assert report.applied == ("0001_a.sql", "0002_b.sql")
    applied_sql = [sql for sql in db.executed if "create table ax" in sql
                   or "create table bx" in sql]
    assert len(applied_sql) == 2
    assert "ax" in applied_sql[0] and "bx" in applied_sql[1]


def test_every_applied_file_is_recorded_with_its_digest(tmp_path):
    (tmp_path / "0001_a.sql").write_text("select 1;\n", encoding="utf-8")
    db = FakeDb(tables=())
    _apply(db, directory=tmp_path)

    (digest,) = [migration_files(tmp_path)[0].digest]
    assert db.tracked == {"0001_a.sql": digest}


def test_each_file_applies_inside_its_own_transaction(tmp_path):
    for name in ("0001_a.sql", "0002_b.sql", "0003_c.sql"):
        (tmp_path / name).write_text("select 1;\n", encoding="utf-8")
    db = FakeDb(tables=())
    _apply(db, directory=tmp_path)
    assert db.transactions_opened == 3


def test_running_it_twice_is_a_noop_the_second_time_and_says_so(tmp_path):
    (tmp_path / "0001_a.sql").write_text("select 1;\n", encoding="utf-8")
    db = FakeDb(tables=())
    _apply(db, directory=tmp_path)

    lines = []
    second = _apply(db, directory=tmp_path, out=lines.append)
    assert second.applied == ()
    assert second.pending == ()
    assert any("nothing to apply" in line for line in lines)


# ── the dry run ──────────────────────────────────────────────────────────


def test_the_dry_run_names_every_pending_file_and_changes_nothing(tmp_path):
    for name in ("0001_a.sql", "0002_b.sql"):
        (tmp_path / name).write_text("create table t (id int);\n",
                                     encoding="utf-8")
    db = FakeDb(tables=())
    lines = []
    report = _apply(db, directory=tmp_path, dry_run=True, out=lines.append)

    assert report.pending == ("0001_a.sql", "0002_b.sql")
    assert report.applied == ()
    assert db.executed == []          # not even the tracking table
    assert db.tracked is None
    named = " ".join(lines)
    assert "0001_a.sql" in named and "0002_b.sql" in named


# ── refusing a database it cannot identify ───────────────────────────────


def test_tables_with_no_record_are_refused_and_named():
    db = FakeDb(tables={"kb_chunks", "traces"})
    with pytest.raises(MigrateError) as refusal:
        _apply(db)
    message = str(refusal.value)
    assert "kb_chunks" in message and "traces" in message
    assert "--allow-existing" in message
    assert db.executed == []


def test_allow_existing_proceeds_over_a_hand_pasted_database(tmp_path):
    (tmp_path / "0001_a.sql").write_text(
        "create table if not exists kb_chunks (id int);\n", encoding="utf-8")
    db = FakeDb(tables={"kb_chunks"})
    report = _apply(db, directory=tmp_path, allow_existing=True)
    assert report.applied == ("0001_a.sql",)
    assert db.tracked is not None


def test_a_table_no_migration_creates_is_called_unrecognised():
    db = FakeDb(tables={"wp_posts"})
    with pytest.raises(MigrateError) as refusal:
        _apply(db)
    assert "wp_posts" in str(refusal.value)
    assert "recognise" in str(refusal.value)


def test_a_recorded_digest_that_no_longer_matches_is_refused(tmp_path):
    (tmp_path / "0001_a.sql").write_text("select 1;\n", encoding="utf-8")
    db = FakeDb(tracked={"0001_a.sql": "0" * 16})
    with pytest.raises(MigrateError) as refusal:
        _apply(db, directory=tmp_path)
    message = str(refusal.value)
    assert "0001_a.sql" in message and "rewritten" in message


def test_a_recorded_file_missing_from_the_repo_is_refused(tmp_path):
    (tmp_path / "0001_a.sql").write_text("select 1;\n", encoding="utf-8")
    db = FakeDb(tracked={"0001_a.sql": migration_files(tmp_path)[0].digest,
                         "9999_gone.sql": "f" * 16})
    with pytest.raises(MigrateError) as refusal:
        _apply(db, directory=tmp_path)
    assert "9999_gone.sql" in str(refusal.value)


def test_a_tracked_database_applies_only_what_is_pending(tmp_path):
    for name in ("0001_a.sql", "0002_b.sql"):
        (tmp_path / name).write_text(f"-- {name}\n", encoding="utf-8")
    first = migration_files(tmp_path)[0]
    db = FakeDb(tables={"kb_chunks"}, tracked={first.name: first.digest})

    report = _apply(db, directory=tmp_path)
    assert report.pending == ("0002_b.sql",)
    assert report.applied == ("0002_b.sql",)


# ── the report is honest about what it did ───────────────────────────────


def test_the_report_never_reports_a_skip_as_a_load(tmp_path):
    (tmp_path / "0001_a.sql").write_text("select 1;\n", encoding="utf-8")
    db = FakeDb(tables=())
    _apply(db, directory=tmp_path)

    lines = []
    second = _apply(db, directory=tmp_path, out=lines.append)
    assert isinstance(second, Report)
    assert second.recorded == ("0001_a.sql",)
    assert not any("applied" in line and "0001" in line for line in lines)


# ── against the real database, in a throwaway schema ────────────────────


@pytest.mark.integration
class TestAgainstLivePostgres:
    """Opt-in: `pytest -m integration`. Applies the real files into a schema
    created for the test and dropped after it — the default schema is never
    touched by a test."""

    SCHEMA = "calmline_migrate_selftest"

    def _connect(self):
        from src.config import MissingConfigError, load_config
        try:
            config = load_config()
        except MissingConfigError:
            pytest.skip("no live DATABASE_URL")
        import asyncpg

        return asyncpg.connect(config.DATABASE_URL,
                               statement_cache_size=0)

    def test_the_real_files_apply_twice_into_a_throwaway_schema(self):
        async def scenario():
            conn = await self._connect()
            try:
                await conn.execute(
                    f'drop schema if exists {self.SCHEMA} cascade')
                await conn.execute(f'create schema {self.SCHEMA}')
                await conn.execute(
                    f'set search_path to {self.SCHEMA}, public, extensions')

                first = await apply_migrations(conn, out=lambda line: None)
                assert first.applied == first.pending
                assert len(first.applied) >= 4

                second = await apply_migrations(conn, out=lambda line: None)
                assert second.applied == ()

                tables = {row["table_name"] for row in await conn.fetch(
                    "select table_name from information_schema.tables "
                    "where table_schema = $1", self.SCHEMA)}
                for expected in ("parties", "policies", "transactions",
                                 "contact_notes", "schema_migrations"):
                    assert expected in tables
            finally:
                await conn.execute(
                    f'drop schema if exists {self.SCHEMA} cascade')
                await conn.close()

        asyncio.run(scenario())
