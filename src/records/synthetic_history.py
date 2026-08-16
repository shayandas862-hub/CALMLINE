"""The 80 synthetic holders, and the histories derived for them at seed time.

`data/synthetic/policyholders.jsonl` is an **identity manifest** (D-CL-022): who
exists, when they were born, where they live, which product they hold. It
carries no dates and no money, so none of the history below is stored — it is
derived, from a fixed seed plus the injected as-of date. Same inputs, same book.

Start dates span 3–60 years back, banded per product (D-CL-029) and always
age-consistent, so the oldest policies sit with the oldest holders. Histories
are **sparse and product-shaped** — an opening, a handful of dated events per
decade — not dense monthly ledgers, and every row is written through the real
store API so append-only, overdraw refusal and the change journal apply to seed
data exactly as they do to a handler's.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from typing import Any

from src.records.models import Contact, LifeAssured, Party, Policy, Transaction, VulnerabilityFlag
from src.records.products import (
    Allowance5Pct,
    ContributionSchedule,
    CoverComponent,
    FundHolding,
    HorizonBondTerms,
    MpaaStatus,
    PensionTax,
    RetirementAccountTerms,
)

MANIFEST_PATH = "data/synthetic/policyholders.jsonl"
RNG_SEED = 20260713

# The eras each product could plausibly have been sold in (D-CL-029).
PRODUCT_MAX_YEARS = {"lifelong_protection": 60, "horizon_bond": 40,
                     "retirement_account": 38}
MIN_YEARS = 3
ADULT = 18

# Both ends of the range are guaranteed rather than hoped for: the oldest
# eligible holders are placed deliberately, and a few policies are made new.
FORCED_OLD = 4        # > 40 years — only LP's band reaches that far
FORCED_YOUNG = 4      # 3–5 years

FUND_SPLITS = {"horizon_bond": (("ALD-MG", "Managed Growth", 60, 65),
                                ("ALD-WP", "With-Profits", 40, 65)),
               "retirement_account": (("ALD-TD", "Target-Date", 70, 22),
                                      ("ALD-GI", "Global Index", 30, 22))}


def load_manifest(path: str = MANIFEST_PATH) -> "list[dict[str, Any]]":
    """The identity rows, in file order."""
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _years_between(start: str, end: str) -> float:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days / 365.25


def _max_years(row: dict, as_at: str) -> int:
    """The oldest this policy could be: its product's band, capped by the
    holder having been an adult when it started."""
    adult_years = int(_years_between(row["dob"], as_at)) - ADULT
    return max(MIN_YEARS, min(PRODUCT_MAX_YEARS[row["policy"]["product"]], adult_years))


def _start_date(as_at: str, years: int, row: dict, rng: random.Random) -> str:
    """A start date at least ``years`` before ``as_at``, never older than the
    product's band, and never before the holder's eighteenth birthday.

    Scattering by whole days rather than by picking a random month is what keeps
    the age inside the band it was assigned — a random month can otherwise land
    past the as-of date and quietly turn a 3-year policy into a 2-year one. The
    adult boundary is computed in days from the actual date of birth rather than
    in whole years, so truncation cannot leave a holder 17 at inception.
    """
    latest = date.fromisoformat(as_at)
    adult_on = date.fromisoformat(row["dob"]) + timedelta(days=int(ADULT * 365.25))
    band_days = int(PRODUCT_MAX_YEARS[row["policy"]["product"]] * 365.25)
    lo = int(years * 365.25)
    hi = max(lo, min(lo + 300, band_days, (latest - adult_on).days))
    return (latest - timedelta(days=rng.randint(lo, hi))).isoformat()


def _within_life(start_date: str, as_at: str, fraction: float) -> str:
    """A date at ``fraction`` through the policy's life — always in range."""
    start = date.fromisoformat(start_date)
    span = (date.fromisoformat(as_at) - start).days
    return (start + timedelta(days=int(span * fraction))).isoformat()


