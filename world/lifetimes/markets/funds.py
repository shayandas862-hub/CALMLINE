"""The fund catalogue — what a policy can be invested in, and how it behaves.

Every annual management charge here is inside the range its product master
states: `02-BOND:3.3` and `03-PEN:3.3` both say 0.10%–1.00%, `01-WOL:3.2` says
0.35%–1.00% for unit-linked whole of life. Two are quoted exactly, because the
sample records name them: Managed Growth at 0.65% (`02-BOND` specimen) and
Global Index at 0.22% (`03-PEN` specimen).

Charges are held in **basis points** rather than percentages — 0.65% is 65 —
because a rate held as a float makes every charge in the book a rounding, and
thirty years of roundings do not reconcile.

``mean_bp`` and ``spread_bp`` are the fund's character: where its annual return
centres, and how far a year can swing either side of that. They are this build's
own design, not a corpus figure, and they exist so that a cautious fund and an
equity fund do not behave identically.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fund:
    """One fund a policy can hold units in.

    ``with_profits`` is not a style label — it changes what the fund can do.
    `02-BOND:3.6` gives the with-profits fund an **annual (reversionary) bonus**
    which "normally cannot be removed", so it has no mechanism for a down year.
    It smooths, which is the whole point of it.
    """

    fund_id: str
    name: str
    amc_bp: int
    mean_bp: int
    spread_bp: int
    with_profits: bool = False


CATALOGUE: dict[str, Fund] = {
    f.fund_id: f for f in (
        # Named in the `02-BOND` sample record, at the charge it states.
        Fund("managed_growth", "Managed Growth", amc_bp=65,
             mean_bp=750, spread_bp=1100),
        # Named in the same sample. Smoothed: it declares, it does not track.
        Fund("with_profits", "With-Profits", amc_bp=55,
             mean_bp=400, spread_bp=150, with_profits=True),
        # Named in the `03-PEN` sample record, at the charge it states.
        Fund("global_index", "Global Index", amc_bp=22,
             mean_bp=800, spread_bp=1300),
        # Named in the `03-PEN` sample record; `03-PEN:3.2` lists target-date
        # funds as the default proposition.
        Fund("target_date_2036", "Target-Date 2036", amc_bp=45,
             mean_bp=620, spread_bp=800),
        Fund("cautious_managed", "Cautious Managed", amc_bp=40,
             mean_bp=450, spread_bp=550),
        Fund("uk_equity", "UK Equity", amc_bp=78,
             mean_bp=700, spread_bp=1400),
        # Whole of life's unit-linked option. Above 35bp, per `01-WOL:3.2`.
        Fund("protection_managed", "Protection Managed", amc_bp=85,
             mean_bp=560, spread_bp=700),
    )
}


def fund(fund_id: str) -> Fund:
    """The fund, or ``KeyError``. An unknown fund is never defaulted — a policy
    invested in something the insurer does not offer is a fact worth stopping
    for, not one worth guessing past."""
    return CATALOGUE[fund_id]
