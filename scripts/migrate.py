"""Apply the SQL migrations, in order, exactly once — and refuse a database
this project cannot identify.

    .venv/bin/python scripts/migrate.py --dry-run
    .venv/bin/python scripts/migrate.py

Until now applying SQL was a manual paste into a web editor, which is how the
live project ended up **half-applied and unrecorded**: the corpus and trace
tables exist, the records half does not, and nothing wrote down what ran. This
runner keeps its own ledger (`schema_migrations`: filename, digest, when) and
treats that hand-pasted state as the *normal starting point*, not an anomaly —
it refuses by default, prints exactly what it found, and proceeds only under an
explicit `--allow-existing`, which is safe because every migration file here is
already written to be run twice (guarded creates, catalogue-checked triggers).

The digest matters because 0001 has already been rewritten in place once
(D-CL-006): a recorded digest that no longer matches the file means the SQL on
disk is not the SQL that was applied, and the honest response is a refusal, not
a shrug.

Business data never passes through here; the only row this script writes is its
own ledger, whose `applied_at` is bookkeeping and may default to now().
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "src" / "db" / "migrations"

TRACKING_DDL = """\
create table if not exists schema_migrations (
    filename   text primary key,
    sha256     text not null,
    applied_at timestamptz not null default now()
)"""

# What a migration file brings into (or removes from) the schema. Derived from
# the files rather than kept as a list beside them, so a new migration cannot
# forget to register its own tables.
_TABLE_RE = re.compile(
    r"(?:create table if not exists|drop table if exists)\s+([a-z_][a-z0-9_]*)",
    re.IGNORECASE)

_SCHEMA_RE = re.compile(r"[a-z_][a-z0-9_]{0,62}")


class MigrateError(RuntimeError):
    """A database this runner will not touch, and the reason."""


@dataclass(frozen=True)
class MigrationFile:
    name: str
    sql: str
    digest: str


@dataclass(frozen=True)
class Report:
    """What one run found and did. `recorded` is the ledger *after* the run,
    so a no-op second run still states what the database already holds."""

    schema: str
    state: str
    pending: tuple[str, ...]
    applied: tuple[str, ...]
    recorded: tuple[str, ...]


def migration_files(directory: Optional[Path] = None) -> tuple[MigrationFile, ...]:
    """Every .sql file, ordered by filename — the order they were written in."""
    directory = Path(directory) if directory else MIGRATIONS_DIR
    files = []
    for path in sorted(directory.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]
        files.append(MigrationFile(name=path.name, sql=sql, digest=digest))
    return tuple(files)


# ── looking before touching ──────────────────────────────────────────────


async def _inventory(conn: Any) -> tuple[str, set[str], Optional[dict[str, str]]]:
    """``(schema, base tables, ledger or None)`` for the connection's target."""
    schema = await conn.fetchval("select current_schema()")
    rows = await conn.fetch(
        "select table_name from information_schema.tables "
        "where table_schema = $1 and table_type = 'BASE TABLE'", schema)
    tables = {row["table_name"] for row in rows}

    tracked: Optional[dict[str, str]] = None
    if "schema_migrations" in tables:
        recorded = await conn.fetch(
            "select filename, sha256 from schema_migrations")
        tracked = {row["filename"]: row["sha256"] for row in recorded}
    return schema, tables - {"schema_migrations"}, tracked


def _identify(files: tuple[MigrationFile, ...], tables: set[str],
              tracked: Optional[dict[str, str]],
              allow_existing: bool) -> tuple[str, tuple[str, ...]]:
    """``(state, pending filenames)`` — or the refusal.

    Three honest states: a **tracked** database follows its own ledger; an
    **empty** one is virgin and gets everything; one holding **untracked
    tables** is refused until the operator says the tables are this project's.
    """
    by_name = {file.name: file for file in files}

    if tracked is not None:
        for name, digest in sorted(tracked.items()):
            local = by_name.get(name)
            if local is None:
                raise MigrateError(
                    f"the database records {name} as applied, but no such file "
                    f"exists in this repository — this database was migrated "
                    f"by something this checkout does not have")
            if local.digest != digest:
                raise MigrateError(
                    f"{name} was rewritten after it was applied: the database "
                    f"records digest {digest}, the file on disk is "
                    f"{local.digest}. The SQL that ran is not the SQL in the "
                    f"repo — refusing rather than pretending they match")
        pending = tuple(f.name for f in files if f.name not in tracked)
        return "tracked", pending

    if not tables:
        return "empty", tuple(file.name for file in files)

    known = {name for file in files for name in _TABLE_RE.findall(file.sql)}
    ours = sorted(tables & known)
    foreign = sorted(tables - known)
    if foreign:
        raise MigrateError(
            f"schema holds tables no migration here creates: "
            f"{', '.join(foreign)} — this does not look like a database this "
            f"project recognises, so nothing was touched")
    if not allow_existing:
        raise MigrateError(
            f"tables exist but nothing records how they got there: "
            f"{', '.join(ours)}. If these are this project's own tables from "
            f"the hand-paste era, rerun with --allow-existing; every file is "
            f"safe to run over them (guarded creates). Nothing was touched")
    return "untracked tables adopted", tuple(file.name for file in files)


