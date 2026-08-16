"""Building one specimen policy per product, from its own corpus record.

Split out of ``anchors.py`` at the 300-line rule, before v4.5 phase 3 modified
it. One job: turning a parsed `III.4` record into the policy, cover, terms,
funds and ledger it describes.

Each specimen ledgers **exactly what its record states** (D-CL-028) — no premium
history the corpus does not give, no invented contributions.

Two records state a value their stated movements cannot reach. Rather than
adjust a figure to make the arithmetic work, the gap is carried by **one
explicitly-reasoned entry** whose reason says it is not itemised by the source
(D-CL-038). The alternative — spreading the difference through the withdrawals —
would make every individual row a small lie to make the total true.
"""

from __future__ import annotations

import re
from typing import Any

from src.records.models import LifeAssured, Policy, Transaction, Trust
from src.records.products import (
    Allowance5Pct,
    ContributionSchedule,
    CoverComponent,
    ExpressionOfWish,
    HorizonBondTerms,
    Indexation,
    MpaaStatus,
    PensionTax,
    RetirementAccountTerms,
    TransferIn,
)
from src.records.sample_record import (
    SampleRecord,
    adviser_loa_from,
    funds_from,
    months_before,
    reversed_date,
    parse_all_money,
    parse_date,
    parse_money,
)

PRODUCT_BY_PREFIX = {"LP": "lifelong_protection", "HB": "horizon_bond",
                     "RA": "retirement_account"}


def seed_stamp(at: str) -> dict[str, str]:
    return {"actor": "seed", "source_ref": "seed", "at": at}


def txn(policy_no: str, seq: int, kind: str, pence: int, at: str,
        reason: str) -> Transaction:
    return Transaction(txn_id=f"TXN-{policy_no}-{seq}", policy_no=policy_no,
                       kind=kind, amount_pence=pence, reason=reason,
                       actor="seed", at=f"{at}T00:00:00")


def _base_policy(record: SampleRecord, party_id: str, start_date: str,
                 **extra) -> Policy:
    policy_no = record.require("policy_no")
    return Policy(policy_no=policy_no, product=PRODUCT_BY_PREFIX[policy_no[:2]],
                  status="in_force", start_date=start_date,
                  holder_party_id=party_id,
                  bank_last4=record.get("bank_last4") or None, **extra)


def seed_lifelong_protection(book: Any, record: SampleRecord, party_id: str,
                             as_at: str) -> None:
    policy_no = record.require("policy_no")
    start_date = record.require("start_date")
    trust_raw = record.require("trust")
    trustees = tuple(re.sub(r"\s*\([^)]*\)", "", name).strip()
    for name in record.get("trustees", "").split(";") if name.strip())

    book.add_policy(_base_policy(
        record, party_id, start_date,
        lives_assured=(LifeAssured(name=record.require("holder"),
                                   party_id=party_id),),
        lives_assured_basis="single",
        trust=Trust(kind=trust_raw.split(",")[0].strip(),
                    executed=parse_date(trust_raw), trustees=trustees,
                    registrable=True),
        adviser_loa=adviser_loa_from(record.require("adviser_LOA"))),
        **seed_stamp(as_at))

    premium = record.require("premium")
    declined = tuple(int(year) for year in re.findall(r"\b(20\d{2})\b",
                                                      record.get("indexation", "")))
    riders = tuple(name for name, key in (("GIO", "GIO"), ("waiver", "waiver"))
                   if "not included" not in record.get(key, "not included"))
    book.add_cover(CoverComponent(
        policy_no=policy_no,
        sum_assured_pence=parse_money(record.require("sum_assured")),
        basis=("reviewable", "unit_linked"), premium_pence=parse_money(premium),
        premium_frequency="monthly",
        next_collection=reversed_date(premium), next_review_date=parse_date(
            record.require("next_review")),
        riders=riders, indexation=Indexation(on=False, declined_years=declined)),
        **seed_stamp(as_at))

    # The record states a fund value and no premium history; the ledger states
    # the same and invents nothing.
    book.apply_transaction(policy_no, txn(
        policy_no, 1, "opening", parse_money(record.require("fund_value")),
        start_date, "stated fund value at the policy's start date"))