def _assign_ages(rows: "list[dict]", as_at: str, rng: random.Random) -> "list[int]":
    """One age in years per row, spanning the directed range."""
    caps = [_max_years(row, as_at) for row in rows]
    ages: "list[int | None]" = [None] * len(rows)

    # The oldest end first: only LP's band reaches past 40, so the forced-old
    # slots go to the LP holders who were born early enough to carry them.
    oldest = sorted((i for i, row in enumerate(rows)
                     if row["policy"]["product"] == "lifelong_protection"
                     and caps[i] > 40),
                    key=lambda i: caps[i], reverse=True)
    for index in oldest[:FORCED_OLD]:
        ages[index] = rng.randint(41, min(60, caps[index]))

    # Then the newest end, from rows not already used.
    for index in [i for i in range(len(rows)) if ages[i] is None][:FORCED_YOUNG]:
        ages[index] = rng.randint(MIN_YEARS, 5)

    for index, cap in enumerate(caps):
        if ages[index] is None:
            ages[index] = rng.randint(MIN_YEARS, cap)
    return [age for age in ages if age is not None]


def _party_from(row: dict) -> Party:
    flag = row.get("vulnerability_flag")
    contact = row["contact"]
    return Party(
        party_id=row["party_id"], name=row["name"], dob=row["dob"],
        registered_address=row["registered_address"],
        contact=Contact(phone=contact["phone"], email=contact["email"],
                        registered=contact["registered"]),
        scottish_taxpayer=row.get("scottish_taxpayer", False),
        vulnerability_flag=None if not flag else VulnerabilityFlag(
            support_needs_ref=flag["support_needs_ref"], category=flag["category"]))


def _round_pounds(pence: int) -> int:
    """Money the book states in whole pounds, as integer pence."""
    return int(round(pence / 100.0)) * 100


def seed_synthetics(book: Any, *, manifest_path: str = MANIFEST_PATH,
                    as_at: str, rng_seed: int = RNG_SEED) -> None:
    """Add every manifest holder, their policy and its derived history."""
    rows = load_manifest(manifest_path)
    rng = random.Random(rng_seed)
    ages = _assign_ages(rows, as_at, rng)

    for row, age in zip(rows, ages):
        start_date = _start_date(as_at, age, row, rng)
        party = _party_from(row)
        seed = {"actor": "seed", "source_ref": "seed", "at": f"{as_at}T00:00:00"}
        book.add_party(party, **seed)

        policy_no = row["policy"]["policy_no"]
        product = row["policy"]["product"]
        book.add_policy(Policy(
            policy_no=policy_no, product=product, status="in_force",
            start_date=start_date, holder_party_id=party.party_id,
            lives_assured=(LifeAssured(name=party.name, party_id=party.party_id),),
            bank_last4=f"{rng.randint(0, 9999):04d}"), **seed)

        for fund_id, name, split, amc in FUND_SPLITS.get(product, ()):
            book.add_fund(FundHolding(fund_id=fund_id, fund_name=name, split_pct=split,
                                      amc_bp=amc, price_date=as_at), policy_no, **seed)

        builder = {"lifelong_protection": _lifelong_protection,
                   "horizon_bond": _horizon_bond,
                   "retirement_account": _retirement_account}[product]
        builder(book, policy_no, start_date, as_at, rng, seed)


def _commit(book: Any, policy_no: str, seq: int, kind: str, pence: int, at: str,
            reason: str) -> None:
    book.apply_transaction(policy_no, Transaction(
        txn_id=f"TXN-{policy_no}-{seq}", policy_no=policy_no, kind=kind,
        amount_pence=pence, reason=reason, actor="seed", at=f"{at}T00:00:00"))


