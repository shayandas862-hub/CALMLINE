"""v4 phase 2 · task 1 — the per-product detail that moved off `Policy`.

Three products with genuinely different mechanics: Lifelong Protection carries
cover and a premium, Horizon Bond carries segments and a 5% allowance,
Retirement Account carries contributions and pension tax. `has_cash_value` was
a boolean pretending to describe all three; `can_pay_cash_out` replaces it with
the actual product rules.
"""

import pytest

from src.records.models import Policy
from src.records.authorisations import (
    AuthorityRecord,
    BankMandate,
    MandateChange,
)
from src.records.products import (
    RA_BENEFIT_ROUTES,
    Allowance5Pct,
    ContributionSchedule,
    CoverComponent,
    ExpressionOfWish,
    FundHolding,
    HorizonBondTerms,
    Indexation,
    MpaaStatus,
    PensionTax,
    RetirementAccountTerms,
    TransferIn,
    can_pay_cash_out,
    fund_split_total,
)
from src.records.models import gbp


def _policy(policy_no="LP-20419876", product="lifelong_protection", **over) -> Policy:
    kw = dict(policy_no=policy_no, product=product, status="in_force",
              start_date="2016-05-01", holder_party_id="PH-1001")
    kw.update(over)
    return Policy(**kw)


def _cover(**over) -> CoverComponent:
    kw = dict(policy_no="LP-20419876", sum_assured_pence=gbp(400_000),
              basis=("unit_linked",),
              premium_pence=gbp(212.40), premium_frequency="monthly",
              next_collection="2026-08-01", next_review_date="2026-05-01",
              indexation=Indexation(on=False, declined_years=(2024, 2025)))
    kw.update(over)
    return CoverComponent(**kw)


# ── CoverComponent (LP) ──────────────────────────────────────────────────
def test_cover_component_carries_sum_assured_and_premium_in_pence():
    cover = _cover()
    assert cover.sum_assured_pence == 40_000_000
    assert cover.premium_pence == 21_240          # £212.40 — exact, no float drift
    assert cover.premium_frequency == "monthly"


def test_cover_component_basis_is_a_closed_vocabulary():
    for basis in ("guaranteed", "reviewable", "unit_linked"):
        assert _cover(basis=(basis,)).basis == (basis,)
    with pytest.raises(ValueError):
        _cover(basis=("with_profits",))


def test_cover_basis_holds_more_than_one_axis_at_once():
    # The LP sample record reads "reviewable, unit-linked": the charge basis and
    # the investment basis are different axes and the policy carries both. A
    # single-valued enum could only record one of them, so the round-trip would
    # silently drop the other.
    cover = _cover(basis=("reviewable", "unit_linked"))
    assert cover.basis == ("reviewable", "unit_linked")


def test_cover_basis_cannot_be_empty():
    # "No basis at all" is not a product; it is missing data.
    with pytest.raises(ValueError):
        _cover(basis=())


def test_cover_component_riders_are_closed_and_default_to_none_held():
    assert _cover().riders == ()
    assert _cover(riders=("waiver", "GIO")).riders == ("waiver", "GIO")
    with pytest.raises(ValueError):
        _cover(riders=("critical_illness",))


def test_indexation_records_the_years_the_holder_declined():
    # The LP sample declined 2024 and 2025 — a fact the review letter depends on.
    cover = _cover()
    assert cover.indexation.on is False
    assert cover.indexation.declined_years == (2024, 2025)


def test_cover_component_rejects_negative_money():
    with pytest.raises(ValueError):
        _cover(sum_assured_pence=-1)


# ── FundHolding (HB and RA) ──────────────────────────────────────────────
def test_fund_holding_holds_whole_percent_splits_and_basis_point_charges():
    fund = FundHolding(fund_id="ALD-BAL", fund_name="Aldercrest Balanced",
                       split_pct=60, amc_bp=65, price_date="2026-07-10")
    assert fund.split_pct == 60
    assert fund.amc_bp == 65        # 0.65% expressed in basis points — an integer
    assert fund.pathway is None


def test_fund_holding_rejects_a_split_outside_1_to_100():
    for bad in (0, 101, -5):
        with pytest.raises(ValueError):
            FundHolding(fund_id="F", fund_name="F", split_pct=bad, amc_bp=65,
                        price_date="2026-07-10")


