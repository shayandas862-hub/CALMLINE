"""The Prequel — the world-builder.

Runs by hand, runs once, and is history afterwards. It invents Aldercrest's
book, checks every movement against the insurer's own rulebook as it goes, and
writes the result to files a person can read before any of it becomes data.

It imports the rulebook (`src/`). Nothing in `src/` imports it.
"""

from __future__ import annotations

from datetime import date

# The day the world stops.
#
# Frozen into the build rather than read from the clock, so a script run
# tomorrow produces the same book as one run today — and so "nothing is dated
# after the world's birth date" is a property of the data rather than an
# accident of when it was generated. Time runs normally *afterwards*, on a real
# clock, so case deadlines age honestly once the world is loaded.
#
# The identity generator's own `--as-of` is a **separate input** and is three
# days earlier (`2026-07-25`, the date `data/world/people.jsonl` was written).
# That file is not regenerated: ages struck three days early are immaterial for
# adult dates of birth, and rebuilding it would change every name, address and
# telephone number in a file that has already been read and approved.
WORLD_BIRTH_DATE = date(2026, 7, 28)

# The date `data/world/people.jsonl` was struck, and a **separate input** rather
# than a stale copy of the birth date. Named here because the dataset manifest
# has to record it: a reader given only one date cannot tell that the ages in
# the people file were computed three days earlier, and a world whose inputs are
# not written down is one nobody can reproduce.
PEOPLE_AS_OF = date(2026, 7, 25)

__all__ = ["PEOPLE_AS_OF", "WORLD_BIRTH_DATE"]
