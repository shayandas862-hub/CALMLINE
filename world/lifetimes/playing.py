"""Playing one policy — its funds, its opening scale, and the two passes.

Split out of ``build.py`` at the 300-line rule when v4.5 phase 3 assembled the
trusts, mandates and authorities into the book. One job: turning a
``PolicySpec`` into a ``BuiltPolicy``, by handing its product's mechanics to the
timeline and offering every movement to the rulebook.

**Hitting a value band takes two passes.** Growth and charges are proportional
to the balance and a bond's regular withdrawal is a percentage of what went in,
so a policy's value is very nearly linear in what it opened with. The first pass
finds that ratio; the second scales the opening so the finished policy lands in
the band the plan gave it. Searching would have been slower and no more exact.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.records.models import LedgerEntry, Policy
from src.records.products import CoverComponent, FundHolding, Indexation
from world.lifetimes.allocation import BAND_TARGET_RANGES, PolicySpec, band_of
from world.lifetimes.bond import play_bond
from world.lifetimes.markets import CATALOGUE
from world.lifetimes.pension import play_pension, refuse_non_benefit_money_out
from world.lifetimes.report import RefusalReport
from world.lifetimes.timeline import play
from world.lifetimes.wholeoflife import play_whole_of_life

# `01-WOL` premiums are monthly; a sum assured of this order needs roughly this.
PREMIUM_PER_100K_PENCE = 53_10


@dataclass(frozen=True)
class BuiltPolicy:
    """One finished policy: what it is, what happened, and what it is worth."""

    policy_no: str
    product: str
    status: str
    start: date
    holder_party_id: str
    entries: tuple[LedgerEntry, ...]
    events: tuple
    band: str
    headline_value_pence: int

    @property
    def value_pence(self) -> int:
        return sum(e.transaction.signed_pence for e in self.entries)


def policy_of(spec: PolicySpec) -> Policy:
    return Policy(policy_no=spec.policy_no, product=spec.product,
                  status=spec.status, start_date=spec.start.isoformat(),
                  holder_party_id=spec.holder_party_id,
                  lives_assured_basis=spec.lives_basis)


def _holdings(spec: PolicySpec, rng: random.Random) -> tuple[FundHolding, ...]:
    if spec.product == "lifelong_protection":
        if "unit_linked" not in spec.cover_basis:
            return ()
        return (FundHolding("protection_managed", "Protection Managed", 100,
                            CATALOGUE["protection_managed"].amc_bp,
                            spec.start.isoformat()),)
    if spec.product == "horizon_bond":
        split = rng.choice((60, 70, 100))
        holdings = [FundHolding("managed_growth", "Managed Growth", split,
                                CATALOGUE["managed_growth"].amc_bp,
                                spec.start.isoformat())]
        if split < 100:
            holdings.append(FundHolding(
                "with_profits", "With-Profits", 100 - split,
                CATALOGUE["with_profits"].amc_bp, spec.start.isoformat()))
        return tuple(holdings)
    return (FundHolding("target_date_2036", "Target-Date 2036", 70,
                        CATALOGUE["target_date_2036"].amc_bp,
                        spec.start.isoformat(), pathway=rng.choice((1, 2, 3, 4))),
            FundHolding("global_index", "Global Index", 30,
                        CATALOGUE["global_index"].amc_bp, spec.start.isoformat()))


def play_once(spec: PolicySpec, holdings, seed: int, born: date, scale: int):
    """One attempt at a policy, at a given opening scale (in pence)."""
    policy = policy_of(spec)
    if spec.product == "lifelong_protection":
        sum_assured = max(1_000_00, scale)
        cover = CoverComponent(
            policy_no=spec.policy_no, sum_assured_pence=sum_assured,
            basis=spec.cover_basis,
            premium_pence=max(10_00, sum_assured * PREMIUM_PER_100K_PENCE
                              // 100_000_00),
            premium_frequency="monthly",
            # Never `hash()` — it is randomised per process and would make the
            # world different on every run while looking deterministic inside
            # one session. The policy's own digits are stable forever.
            indexation=Indexation(
                on=int(spec.policy_no[3:]) % 3 == 0,
                declined_years=(2024, 2025) if int(spec.policy_no[3:]) % 7 == 0
                else ()))
        plan = play_whole_of_life(policy, cover, holdings, seed=seed, born=born)
        return plan, plan.sum_assured_pence, ()
    if spec.product == "horizon_bond":
        invested = max(5_000_00, scale)
        plan = play_bond(policy, holdings, invested_pence=invested, seed=seed,
                         withdraw_annually_pence=invested // 20,
                         surrender_segments_pence=(invested // 8
                                                   if spec.status == "in_force"
                                                   else 0),
                         born=born)
        return plan, None, ()
    contribution = max(50_00, scale // 200)
    plan = play_pension(policy, holdings, member_dob=date(1961, 6, 18),
                        seed=seed, monthly_contribution_pence=contribution,
                        transfer_in_pence=scale // 3,
                        benefit_route=("ufpls" if spec.status == "claimed"
                                       else None),
                        born=born)
    return plan, None, ()


def build_one(spec: PolicySpec, seed: int, born: date,
               report: RefusalReport) -> Optional[BuiltPolicy]:
    rng = random.Random(f"{seed}:book:{spec.policy_no}")
    holdings = _holdings(spec, rng)
    # Each policy draws its own target from inside its band, so a band is
    # a spread of policies rather than seventy-four copies of one figure.
    low, high = BAND_TARGET_RANGES[spec.band]
    target = rng.randint(low, high)

    rules = ((refuse_non_benefit_money_out,)
             if spec.product == "retirement_account" else ())

    # Two passes, because a policy's headline value is very nearly linear in
    # what it opened with: growth and charges are proportional to the balance,
    # a bond's regular withdrawal is a percentage of what went in, and a
    # whole-of-life premium is a percentage of the cover. The first pass finds
    # that ratio; the second scales the opening so the finished policy lands in
    # the band the plan gave it. Searching would be slower and no more exact.
    #
    # Whole of life needs this as much as the others and was missed at first:
    # indexation raises the sum assured by around 3% a year, so twenty-eight
    # years of it more than doubles the figure the band is measured on.
    scale = target
    plan = lifetime = None
    for _ in range(2):
        plan, headline, _ = play_once(spec, holdings, seed, born, scale)
        lifetime = play(policy_of(spec), plan.movements, report=report,
                        rules=rules)
        if lifetime is None:
            return None
        value = _headline(headline, lifetime)
        if value <= 0:
            break
        scale = max(1_000_00, scale * target // value)

    value = _headline(headline, lifetime)
    return BuiltPolicy(
        policy_no=spec.policy_no, product=spec.product, status=spec.status,
        start=spec.start, holder_party_id=spec.holder_party_id,
        entries=lifetime.entries, events=tuple(plan.events),
        band=band_of(value), headline_value_pence=value)


def _peak(entries: tuple[LedgerEntry, ...]) -> int:
    """The most this policy was ever worth — what a control would have tested."""
    return max((e.balance_after_pence for e in entries), default=0)


def _headline(sum_assured: Optional[int], lifetime) -> int:
    """The figure `05-OPS:9.9` bands authority by: the sum assured for
    protection cover, and the fund for everything else. A lapsed or claimed
    policy holds nothing now, so its peak is what a control would have tested."""
    if sum_assured is not None:
        return sum_assured
    return max(lifetime.value_pence, _peak(lifetime.entries))