def _decade_marks(start_date: str, as_at: str, rng: random.Random) -> "list[str]":
    """One dated point per full decade the policy has run, spread across its
    life and always strictly inside it."""
    decades = min(int(_years_between(start_date, as_at) // 10), 6)
    return [_within_life(start_date, as_at, (index + 1) / (decades + 1))
            for index in range(decades)]


def _lifelong_protection(book, policy_no, start_date, as_at, rng, seed) -> None:
    """Cover, a premium, and — only when unit-linked — a fund with a history."""
    unit_linked = rng.random() < 0.5
    basis = ("reviewable", "unit_linked") if unit_linked else (
        rng.choice(("guaranteed", "reviewable")),)
    sum_assured = _round_pounds(rng.randint(50_000, 500_000) * 100)
    book.add_cover(CoverComponent(
        policy_no=policy_no, sum_assured_pence=sum_assured, basis=basis,
        premium_pence=_round_pounds(rng.randint(20, 400) * 100),
        premium_frequency="monthly",
        next_review_date=None if not unit_linked else as_at), **seed)

    if not unit_linked:
        return          # protection-only cover has no fund to surrender

    balance = _round_pounds(int(sum_assured * rng.uniform(0.05, 0.2)))
    _commit(book, policy_no, 1, "opening", balance, start_date, "opening fund value")
    seq = 2
    for mark in sorted(_decade_marks(start_date, as_at, rng)):
        growth = _round_pounds(int(balance * rng.uniform(0.05, 0.25)))
        _commit(book, policy_no, seq, "credit_adjustment", growth, mark,
                "unit revaluation at the policy anniversary")
        balance += growth
        seq += 1
    if rng.random() < 0.3 and balance > 0:
        amount = _round_pounds(int(balance * rng.uniform(0.05, 0.15)))
        _commit(book, policy_no, seq, "withdrawal", amount,
                _within_life(start_date, as_at, rng.uniform(0.75, 0.98)),
                "partial surrender")


def _horizon_bond(book, policy_no, start_date, as_at, rng, seed) -> None:
    """An investment, an optional run of 5% withdrawals, and revaluations."""
    invested = _round_pounds(rng.randint(20_000, 250_000) * 100)
    age = int(_years_between(start_date, as_at))
    per_year = invested // 20                      # 5% of the amount invested

    # 5% a year is a 20-policy-year allowance in total; a run never exceeds it,
    # and never runs longer than the policy has existed.
    run = min(rng.randint(0, 12), max(0, age - 1), 20)
    used = per_year * run
    book.add_bond_terms(HorizonBondTerms(
        policy_no=policy_no, invested_pence=invested, invested_date=start_date,
        segments_total=1_000, segments_remaining=1_000,
        allowance_5pct=Allowance5Pct(used_pence=used,
                                     available_pence=max(0, invested - used),
                                     policy_year=max(1, age))), **seed)

    _commit(book, policy_no, 1, "opening", invested, start_date, "amount invested")
    seq = 2
    start_year = date.fromisoformat(start_date).year
    for index in range(run):
        _commit(book, policy_no, seq, "regular_withdrawal", per_year,
                f"{start_year + index + 1}-{date.fromisoformat(start_date).month:02d}-01",
                f"annual 5% withdrawal, policy year {index + 1}")
        seq += 1
    for mark in sorted(_decade_marks(start_date, as_at, rng)):
        _commit(book, policy_no, seq, "credit_adjustment",
                _round_pounds(int(invested * rng.uniform(0.05, 0.3))), mark,
                "investment growth to the anniversary valuation")
        seq += 1


def _retirement_account(book, policy_no, start_date, as_at, rng, seed) -> None:
    """An accumulated pot, then monthly contributions across recent years only."""
    member = _round_pounds(rng.randint(100, 800) * 100)
    employer = _round_pounds(rng.randint(50, 500) * 100)
    book.add_pension_terms(RetirementAccountTerms(
        policy_no=policy_no,
        contribution_schedule=ContributionSchedule(member_net_pence=member,
                                                   employer_gross_pence=employer,
                                                   frequency="monthly"),
        target_retirement_age=rng.choice((60, 65, 67))), **seed)
    book.add_pension_tax(PensionTax(policy_no=policy_no,
                                    mpaa_triggered=MpaaStatus(value=False)), **seed)

    pot = _round_pounds(rng.randint(5_000, 200_000) * 100)
    _commit(book, policy_no, 1, "opening", pot, start_date,
            "accumulated value carried at the policy's start")
    seq = 2

    age = int(_years_between(start_date, as_at))
    if age >= 5 and rng.random() < 0.4:
        _commit(book, policy_no, seq, "transfer_in",
                _round_pounds(rng.randint(5_000, 80_000) * 100),
                _within_life(start_date, as_at, rng.uniform(0.3, 0.8)),
                "transfer in from a workplace scheme")
        seq += 1

    monthly = member + employer
    for at in _recent_months(as_at, min(rng.randint(3, 6), max(1, age)) * 12, start_date):
        _commit(book, policy_no, seq, "contribution", monthly, at,
                "member net + employer gross")
        seq += 1


def _recent_months(as_at: str, count: int, not_before: str) -> "list[str]":
    """The first of each of the ``count`` months ending before ``as_at``."""
    year, month = int(as_at[:4]), int(as_at[5:7])
    months = []
    for _ in range(count):
        month -= 1
        if month == 0:
            year, month = year - 1, 12
        candidate = f"{year}-{month:02d}-01"
        if candidate < not_before:
            break
        months.append(candidate)
    return sorted(months)
