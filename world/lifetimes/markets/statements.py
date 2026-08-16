"""When growth and charges post — annually, on the date each product reckons by.

Never monthly. A thirty-two-year policy deducting a charge every month is four
hundred ledger rows nobody can read, and the assistant has to *read* a policy's
history to answer a question about it.

Which annual date differs by product, and each choice comes from the corpus
rather than from tidiness:

- **Horizon Bond** — the **policy anniversary**. `02-BOND:4.2` runs the 5%
  tax-deferred allowance on *policy years*, so any other anchor would make the
  allowance year and the charging year disagree with each other.
- **Retirement Account** — **6 April**, the start of the UK tax year. The
  `03-PEN` specimen issues its annual statement on `2026-04-06`, and the annual
  allowance (`03-PEN:4.1`) is reckoned by tax year.
- **Lifelong Protection** — the **policy anniversary**. Premiums, premium
  reviews and indexation all reckon from it (`01-WOL:3.1`).

The first statement falls after the policy's first anniversary — a statement
covering three weeks is not an annual statement.
"""

from __future__ import annotations

from datetime import date

# The UK tax year opens on 6 April.
TAX_YEAR_START = (4, 6)

ANNIVERSARY_PRODUCTS = frozenset({"horizon_bond", "lifelong_protection"})
TAX_YEAR_PRODUCTS = frozenset({"retirement_account"})


def anniversary(start: date, year: int) -> date:
    """``start``'s anniversary in ``year``.

    29 February exists one year in four; the other three it falls back to the
    28th, rather than raising and stopping a policy that has done nothing wrong.
    """
    try:
        return start.replace(year=year)
    except ValueError:
        return date(year, 2, 28)


def _anniversary_dates(start: date, born: date) -> tuple[date, ...]:
    dates = []
    for year in range(start.year + 1, born.year + 1):
        due = anniversary(start, year)
        if start < due <= born:
            dates.append(due)
    return tuple(dates)


def _tax_year_dates(start: date, born: date) -> tuple[date, ...]:
    """Every 6 April after the policy's first anniversary."""
    first_anniversary = anniversary(start, start.year + 1)
    opening = date(first_anniversary.year, *TAX_YEAR_START)
    first_year = (first_anniversary.year if opening > first_anniversary
                  else first_anniversary.year + 1)
    return tuple(
        date(year, *TAX_YEAR_START)
        for year in range(first_year, born.year + 1)
        if date(year, *TAX_YEAR_START) <= born
    )


def statement_dates(product: str, start: date, *, born: date) -> tuple[date, ...]:
    """Every date this policy posts growth and charges on, oldest first.

    Nothing on the day it started — no year has passed to report on — and
    nothing after the world's birth date.
    """
    if product in ANNIVERSARY_PRODUCTS:
        return _anniversary_dates(start, born)
    if product in TAX_YEAR_PRODUCTS:
        return _tax_year_dates(start, born)
    raise ValueError(
        f"no statement basis for product {product!r} — the three Aldercrest "
        f"products are {sorted(ANNIVERSARY_PRODUCTS | TAX_YEAR_PRODUCTS)}"
    )