def test_fund_holding_pathway_is_one_to_four_or_absent():
    assert FundHolding(fund_id="F", fund_name="F", split_pct=100, amc_bp=65,
                       price_date="2026-07-10", pathway=3).pathway == 3
    with pytest.raises(ValueError):
        FundHolding(fund_id="F", fund_name="F", split_pct=100, amc_bp=65,
                    price_date="2026-07-10", pathway=5)


def test_fund_split_total_sums_the_holdings():
    funds = (FundHolding(fund_id="A", fund_name="A", split_pct=60, amc_bp=65,
                         price_date="2026-07-10"),
             FundHolding(fund_id="B", fund_name="B", split_pct=40, amc_bp=80,
                         price_date="2026-07-10"))
    assert fund_split_total(funds) == 100


# ── HorizonBondTerms (HB policy-level) ───────────────────────────────────
def test_bond_terms_track_segments_and_the_five_percent_allowance():
    terms = HorizonBondTerms(
        policy_no="HB-40582213", invested_pence=gbp(120_000), invested_date="2019-03-01",
        segments_total=100, segments_remaining=100,
        allowance_5pct=Allowance5Pct(used_pence=gbp(36_000),
                                     available_pence=gbp(6_000), policy_year=7))
    assert terms.segments_remaining == 100
    assert terms.allowance_5pct.used_pence == 3_600_000     # £36,000 of £42,000 used
    assert terms.allowance_5pct.policy_year == 7


def test_bond_terms_reject_more_segments_remaining_than_exist():
    with pytest.raises(ValueError):
        HorizonBondTerms(policy_no="HB-40582213", invested_pence=gbp(120_000),
                         invested_date="2019-03-01", segments_total=100,
                         segments_remaining=101,
                         allowance_5pct=Allowance5Pct(used_pence=0, available_pence=gbp(6_000),
                                                      policy_year=1))


# ── RetirementAccountTerms (RA policy-level) ─────────────────────────────
def test_pension_terms_carry_contributions_wish_and_transfers_in():
    terms = RetirementAccountTerms(
        policy_no="RA-77103428",
        contribution_schedule=ContributionSchedule(member_net_pence=gbp(400),
                                                   employer_gross_pence=gbp(300),
                                                   frequency="monthly"),
        target_retirement_age=67,
        expression_of_wish=ExpressionOfWish(beneficiary="Kappa Quasar 58",
                                            share_pct=100, signed="2024-08-01"),
        transfers_in=(TransferIn(at="2024-08-01", amount_pence=gbp(58_000),
                                 scam_dd_passed=True, safeguarded_benefits=False),))
    assert terms.contribution_schedule.member_net_pence == 40_000
    assert terms.target_retirement_age == 67
    assert terms.transfers_in[0].scam_dd_passed is True
    assert terms.transfers_in[0].safeguarded_benefits is False


def test_expression_of_wish_shares_cannot_exceed_one_hundred_percent():
    with pytest.raises(ValueError):
        ExpressionOfWish(beneficiary="x", share_pct=101, signed="2024-08-01")


# ── PensionTax (RA only) ─────────────────────────────────────────────────
def test_pension_tax_records_mpaa_and_protections():
    tax = PensionTax(policy_no="RA-77103428",
                     mpaa_triggered=MpaaStatus(value=False, at=None),
                     protections="none", ttfac=None,
                     lsa_used_pence=0, aa_headroom_estimate_pence=gbp(20_000))
    assert tax.mpaa_triggered.value is False
    assert tax.mpaa_triggered.at is None
    assert tax.aa_headroom_estimate_pence == 2_000_000


def test_pension_tax_protections_are_a_closed_vocabulary():
    with pytest.raises(ValueError):
        PensionTax(policy_no="RA-77103428", mpaa_triggered=MpaaStatus(value=False, at=None),
                   protections="FP2020", ttfac=None, lsa_used_pence=0,
                   aa_headroom_estimate_pence=0)


def test_mpaa_triggered_must_carry_a_date_when_it_is_true():
    # "Triggered, but we cannot say when" is not a statable fact.
    with pytest.raises(ValueError):
        MpaaStatus(value=True, at=None)


