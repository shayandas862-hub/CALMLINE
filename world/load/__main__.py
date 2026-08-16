"""Load the committed world into the configured database.

    .venv/bin/python -m world.load --dry-run
    .venv/bin/python -m world.load
    .venv/bin/python -m world.load --schema rehearsal --only LP-20000137

Reads `data/world/` through the same refusing reader the console boots on, so
nothing can be loaded that the console would not accept. The target must
already be migrated (`scripts/migrate.py`); this command never applies schema.
`--schema` points at a named schema for rehearsals and never creates one —
a rehearsal against a schema that does not exist should say so, not invent it.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

from world.dataset import DEFAULT_ROOT, DatasetError, read_world
from world.load import LoadError, load_world

_SCHEMA_RE = re.compile(r"[a-z_][a-z0-9_]{0,62}")


async def _amain(args: argparse.Namespace) -> int:
    import asyncpg

    from src.config import load_config

    world = read_world(Path(args.root))
    print(f"read {len(world.policies)} policies · {world.movements} movements "
          f"· {len(world.stories)} stories from {args.root}")
    if args.dry_run:
        print("dry run — nothing connected, nothing loaded")
        return 0

    config = load_config()
    conn = await asyncpg.connect(config.DATABASE_URL, statement_cache_size=0)
    try:
        if args.schema:
            if not _SCHEMA_RE.fullmatch(args.schema):
                raise LoadError(f"{args.schema!r} is not a schema name this "
                                f"loader will target")
            await conn.execute(
                f"set search_path to {args.schema}, public, extensions")
            print(f"targeting schema {args.schema}")
        only = frozenset(args.only.split(",")) if args.only else None
        await load_world(conn, world, only=only)
        return 0
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(DEFAULT_ROOT),
                        help="the dataset to load (default: data/world)")
    parser.add_argument("--schema", default=None,
                        help="target a named, already-migrated schema "
                             "(rehearsals; never created here)")
    parser.add_argument("--only", default=None,
                        help="comma-separated policy numbers — the rehearsal "
                             "seam; a real load takes the whole book")
    parser.add_argument("--dry-run", action="store_true",
                        help="read and verify the dataset, connect to nothing")
    try:
        return asyncio.run(_amain(parser.parse_args()))
    except (LoadError, DatasetError) as refusal:
        print(f"REFUSED — {refusal}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
