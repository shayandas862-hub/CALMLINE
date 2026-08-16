"""Assembling the whole book, and proving it.

Every policy is played by its own product's mechanics (`playing.py`) and then
offered, movement by movement, to the rulebook. A refusal stops that policy and
lands in the report; the build carries on, so the report is a list of everything
wrong rather than the first thing wrong.

Around the money sits everything else the plan asks for: the bank mandates and
their change history, the trusts, the adviser mandates, the attorneys, deputies
and personal representatives, and the operational shape of past calls and cases.
**The four authority allocators are called here** — until v4.5 phase 3 three of
them were reached only by their own tests, so §4, §5 and §6 of the bucket plan
described data that landed on no policy at all.

§11 is closed here — sixty holders carrying a memorable datum — by a separately
seeded pass over the committed people file. Adding the draw to the identity
generator would have shifted every subsequent draw and rebuilt all 299 people.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from src.records.authorisations import AuthorityRecord, BankMandate
from src.records.models import AdviserLoa, Policy, Trust
from world import WORLD_BIRTH_DATE
from world.lifetimes.allocation import MEMORABLE_HOLDERS, PolicySpec, allocate_book
from world.lifetimes.authorities import (
    allocate_bank_mandates,
    allocate_mandates,
    allocate_third_party_authorities,
    allocate_trusts,
)
from world.lifetimes.pension.claims import graft_pension_claims
from world.lifetimes.playing import BuiltPolicy, build_one, policy_of
from world.lifetimes.reconcile import (
    notify_after_death,
    retype_claim_cases,
    reword_relief,
    swap_for_minimum_age,
)
from world.lifetimes.report import RefusalReport
from world.operations import PolicyOperations, plan_operations
from world.operations.parties import reconcile_operations

PEOPLE_FILE = Path(__file__).resolve().parents[2] / "data" / "world" / "people.jsonl"


@dataclass(frozen=True)
class Book:
    """The whole world, and the report of anything it would not build."""

    policies: tuple[BuiltPolicy, ...]
    report: RefusalReport
    bank_mandates: dict[str, BankMandate]
    operations: dict[str, PolicyOperations]
    memorable_holders: tuple[str, ...]
    # §4, §5 and §6. Built by their own allocators in phase 2 and assembled here
    # in phase 3 — until then the allocators were reached only by their own
    # tests, so the plan's counts described data that landed on no policy.
    trusts: dict[str, Trust] = field(default_factory=dict)
    adviser_mandates: dict[str, AdviserLoa] = field(default_factory=dict)
    authorities: dict[str, tuple[AuthorityRecord, ...]] = field(
        default_factory=dict)


def load_people(path: Path = PEOPLE_FILE) -> list[dict]:
    """Everyone the world holds, as phase 1 wrote them. Read, never rewritten."""
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def select_memorable_holders(holders: list[str], *, seed: int) -> tuple[str, ...]:
    """§11 — sixty of the two hundred, chosen without touching anybody.

    A separate seed, so this pass cannot perturb any other draw in the world.

    ``holders`` is **the two hundred policyholders**, which is why §11's own
    partition closes at 60 + 140. It is not the same set as "everyone holding a
    policy": 162 people hold at least one and the other 38 appear only as the
    second life on a joint-life policy (§1) — still policyholders, still
    verifiable against `05-OPS:3.2`.

    Deduplicated before the draw. Fed one entry per *policy* the list carries
    two hundred entries covering 162 people, and sampling that draws somebody
    twice: the world then reports sixty and gives four askable checks to
    fifty-five. Counting the result alone will not catch it, so the caller's
    test counts distinct people.
    """
    pool = sorted(set(holders))
    rng = random.Random(f"{seed}:memorable")
    return tuple(sorted(rng.sample(pool, min(MEMORABLE_HOLDERS, len(pool)))))


def build_book(*, seed: int, born: date = WORLD_BIRTH_DATE) -> Book:
    """Assemble all two hundred, and hand back everything needed to prove them."""
    people = load_people()
    holders = [p["party_id"] for p in people if p["role"] == "policyholder"]
    specs = allocate_book(seed=seed, born=born, holders=holders[:162],
                          second_lives=holders[162:200],
                          # Without these the allocator cannot tell whether the
                          # person it picked was alive when the policy started.
                          dobs={p["party_id"]: date.fromisoformat(p["dob"])
                                for p in people if "party_id" in p})

    report = RefusalReport()
    built = [policy for spec in specs
             if (policy := build_one(spec, seed, born, report)) is not None]

    dobs = {p["party_id"]: date.fromisoformat(p["dob"])
            for p in people if "party_id" in p}
    records = [policy_of(s) for s in specs]
    bank = allocate_bank_mandates(records, seed=seed, born=born)
    trusts = allocate_trusts(records, seed=seed,
                             trustees=_ids(people, "trustee"))
    mandates = allocate_mandates(records, _firms(people), seed=seed, born=born)
    authorities = allocate_third_party_authorities(
        records, seed=seed,
        attorneys=_role(people, "attorney"),
        deputies=_role(people, "deputy"),
        personal_representatives=_role(people, "personal_representative"))

    # The reconciliation passes — rulebook corrections that consume no RNG, so
    # every draw above and below them is exactly what it always was. Order
    # matters: holders settle before anything reads a date of birth, the
    # operations are planned from the pre-graft ledger so their per-policy
    # streams are untouched, and the pension claims land after both.
    policies = reword_relief(swap_for_minimum_age(tuple(built), dobs), dobs)
    operations = {
        policy.policy_no: plan_operations(
            policy.policy_no, _movements_of(policy), start=policy.start,
            seed=seed, born=born)
        for policy in policies}
    operations = reconcile_operations(operations, trusts=trusts,
                                      adviser_mandates=mandates,
                                      authorities=authorities)
    policies, operations = graft_pension_claims(policies, operations,
                                                born=born)
    operations = notify_after_death(policies, operations)
    operations = retype_claim_cases(policies, operations)
    _require_distinct_references(operations)
    return Book(policies=policies, report=report, bank_mandates=bank,
                operations=operations,
                # The two hundred policyholders — §11's own partition — rather
                # than one entry per policy, which covers only the 162 who hold
                # one and counts the multiple-policy holders more than once.
                memorable_holders=select_memorable_holders(holders, seed=seed),
                trusts=trusts, adviser_mandates=mandates,
                authorities=authorities)


def _require_distinct_references(operations: dict[str, PolicyOperations]) -> None:
    """No two contacts, cases or evidence items may share a reference.

    Asserted across the **finished** world rather than trusted to the formula
    that mints them. The first version of that formula silently gave 819
    distinct `CN-` to 1,409 contacts, and nothing noticed because each policy's
    own references looked fine — the collisions were between policies. A
    contact note is keyed on its `CN-`, so two calls sharing one are two calls
    whose notes land on each other.
    """
    for name, refs in (
            ("CN", [c.cn_ref for ops in operations.values()
                    for c in ops.contacts]),
            ("CW", [k.cw_ref for ops in operations.values() for k in ops.cases]),
            ("EVD", [e.evidence_id for ops in operations.values()
                     for k in ops.cases for e in k.evidence])):
        if len(set(refs)) != len(refs):
            raise ValueError(
                f"{name}: {len(set(refs))} distinct references for {len(refs)} "
                f"items — two policies would share one, and a note keyed on it "
                f"would land on the wrong call")


def _role(people: list[dict], role: str) -> list[dict]:
    return [person for person in people if person["role"] == role]


def _ids(people: list[dict], role: str) -> list[str]:
    return [person["party_id"] for person in _role(people, role)]


def _firms(people: list[dict]) -> list[dict]:
    return _role(people, "adviser_firm")


def _movements_of(policy: BuiltPolicy):
    """The policy's committed movements, in the shape the operations planner
    reads — it only needs the kind, the amount and the day."""
    from world.lifetimes.timeline import Movement
    return tuple(
        Movement(on=date.fromisoformat(e.transaction.at[:10]),
                 kind=e.transaction.kind,
                 amount_pence=e.transaction.amount_pence,
                 reason=e.transaction.reason)
        for e in policy.entries)
