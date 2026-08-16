#!/usr/bin/env python3
"""Seed the Aldercrest KB into `kb_chunks` — embedding only what changed.

    python scripts/seed_corpus.py --check    # release gate only, no writes
    python scripts/seed_corpus.py --plan     # dry run: what a seed would do
    python scripts/seed_corpus.py            # seed for real

The release gate runs first, always: a corpus that fails validation is never
embedded. Then the run diffs against what the index already holds by
`content_hash`, so re-running over an untouched corpus costs nothing and a
tax-rate change costs two or three embeddings rather than a rebuild
(`data/kb/README.md` §5).

Needs `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` and `OPENAI_API_KEY`; the migration
must already be applied. Every secret is read through the validated `Config`,
which names all missing variables at once.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import MissingConfigError, load_config  # noqa: E402
from src.corpus.kb_parser import parse_kb  # noqa: E402
from src.corpus.kb_seed import plan_seed, read_index, seed_kb_chunks  # noqa: E402
from src.corpus.kb_validate import validate  # noqa: E402
from src.db.client import get_client  # noqa: E402

KB = Path(__file__).resolve().parent.parent / "data" / "kb"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    report = validate(KB)
    if not report.passed:
        print(f"FAIL — the corpus does not pass the release gate "
              f"({len(report.failures)} problem(s)); nothing will be embedded:")
        for failure in report.failures:
            print(f"  - {failure}")
        return 1
    print(f"gate: PASS — {report.chunk_count} chunks "
          f"({report.embedded_count} embeddable)")
    if "--check" in args:
        return 0

    chunks = parse_kb(KB)
    try:
        client = get_client(load_config())
    except MissingConfigError as error:
        print(f"FAIL — {error}")
        return 1

    if "--plan" in args:
        plan = plan_seed(chunks, read_index(client))
        print(f"plan: embed {plan.embedding_calls}, skip {len(plan.unchanged)} "
              f"unchanged, tombstone {len(plan.to_tombstone)}, "
              f"withhold {len(plan.withheld)} sample_record")
        if plan.to_tombstone:
            print(f"      tombstoning: {', '.join(plan.to_tombstone)}")
        return 0

    result = seed_kb_chunks(chunks, client)
    print(f"seeded: embedded {result.embedded}, skipped {result.skipped} "
          f"unchanged, tombstoned {result.tombstoned}, "
          f"withheld {result.withheld} sample_record")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
