"""Segments — the bond's identical mini-policies.

`02-BOND:3.1` — "Issued as identical mini-policies ("segments"; Aldercrest
default **1,000**), enabling tax-efficient surrender of whole segments (§4.9)."

`02-BOND:4.9` is why segments exist at all, and why a segment surrender must
never be modelled as the same event as a partial withdrawal:

> (a) **partial withdrawal across all segments** — taxed only on the excess over
> the cumulative 5% allowance, but a large withdrawal early on can create an
> **artificially huge gain** unrelated to real growth; (b) **full surrender of
> whole segments** — gain per segment = proceeds − premium share, usually
> tracking real growth.

Same cash, very different tax. Collapsing them into one "withdrawal" would erase
the comparison `02-BOND:4.9` says the AI must surface before processing.

**A segment is indivisible.** Half a segment does not exist, so a segment
surrender takes whole ones and lands on a round multiple of the segment value.
"""

from __future__ import annotations

DEFAULT_SEGMENTS = 1_000


def segment_value_pence(value_pence: int, segments_remaining: int) -> int:
    """What one segment is worth. Whole pence, floor — the remainder stays in
    the bond rather than being conjured into a segment that is worth more than
    the fund can pay."""
    if segments_remaining <= 0:
        return 0
    return value_pence // segments_remaining


def segments_for_amount(wanted_pence: int, segment_value: int, *,
                        segments_remaining: int) -> int:
    """How many whole segments to surrender to raise about ``wanted_pence``.

    Rounds **down**, so a surrender never raises more than was asked for, and is
    capped at what is left — `HorizonBondTerms` refuses a remaining count
    outside 0…total, and the cap here is what keeps it inside.
    """
    if wanted_pence <= 0 or segment_value <= 0 or segments_remaining <= 0:
        return 0
    return min(wanted_pence // segment_value, segments_remaining)
