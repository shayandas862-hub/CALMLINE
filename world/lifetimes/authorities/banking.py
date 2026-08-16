"""Bank mandates — their verification state, their holds, and their history.

Every policy has a payment position, so this is a partition of all two hundred
rather than an overlay.

The change history is the **fraud watch**. `05-OPS:3.4` requires enhanced
verification for "an address change followed within 30 days by a bank change or
withdrawal", and "the bank was changed, then a large withdrawal went out two
weeks later" is only an answerable question because the mandate keeps its
changes in order, with dates. A mandate holding only its current details can
never answer it.

Bucket plan §7 wants eighteen changed **within 90 days of the world's birth
date**, computed from the birth-date constant rather than hardcoded — the window
moved once already when the birth date was settled.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Sequence

from src.records.authorisations import BankMandate, MandateChange
from src.records.models import Policy
from world.lifetimes.authorities.counts import (
    BANK_ON_HOLD,
    BANK_RECENTLY_CHANGED,
    BANK_UNVERIFIED,
    BOOK_SIZE,
    RECENT_CHANGE_WINDOW_DAYS,
)


def _last4(rng: random.Random) -> str:
    return f"{rng.randrange(0, 10_000):04d}"


def allocate_bank_mandates(policies: Sequence[Policy], *, seed: int,
                           born: date) -> dict[str, BankMandate]:
    """One bank position per policy, to the bucket plan's §7 partition."""
    if len(policies) < BOOK_SIZE:
        raise ValueError(
            f"§7 partitions {BOOK_SIZE} policies; got {len(policies)}")

    rng = random.Random(f"{seed}:bank")
    order = sorted(p.policy_no for p in policies)
    rng.shuffle(order)

    unverified = set(order[:BANK_UNVERIFIED])
    held = set(order[BANK_UNVERIFIED:BANK_UNVERIFIED + BANK_ON_HOLD])
    recent_from = BANK_UNVERIFIED + BANK_ON_HOLD
    recent = set(order[recent_from:recent_from + BANK_RECENTLY_CHANGED])

    earliest_recent = born - timedelta(days=RECENT_CHANGE_WINDOW_DAYS)
    allocated: dict[str, BankMandate] = {}

    for policy_no in sorted(order):
        history: list[MandateChange] = []
        if policy_no in recent:
            # Inside the window, and never on the birth date itself so that a
            # withdrawal can still follow it.
            changed = earliest_recent + timedelta(
                days=rng.randint(1, RECENT_CHANGE_WINDOW_DAYS - 21))
            history.append(MandateChange(
                at=f"{changed.isoformat()}T10:15:00",
                actor="back_office",
                note="bank details changed on the customer's instruction, "
                     "verified by enhanced verification (`05-OPS:3.4`)"))
        elif policy_no not in unverified and policy_no not in held \
                and rng.random() < 0.25:
            # An older change, well outside the window: ordinary history, and
            # what stops "has a change history" being the same fact as "recent".
            changed = born - timedelta(days=rng.randint(400, 3_000))
            history.append(MandateChange(
                at=f"{changed.isoformat()}T09:30:00",
                actor="back_office",
                note="bank details changed on the customer's instruction"))

        allocated[policy_no] = BankMandate(
            policy_no=policy_no,
            account_last4=_last4(rng),
            verified=policy_no not in unverified and policy_no not in held,
            hold_until=((born + timedelta(days=rng.randint(3, 30))).isoformat()
                        if policy_no in held else None),
            change_history=tuple(history),
        )
    return allocated


def changed_shortly_before(mandate: BankMandate, on: date, *,
                           within_days: int = 30) -> bool:
    """Whether the bank was changed shortly before ``on``.

    This is the pattern `05-OPS:3.4` watches for: a bank change followed by a
    withdrawal. ``on`` is **injected** — the day the withdrawal happened — and
    never read from the clock, or the same book would answer differently
    tomorrow.
    """
    if not mandate.change_history:
        return False
    last = date.fromisoformat(mandate.change_history[-1].at[:10])
    return 0 <= (on - last).days <= within_days
