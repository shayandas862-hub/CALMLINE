"""Per-product detail — what makes the three Aldercrest products different.

`Policy` holds what they share. Everything here is what they do not: Lifelong
Protection carries cover and a premium, Horizon Bond carries segments and a 5%
allowance, Retirement Account carries contributions, transfers-in and pension
tax.

`can_pay_cash_out` replaces v3's `has_cash_value`. A boolean could only ever be
right about one product at a time; the answer genuinely depends on the cover
basis (LP), on nothing at all (HB), and on which benefit route is being used
(RA).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.records.models import Policy, require_in, require_pence

COVER_BASES = frozenset({"guaranteed", "reviewable", "unit_linked"})
RIDERS = frozenset({"waiver", "GIO"})
PREMIUM_FREQUENCIES = frozenset({"monthly", "yearly"})
PROTECTIONS = frozenset({"FP2016", "IP2016", "none"})

# The only ways a Retirement Account pays money out (KB `03-PEN`). A plain
# "withdrawal" is not among them — that is the whole point.
RA_BENEFIT_ROUTES = frozenset({
    "ufpls", "pcls", "drawdown", "annuity", "small_pot", "trivial_commutation",
})

# Only a unit-linked LP has a fund to surrender; guaranteed and reviewable
# cover is protection, not savings.
LP_CASHABLE_BASES = frozenset({"unit_linked"})


# ── Lifelong Protection ──────────────────────────────────────────────────
@dataclass(frozen=True)
class Indexation:
    """Automatic increases, and the years the holder declined them."""

    on: bool = False
    declined_years: tuple[int, ...] = ()


@dataclass(frozen=True)
class CoverComponent:
    """LP only. The dictionary omits premium; the LP sample carries it, so it
    is held here (dictionary ∪ samples)."""

    policy_no: str
    sum_assured_pence: int
    basis: tuple[str, ...]
    premium_pence: int
    premium_frequency: str = "monthly"
    next_collection: Optional[str] = None
    riders: tuple[str, ...] = ()
    next_review_date: Optional[str] = None
    indexation: Indexation = Indexation()

    def __post_init__(self) -> None:
        # The LP sample reads "reviewable, unit-linked" — the charge basis and
        # the investment basis are separate axes and a policy carries both, so
        # this is a set of bases rather than a single one. The vocabulary is
        # the data model's, unchanged; only the arity follows the KB.
        if not self.basis:
            raise ValueError(f"{self.policy_no}: cover must state at least one basis")
        for basis in self.basis:
            require_in(self.policy_no, "cover basis", basis, COVER_BASES)
        require_in(self.policy_no, "premium_frequency", self.premium_frequency,
                   PREMIUM_FREQUENCIES)
        for rider in self.riders:
            require_in(self.policy_no, "rider", rider, RIDERS)
        require_pence(self.policy_no, "sum_assured_pence", self.sum_assured_pence)
        require_pence(self.policy_no, "premium_pence", self.premium_pence)


# ── Funds (HB and RA) ────────────────────────────────────────────────────
@dataclass(frozen=True)
class FundHolding:
    """One fund line. ``amc_bp`` is basis points (0.65% → 65) so the charge is
    an exact integer rather than a float percentage."""

    fund_id: str
    fund_name: str
    split_pct: int
    amc_bp: int
    price_date: str
    pathway: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.split_pct, int) or not 1 <= self.split_pct <= 100:
            raise ValueError(f"{self.fund_id}: split_pct must be a whole 1–100 percent")
        require_pence(self.fund_id, "amc_bp", self.amc_bp)
        if self.pathway is not None and self.pathway not in (1, 2, 3, 4):
            raise ValueError(f"{self.fund_id}: pathway must be 1–4 or absent")


def fund_split_total(holdings: "tuple[FundHolding, ...]") -> int:
    """Total allocation across ``holdings`` — 100 for a complete policy."""
    return sum(h.split_pct for h in holdings)


# ── Horizon Bond ─────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Allowance5Pct:
    """The running 5% withdrawal allowance: what has been used, what remains,
    and the policy year those figures belong to."""

    used_pence: int
    available_pence: int
    policy_year: int

    def __post_init__(self) -> None:
        require_pence("allowance_5pct", "used_pence", self.used_pence)
        require_pence("allowance_5pct", "available_pence", self.available_pence)
        if self.policy_year < 1:
            raise ValueError("allowance_5pct: policy_year starts at 1")


@dataclass(frozen=True)
class HorizonBondTerms:
    """HB policy-level figures, seeded from the sample and moved forward by
    rules in code as withdrawals commit."""

    policy_no: str
    invested_pence: int
    invested_date: str
    segments_total: int
    segments_remaining: int
    allowance_5pct: Allowance5Pct

    def __post_init__(self) -> None:
        require_pence(self.policy_no, "invested_pence", self.invested_pence)
        if self.segments_total < 1:
            raise ValueError(f"{self.policy_no}: segments_total must be at least 1")
        if not 0 <= self.segments_remaining <= self.segments_total:
            raise ValueError(
                f"{self.policy_no}: segments_remaining {self.segments_remaining} "
                f"is outside 0–{self.segments_total}"
            )


# ── Retirement Account ───────────────────────────────────────────────────
@dataclass(frozen=True)
class ContributionSchedule:
    """What goes in, and how often. Member contributions are net; employer
    contributions are gross — the difference is not cosmetic at tax time."""

    member_net_pence: int
    employer_gross_pence: int
    frequency: str = "monthly"

    def __post_init__(self) -> None:
        require_pence("contribution_schedule", "member_net_pence", self.member_net_pence)
        require_pence("contribution_schedule", "employer_gross_pence",
                      self.employer_gross_pence)


@dataclass(frozen=True)
class ExpressionOfWish:
    """Who the member wishes the death benefit to go to. Not binding, but its
    absence is a real gap at claim time."""

    beneficiary: str
    share_pct: int
    signed: str

    def __post_init__(self) -> None:
        if not 0 < self.share_pct <= 100:
            raise ValueError("expression_of_wish: share_pct must be 1–100")


@dataclass(frozen=True)
class TransferIn:
    """A transfer received. ``scam_dd_passed`` and ``safeguarded_benefits`` are
    the two checks that decide whether it should have been accepted at all."""

    at: str
    amount_pence: int
    scam_dd_passed: bool
    safeguarded_benefits: bool

    def __post_init__(self) -> None:
        require_pence("transfer_in", "amount_pence", self.amount_pence)


@dataclass(frozen=True)
class RetirementAccountTerms:
    """RA policy-level figures."""

    policy_no: str
    contribution_schedule: ContributionSchedule
    target_retirement_age: int
    expression_of_wish: Optional[ExpressionOfWish] = None
    transfers_in: tuple[TransferIn, ...] = ()

    def __post_init__(self) -> None:
        if not 55 <= self.target_retirement_age <= 75:
            raise ValueError(
                f"{self.policy_no}: target_retirement_age {self.target_retirement_age} "
                "is outside the selectable range"
            )


@dataclass(frozen=True)
class MpaaStatus:
    """The money-purchase annual allowance trigger. If it has been triggered we
    must be able to say when — "triggered, date unknown" is not a statable
    fact, and the answer changes the member's contribution headroom."""

    value: bool
    at: Optional[str] = None

    def __post_init__(self) -> None:
        if self.value and not self.at:
            raise ValueError("mpaa_triggered: a triggered MPAA must carry its date")


