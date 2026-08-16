"""Write the world to files a person can read.

    python -m world.dataset --seed 11

Runs by hand, spends nothing, reads no clock, and its output is committed and
reviewed before any of it becomes data. Running it twice writes the same bytes.

It **reads back what it just wrote** and refuses to report success on a dataset
its own reader will not accept — a writer that cannot be read is a writer that
has not finished, and finding that out at load time is finding it out too late.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from world import WORLD_BIRTH_DATE
from world.dataset import (
    DEFAULT_ROOT,
    World,
    carried_queue,
    carried_stories,
    read_world,
    write_world,
)
from world.lifetimes.build import build_book


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--born", default=WORLD_BIRTH_DATE.isoformat(),
                        help="the world's birth date — never the wall clock")
    parser.add_argument("--out", default=str(DEFAULT_ROOT))
    args = parser.parse_args()

    born = date.fromisoformat(args.born)
    root = Path(args.out)

    book = build_book(seed=args.seed, born=born)
    if book.report.refusals:
        # A refused movement stops its policy. Writing the survivors would put a
        # book on disk that is quietly short of the two hundred it claims.
        print(f"REFUSED — {len(book.report.refusals)} movements were not built:")
        for refusal in book.report.refusals[:20]:
            print(f"  {refusal}")
        raise SystemExit(1)

    # The prose and the live queue are carried across, never rebuilt.
    # `build_book` returns the numbers and nothing else, so a rerun that did
    # not read the files first would write an empty `stories.jsonl` over two
    # hundred policies of hand-written history — and silently throw away
    # whatever live work the queue step had opened.
    world = World.of(book, seed=args.seed, born=born,
                     stories=carried_stories(root),
                     queue=carried_queue(root))
    write_world(world, root)

    # The writer's own output, through the reader that will load it.
    read_back = read_world(root)
    if read_back != world:
        raise SystemExit(f"{root}: written and read back are not the same world")

    # The sheet is rendered from what was just written, never maintained by
    # hand: an answer key that drifts sends a handler to a policy that has
    # moved, which is worse than having no key at all.
    from world.reference import write_sheet

    write_sheet(read_back, root / "reference-sheet.md")

    print(f"wrote {len(world.policies)} policies → {root}")
    print(f"  seed {args.seed} · born {born.isoformat()} · "
          f"{world.movements} movements · {len(world.people)} people")
    print(f"  {len(world.trusts)} trusts · {len(world.adviser_mandates)} "
          f"adviser mandates · "
          f"{sum(len(a) for a in world.authorities.values())} authorities")
    for name in ("people.jsonl", "policies.jsonl", "stories.jsonl",
                 "manifest.json", "reference-sheet.md"):
        size = (root / name).stat().st_size
        print(f"  {name:20} {size:>9,} bytes")


if __name__ == "__main__":
    main()
