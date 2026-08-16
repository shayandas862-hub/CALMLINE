"""Write the world's people to a file a person can read.

    python -m world.identities --seed 11 --as-of 2026-07-25

Runs by hand, spends nothing, and its output is committed and reviewed before
any of it becomes data.
"""

from __future__ import annotations

import argparse
from datetime import date

from world.identities import ADVISER_FIRM, generate_identities, write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--as-of", default="2026-07-25",
                        help="the world's birth date — never the wall clock")
    parser.add_argument("--holders", type=int, default=200)
    parser.add_argument("--out", default="data/world/people.jsonl")
    args = parser.parse_args()

    world = generate_identities(seed=args.seed,
                                as_of=date.fromisoformat(args.as_of),
                                holders=args.holders)
    write_jsonl(world, args.out)

    counts: dict[str, int] = {}
    for record in world:
        counts[record["role"]] = counts.get(record["role"], 0) + 1
    firms = counts.get(ADVISER_FIRM, 0)
    print(f"wrote {len(world)} records → {args.out}")
    print(f"  seed {args.seed} · as at {args.as_of} · {firms} adviser firms")
    for role in sorted(counts):
        print(f"  {role:26} {counts[role]:>4}")


if __name__ == "__main__":
    main()
