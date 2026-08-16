"""The market — deterministic, shared, and able to fall.

A fund's return for a year is derived from the world seed, the fund's id and the
year, and from nothing else. Two consequences, both deliberate:

**The same fund returns the same figure in the same year on every policy.** That
is what makes it a market rather than a per-policy random walk. Without it 2008
is a bad year for some policyholders and a good one for others, and no question
about the book has a coherent answer.

**The same seed rebuilds the same market forever.** The derivation seeds
``random.Random`` with a *string*, which Python hashes with SHA-512 — stable
across processes, machines and runs. Python's built-in ``hash()`` is randomised
per process and would have made the world different on every run while looking
perfectly deterministic in a single session.

The stress years are real market history — the dot-com unwind, the financial
crisis, the pandemic, the 2022 rate shock. A synthetic market that only ever
drifts upward with noise would make every "why did my bond fall?" conversation
in the book impossible to have.
"""

from __future__ import annotations

import random
from datetime import date
from typing import Optional, Sequence

from src.records.products import FundHolding
from world.lifetimes.markets.funds import fund
from world.lifetimes.timeline import Movement

# Years the whole market fell, and roughly how hard, in basis points. Applied to
# every unit-linked fund on top of its own draw, so a crash is shared.
MARKET_STRESS: dict[int, int] = {
    2000: -1200,   # the dot-com unwind begins
    2001: -1500,
    2002: -2200,
    2008: -3400,   # the financial crisis
    2020: -900,    # the pandemic quarter
    2022: -1500,   # rates, and everything repriced at once
}

# The stress figures above are quoted for a fund of this spread. A fund is hit
# in proportion to its own — a cautious fund losing as much as a UK equity fund
# in 2008 would be a market nobody would recognise, and `spread_bp` already
# says how much risk each one carries, so it needs no second field to say it.
REFERENCE_SPREAD_BP = 1100


def annual_return_bp(fund_id: str, year: int, *, seed: int) -> int:
    """This fund's return for ``year``, in basis points. Signed.

    The draw is the mean of two uniform draws rather than one, which piles the
    mass near the fund's central return and makes the extremes rare. A single
    uniform draw made every fund fall in roughly half its years; real markets
    rise in about three years in four, and a book that falls half the time
    would misrepresent every long-run figure in it.
    """
    f = fund(fund_id)
    rng = random.Random(f"{seed}:{fund_id}:{year}")
    swing = (rng.randint(-f.spread_bp, f.spread_bp)
             + rng.randint(-f.spread_bp, f.spread_bp)) // 2
    drawn = f.mean_bp + swing
    if f.with_profits:
        # Smoothing (`02-BOND:3.6`): the declared bonus does not track the
        # market down, and a reversionary bonus once added cannot be removed —
        # so there is no mechanism here for a negative year. The falls a
        # with-profits holder feels come out at exit, as an MVR, which is a
        # surrender adjustment rather than a growth event.
        return max(0, drawn)
    stress = MARKET_STRESS.get(year, 0) * f.spread_bp // REFERENCE_SPREAD_BP
    return drawn + stress


def blended_return_bp(holdings: Sequence[FundHolding], year: int, *,
                      seed: int) -> int:
    """The whole policy's return, weighted by how it is split across funds."""
    if not holdings:
        return 0
    return sum(h.split_pct * annual_return_bp(h.fund_id, year, seed=seed)
               for h in holdings) // 100


def _slice_movement(value_pence: int, on: date, group: Sequence[FundHolding], *,
                    seed: int, rise: str, fall: str,
                    reason: str) -> Optional[Movement]:
    """One movement for one group of holdings that share a direction rule."""
    split = sum(h.split_pct for h in group)
    if split <= 0:
        return None
    held = value_pence * split // 100
    return_bp = sum(h.split_pct * annual_return_bp(h.fund_id, on.year, seed=seed)
                    for h in group) // split
    # `amount_pence` is a magnitude and the kind carries the direction, so the
    # sign is taken off here rather than pushed into the ledger.
    amount = held * abs(return_bp) // 10_000
    if amount == 0:
        return None
    return Movement(on=on, kind=rise if return_bp >= 0 else fall,
                    amount_pence=amount, reason=reason)


def growth_movements(value_pence: int, on: date,
                     holdings: Sequence[FundHolding], *,
                     seed: int) -> tuple[Movement, ...]:
    """What the funds did to ``value_pence`` in the year ending ``on``.

    Unit-linked holdings and with-profits holdings post **separately**, because
    they are separate events: unit growth can reverse next year, a declared
    reversionary bonus cannot (`02-BOND:3.6`). Blending them into one line would
    throw away the only fact that distinguishes them.

    Nothing is posted for a zero movement — a £0 row is noise in a history a
    person has to read.
    """
    if value_pence <= 0 or not holdings:
        return ()
    unit_linked = [h for h in holdings if not fund(h.fund_id).with_profits]
    with_profits = [h for h in holdings if fund(h.fund_id).with_profits]

    movements = (
        _slice_movement(value_pence, on, unit_linked, seed=seed,
                        rise="investment_return", fall="investment_loss",
                        reason="annual investment performance"),
        _slice_movement(value_pence, on, with_profits, seed=seed,
                        rise="bonus", fall="bonus",
                        reason="reversionary bonus declared"),
    )
    return tuple(m for m in movements if m is not None)