@dataclass(frozen=True)
class PensionTax:
    """RA only."""

    policy_no: str
    mpaa_triggered: MpaaStatus
    protections: str = "none"
    ttfac: Optional[str] = None
    lsa_used_pence: int = 0
    aa_headroom_estimate_pence: int = 0

    def __post_init__(self) -> None:
        require_in(self.policy_no, "protections", self.protections, PROTECTIONS)
        require_pence(self.policy_no, "lsa_used_pence", self.lsa_used_pence)
        require_pence(self.policy_no, "aa_headroom_estimate_pence",
                      self.aa_headroom_estimate_pence)


# ── the rule that replaced has_cash_value ────────────────────────────────
def can_pay_cash_out(
    policy: Policy,
    *,
    cover: Optional[CoverComponent] = None,
    route: Optional[str] = None,
) -> bool:
    """Can this policy pay money out to the holder?

    - **Lifelong Protection** — only when the cover is unit-linked, so there is
      a fund to surrender. Without a cover component the basis is unknown, and
      unknown is not a licence to pay out.
    - **Horizon Bond** — yes; that is what a bond is for.
    - **Retirement Account** — only through a benefit route (UFPLS, PCLS,
      drawdown, annuity purchase, small pot, trivial commutation). A plain
      withdrawal request is refused here, before any money tool sees it.

    ``route`` is a pension mechanic and is deliberately ignored by the other
    two products, so a benefit route cannot unlock protection-only cover.
    """
    if policy.product == "lifelong_protection":
        return cover is not None and bool(LP_CASHABLE_BASES.intersection(cover.basis))
    if policy.product == "horizon_bond":
        return True
    if policy.product == "retirement_account":
        return route in RA_BENEFIT_ROUTES
    return False