# ── applying ─────────────────────────────────────────────────────────────


async def apply_migrations(conn: Any, *, directory: Optional[Path] = None,
                           dry_run: bool = False, allow_existing: bool = False,
                           out: Callable[[str], None] = print) -> Report:
    """Plan against what the database actually is, print the plan, then apply.

    Each file runs inside its own transaction with its ledger row, so a run
    killed mid-file leaves that file wholly unapplied and wholly unrecorded.
    """
    files = migration_files(directory)
    schema, tables, tracked = await _inventory(conn)
    state, pending = _identify(files, tables, tracked, allow_existing)

    out(f"migrate: schema {schema} — {state}, "
        f"{len(tracked or ())} recorded, {len(files)} files in repo")
    if not pending:
        out(f"nothing to apply — all {len(files)} files already recorded")
        return Report(schema=schema, state=state, pending=(), applied=(),
                      recorded=tuple(sorted(tracked or ())))
    for name in pending:
        out(f"  {'would apply' if dry_run else 'will apply'} {name}")
    if dry_run:
        return Report(schema=schema, state=state, pending=pending, applied=(),
                      recorded=tuple(sorted(tracked or ())))

    if tracked is None:
        await conn.execute(TRACKING_DDL)
        tracked = {}

    by_name = {file.name: file for file in files}
    applied = []
    for name in pending:
        file = by_name[name]
        async with conn.transaction():
            await conn.execute(file.sql)
            await conn.execute(
                "insert into schema_migrations (filename, sha256) "
                "values ($1, $2)", file.name, file.digest)
        tracked[file.name] = file.digest
        applied.append(file.name)
        out(f"  applied {name}")

    return Report(schema=schema, state=state, pending=pending,
                  applied=tuple(applied), recorded=tuple(sorted(tracked)))


# ── the command ──────────────────────────────────────────────────────────


async def _amain(args: argparse.Namespace) -> int:
    import asyncpg

    # Runnable as `python scripts/migrate.py` — the documented invocation —
    # not only as a module: the repo root joins the path the way
    # run_console.py's does, deferred to here so importing this module for
    # its functions never touches sys.path.
    sys.path.insert(0, str(MIGRATIONS_DIR.parents[2]))
    from src.config import load_config

    config = load_config()
    # statement_cache_size=0: safe under Supabase's transaction-mode pooler,
    # where server-side prepared statements do not survive between queries.
    conn = await asyncpg.connect(config.DATABASE_URL, statement_cache_size=0)
    try:
        if args.schema:
            if not _SCHEMA_RE.fullmatch(args.schema):
                raise MigrateError(f"{args.schema!r} is not a schema name "
                                   f"this runner will create")
            await conn.execute(f"create schema if not exists {args.schema}")
            await conn.execute(
                f"set search_path to {args.schema}, public, extensions")
            print(f"targeting schema {args.schema}")
        await apply_migrations(conn, dry_run=args.dry_run,
                               allow_existing=args.allow_existing)
        return 0
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan and change nothing")
    parser.add_argument("--allow-existing", action="store_true",
                        help="proceed over untracked tables that this "
                             "project's own migrations create")
    parser.add_argument("--schema", default=None,
                        help="target a named schema instead of the default "
                             "(created if missing; used for rehearsals)")
    try:
        return asyncio.run(_amain(parser.parse_args()))
    except MigrateError as refusal:
        print(f"REFUSED — {refusal}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
