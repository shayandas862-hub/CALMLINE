"""Who holds what, and whether they were old enough to.

Split out of ``allocation.py`` at the 300-line rule when v4.5 phase 3 added
the age check. One job: deciding which of the two hundred policies belong to
the same person, and which person that is.

The two halves are deliberately separate. **The plan decides the shape** — that
132 people hold one policy, 22 hold two and 8 hold three, and which policies
share a holder. **The relabelling decides the names**, and only the names, so
a person's holdings stay spread across time exactly as the plan drew them.
"""

from __future__ import annotations

import random
from datetime import date

# §1 — the holder mapping. 132 + 22×2 + 8×3 = 200 policies across 162 people.
# Defined here rather than in `allocation.py` because they describe holders, and
# because importing them back the other way would be a cycle.
HOLDS_ONE, HOLDS_TWO, HOLDS_THREE = 132, 22, 8

ADULT_YEARS = 18

def _holder_plan(rng: random.Random, holders: list[str]) -> list[str]:
    """§1 — which holder each of the 200 policies belongs to."""
    if len(holders) < HOLDS_ONE + HOLDS_TWO + HOLDS_THREE:
        raise ValueError(f"the plan needs 162 holders; got {len(holders)}")
    chosen = list(holders)
    rng.shuffle(chosen)
    assignments: list[str] = []
    cursor = 0
    for count, people in ((1, HOLDS_ONE), (2, HOLDS_TWO), (3, HOLDS_THREE)):
        for party_id in chosen[cursor:cursor + people]:
            assignments.extend([party_id] * count)
        cursor += people
    return assignments

def _age_consistent(holder_for: list[str], starts: list[date],
                    dobs: dict[str, date]) -> list[str]:
    """Re-label who holds what, so nobody holds a policy older than they are.

    Start dates are drawn from a per-product span and holders from a separate
    shuffle, and until v4.5 phase 3 the two were never compared: twenty-four of
    the two hundred began before their holder turned eighteen and one began two
    and a half years before the holder was born.

    **The shape is kept and only the labels move.** `_holder_plan` has already
    decided *which policies share a holder* — that a person holds one, two or
    three, and which ones. Reassigning those groups wholesale would cluster a
    person's policies into adjacent years; relabelling leaves each person's
    holdings spread across time exactly as drawn.

    Oldest person to the group whose earliest policy is earliest. Sorted pairing
    is optimal here, so if this raises, no assignment satisfies the constraint
    and the fault is in the spans or the people rather than in the pairing.
    """
    groups: dict[str, list[int]] = {}
    for index, party_id in enumerate(holder_for):
        groups.setdefault(party_id, []).append(index)

    # Each group ranked by the earliest policy it must accommodate, and each
    # candidate by age. Ties broken on the party id so the pairing is stable.
    by_start = sorted(groups.values(), key=lambda ix: (min(starts[i] for i in ix),
                                                       ix))
    by_age = sorted(groups, key=lambda pid: (dobs[pid], pid))

    relabelled = list(holder_for)
    for indices, party_id in zip(by_start, by_age):
        earliest = min(starts[i] for i in indices)
        if (earliest - dobs[party_id]).days / 365.25 < ADULT_YEARS:
            raise ValueError(
                f"{party_id} was born {dobs[party_id].isoformat()} and the "
                f"earliest policy left to allocate starts "
                f"{earliest.isoformat()} — no age-consistent assignment exists "
                f"for this book")
        for index in indices:
            relabelled[index] = party_id
    return relabelled