def seed_horizon_bond(book: Any, record: SampleRecord, party_id: str,
                      as_at: str) -> None:
    policy_no = record.require("policy_no")
    invested_raw = record.require("invested")
    invested_pence = parse_money(invested_raw)
    start_date = parse_date(invested_raw)
    segments = int(re.search(r"([\d,]+)\s+segments",
                             invested_raw).group(1).replace(",", ""))

    lives = tuple(LifeAssured(name=re.sub(r"\s*\([^)]*\)", "", name).strip(),
                              party_id=party_id if index == 0 else None)
                  for index, name in
                  enumerate(record.require("lives_assured").split(";")))
    book.add_policy(_base_policy(
        record, party_id, start_date, lives_assured=lives,
        lives_assured_basis="joint_last_survivor",
        adviser_loa=adviser_loa_from(record.require("adviser_LOA"))),
        **seed_stamp(as_at))

    withdrawals = record.require("withdrawals")
    per_year, used, allowance_total = parse_all_money(withdrawals)
    book.add_bond_terms(HorizonBondTerms(
        policy_no=policy_no, invested_pence=invested_pence,
        invested_date=start_date,
        segments_total=segments, segments_remaining=segments,
        allowance_5pct=Allowance5Pct(used_pence=used,
                                     available_pence=allowance_total - used,
                                     policy_year=allowance_total // per_year)),
        **seed_stamp(as_at))

    for fund in funds_from(record.require("funds")):
        book.add_fund(fund, policy_no, **seed_stamp(as_at))

    book.apply_transaction(policy_no, txn(
        policy_no, 1, "opening", invested_pence, start_date,
        "stated amount invested"))

    # "£6,000/yr (5%) since 2020-03" — one row per year, which is what makes
    # "£36,000 of £42,000" tie out rather than being asserted.
    first_year, first_month = (int(part) for part in
                               re.search(r"since (\d{4})-(\d{2})",
                                         withdrawals).groups())
    for index in range(used // per_year):
        book.apply_transaction(policy_no, txn(
            policy_no, index + 2, "regular_withdrawal", per_year,
            f"{first_year + index}-{first_month:02d}-01",
            f"annual 5% withdrawal, policy year {index + 1}"))

    stated_value = parse_money(record.require("current_value"))
    growth = stated_value - (invested_pence - used)
    if growth:
        book.apply_transaction(policy_no, txn(
            policy_no, 99, "credit_adjustment" if growth > 0 else "debit_adjustment",
            abs(growth), _valuation_date(record),
            "investment growth to the stated valuation — not itemised by the "
            "source record (D-CL-038)"))


def _valuation_date(record: SampleRecord) -> str:
    """The date the record says its value was issued at, else the KB date."""
    for item in record.get("recent", "").split(";"):
        if "valuation" in item or "statement" in item:
            return parse_date(item)
    return "2026-07-13"


def seed_retirement_account(book: Any, record: SampleRecord, party_id: str,
                            as_at: str) -> None:
    policy_no = record.require("policy_no")
    transfer_raw = record.require("transfers_in")
    transfer_pence = parse_money(transfer_raw)
    transfer_month = re.search(r"(\d{4}-\d{2})", transfer_raw)
    if transfer_month is None:
        raise ValueError(f"{policy_no}: transfers_in states no month: "
                         f"{transfer_raw!r}")
    transfer_at = f"{transfer_month.group(1)}-01"

    # The record states no start date. Rather than invent one, the account is
    # recorded as starting at its earliest evidenced event (D-CL-038).
    start_date = transfer_at
    book.add_policy(_base_policy(record, party_id, start_date),
                    **seed_stamp(as_at))

    contributions = record.require("contributions")
    member, employer = parse_all_money(contributions)
    wish = record.get("EoW", "")
    book.add_pension_terms(RetirementAccountTerms(
        policy_no=policy_no,
        contribution_schedule=ContributionSchedule(member_net_pence=member,
                                                   employer_gross_pence=employer,
                                                   frequency="monthly"),
        target_retirement_age=int(record.require("target_retirement_age")),
        expression_of_wish=ExpressionOfWish(
            beneficiary=re.sub(r"^\w+\s+", "", wish.split("100%")[0]).strip(),
            share_pct=100, signed=parse_date(wish)) if wish else None,
        transfers_in=(TransferIn(
            at=transfer_at, amount_pence=transfer_pence,
            scam_dd_passed="scam-DD passed" in transfer_raw,
            safeguarded_benefits="no safeguarded" not in transfer_raw),)),
        **seed_stamp(as_at))

    book.add_pension_tax(PensionTax(
        policy_no=policy_no,
        mpaa_triggered=MpaaStatus(
            value="not triggered" not in record.require("MPAA")),
        protections="none", ttfac=None), **seed_stamp(as_at))

    for fund in funds_from(record.require("funds")):
        book.add_fund(fund, policy_no, **seed_stamp(as_at))

    # Twelve months of contributions at the stated rate, ending before the
    # as-of date, plus the stated transfer-in. The remainder of the stated fund
    # value is the pot the record does not itemise.
    monthly = member + employer
    months = months_before(as_at, 12)
    stated_value = parse_money(record.require("fund_value"))
    opening = stated_value - transfer_pence - monthly * len(months)
    book.apply_transaction(policy_no, txn(
        policy_no, 1, "opening", opening, start_date,
        "accumulated value at the account's earliest evidenced event — the "
        "source record states a fund value but does not itemise its history "
        "(D-CL-038)"))
    book.apply_transaction(policy_no, txn(
        policy_no, 2, "transfer_in", transfer_pence, transfer_at,
        "transfer in from a workplace scheme (scam due diligence passed)"))
    for index, month in enumerate(months):
        book.apply_transaction(policy_no, txn(
            policy_no, index + 3, "contribution", monthly, month,
            "member net + employer gross, at the stated rate"))
