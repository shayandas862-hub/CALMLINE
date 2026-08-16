"""The 5% tax-deferred withdrawal allowance — `02-BOND:4.2`.

> Withdraw up to **5% of the amount invested per policy year** with no immediate
> tax; **cumulative** (unused carries forward) up to 100% of the amount
> invested. A **deferral, not an exemption** — withdrawals re-enter the final
> gain calculation. Each top-up starts its own 5% clock (§7).

Three ways to get this wrong, each producing a book that is internally
consistent and externally false:

1. **Five percent of the current value.** It is 5% of the *amount invested*,
   for the life of the bond. A bond that took £100,000 and is now worth £150,000
   still has a £5,000 annual allowance. The current value is not a parameter of
   anything in this module, so the mistake cannot be made here.
2. **Forgetting the 100% ceiling.** The allowance stops accruing once it equals
   the amount invested — twenty policy years, and no more after that.
3. **Testing an excess on the day of the withdrawal.** `02-BOND:4.3` tests it
   **at policy-year end**, so a year's withdrawals are judged together.

`02-BOND:5` gives the arithmetic to check against: £100,000 invested, £50,000
withdrawn in year 2, excess "£50,000 − 2×5% allowance" = £40,000.

**A contradiction inside the corpus, resolved here and logged.** The `02-BOND`
specimen (£120,000 invested 2019-03-01) states "cumulative allowance used
£36,000 of £42,000" — at the world's birth date that is policy year 8, and
£42,000 is seven allowances, i.e. complete years *elapsed*. `02-BOND:4.2` and the
§5 worked example both give N allowances in policy year N. **The rule sections
win**: they carry explicit arithmetic, they match the real rule (ITTOIA s.507,
where each insurance year's allowance is available in that year), and a specimen
record is a record rather than a rule.
"""

from __future__ import annotations

from datetime import date

ANNUAL_ALLOWANCE_BP = 500     # 5% per policy year
MAX_CUMULATIVE_BP = 10_000    # capped at 100% of the amount invested
BASIS_POINTS_IN_WHOLE = 10_000


def policy_year_of(invested_on: date, on: date) -> int:
    """Which policy year ``on`` falls in, counting the first as 1.

    Policy years, not tax years and not calendar years: the bond's own clock
    starts the day the money went in, which is what `02-BOND:4.2` reckons by.
    """
    if on < invested_on:
        raise ValueError(
            f"{on.isoformat()} is before the bond was invested on "
            f"{invested_on.isoformat()}")
    years = on.year - invested_on.year
    if (on.month, on.day) < (invested_on.month, invested_on.day):
        years -= 1
    return years + 1


def cumulative_allowance_pence(invested_pence: int, policy_year: int) -> int:
    """Everything that has accrued by ``policy_year``, ceiling applied."""
    if policy_year < 1:
        raise ValueError(f"policy years start at 1, got {policy_year}")
    accrued_bp = min(ANNUAL_ALLOWANCE_BP * policy_year, MAX_CUMULATIVE_BP)
    return invested_pence * accrued_bp // BASIS_POINTS_IN_WHOLE


def remaining_allowance_pence(invested_pence: int, *, policy_year: int,
                              used_pence: int) -> int:
    """What is still available to draw tax-deferred. Never negative — an
    overdrawn allowance is an excess, and excesses are counted separately."""
    accrued = cumulative_allowance_pence(invested_pence, policy_year)
    return max(0, accrued - used_pence)


def excess_pence(withdrawal_pence: int, invested_pence: int, *,
                 policy_year: int, used_pence: int) -> int:
    """The part of ``withdrawal_pence`` above the remaining allowance.

    This is the figure `02-BOND:4.3` assesses as a chargeable event, and
    `02-BOND:4.9` warns "can create an artificially huge gain unrelated to real
    growth" — which is exactly why it is computed from the allowance rather
    than from anything the fund did.
    """
    remaining = remaining_allowance_pence(invested_pence,
                                          policy_year=policy_year,
                                          used_pence=used_pence)
    return max(0, withdrawal_pence - remaining)