# ── BankMandate — the fraud watch ────────────────────────────────────────
def test_bank_mandate_keeps_its_change_history():
    # E29's "bank change then £40k two weeks later" is answerable only because
    # this history exists.
    mandate = BankMandate(policy_no="HB-40582213", account_last4="4471", verified=True,
                          hold_until=None,
                          change_history=(MandateChange(at="2026-06-01T09:00:00",
                                                        actor="handler_a",
                                                        note="account changed on request"),))
    assert mandate.change_history[0].actor == "handler_a"
    assert mandate.account_last4 == "4471"


def test_bank_mandate_rejects_an_account_stub_that_is_not_four_digits():
    with pytest.raises(ValueError):
        BankMandate(policy_no="HB-40582213", account_last4="71", verified=True,
                    hold_until=None, change_history=())


# ── AuthorityRecord — third parties are first class (AD-CL-033) ──────────
def test_authority_record_carries_type_scope_and_evidence():
    auth = AuthorityRecord(authority_id="AUTH-0001", policy_no="LP-20419876",
                           party_id="PH-1002", type="LPA", scope=("withdrawals",),
                           evidence_ref="OPG-123456", verified_date="2026-05-01",
                           status="active")
    assert auth.type == "LPA"
    assert auth.status == "active"


@pytest.mark.parametrize("kind", ["LOA", "LPA", "EPA", "deputy", "PR", "trustee",
                                  "mandate", "one_off"])
def test_authority_types_are_the_documented_set(kind):
    assert AuthorityRecord(authority_id="AUTH-1", policy_no="LP-20419876",
                           party_id="PH-1002", type=kind, scope=(),
                           evidence_ref="ref", verified_date=None,
                           status="unverified").type == kind


def test_authority_record_rejects_an_unknown_type_or_status():
    with pytest.raises(ValueError):
        AuthorityRecord(authority_id="A", policy_no="LP-20419876", party_id="PH-1002",
                        type="power_of_attorney", scope=(), evidence_ref="r",
                        verified_date=None, status="active")
    with pytest.raises(ValueError):
        AuthorityRecord(authority_id="A", policy_no="LP-20419876", party_id="PH-1002",
                        type="LPA", scope=(), evidence_ref="r", verified_date=None,
                        status="pending")


# ── can_pay_cash_out — what has_cash_value could never express ───────────
def test_unit_linked_lifelong_protection_can_pay_cash_out():
    assert can_pay_cash_out(_policy(), cover=_cover(basis=("unit_linked",))) is True


@pytest.mark.parametrize("basis", ["guaranteed", "reviewable"])
def test_non_unit_linked_lifelong_protection_cannot_pay_cash_out(basis):
    # Protection-only cover has no fund to surrender — the v3 Term Life rule,
    # now expressed against the actual product mechanics.
    assert can_pay_cash_out(_policy(), cover=_cover(basis=(basis,))) is False


def test_lifelong_protection_without_a_cover_component_cannot_pay_cash_out():
    # Unknown basis is not a licence to pay out.
    assert can_pay_cash_out(_policy(), cover=None) is False


def test_horizon_bond_can_always_pay_cash_out():
    assert can_pay_cash_out(_policy("HB-40582213", "horizon_bond")) is True


def test_retirement_account_refuses_a_plain_withdrawal():
    # The done criterion: an RA withdrawal outside benefit rules is refused.
    assert can_pay_cash_out(_policy("RA-77103428", "retirement_account")) is False


@pytest.mark.parametrize("route", sorted(RA_BENEFIT_ROUTES))
def test_retirement_account_pays_out_only_through_a_benefit_route(route):
    assert can_pay_cash_out(_policy("RA-77103428", "retirement_account"), route=route) is True


def test_retirement_account_rejects_an_invented_benefit_route():
    assert can_pay_cash_out(_policy("RA-77103428", "retirement_account"),
                            route="just_send_it") is False


def test_a_benefit_route_does_not_unlock_a_protection_only_policy():
    # Routes are pension mechanics; they must not leak across products.
    assert can_pay_cash_out(_policy(), cover=_cover(basis=("guaranteed",)),
                            route="ufpls") is False
