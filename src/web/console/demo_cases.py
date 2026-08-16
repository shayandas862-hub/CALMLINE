"""Deterministic demo cases — so the ops (and back-office) screens are populated.

Each case is built through the SAME real path the front office uses: a proposed
movement (`record_transaction`), a cited compliance check (`run_compliance_check`),
the queue (`queue.open` + `attach_precheck`), and — for one case — a human
approval (`approve_case`). Nothing is faked. The spread is chosen so the three
ops lenses show honest, non-zero numbers on the very first ops login, WITHOUT
disturbing the anchor balances (only a pending case touches them).

Off by default; the console opts in via ``create_console_app(seed_demo=True)``.
"""

from __future__ import annotations

from typing import Any

from src.agent.tools.case_tools import run_compliance_check
from src.agent.tools.money_tools import record_transaction
from src.casework.approval import approve_case
from src.authority.checklist import money_out_checklist
from src.authority.sla import sla_due
from src.casework.queue import CaseQueue
from src.records.models import gbp


def _raise(queue: CaseQueue, book: Any, now: str, *, policy_no: str, request: str,
           priority: str, amount_pence: int, sla_hours: float) -> Any:
    """Raise one case exactly as the front-office endpoint does (pre-check + proposal)."""
    case = queue.open(
        {"policy_no": policy_no, "request": request, "priority": priority,
         "status": "pending_review"},
        sla_due=sla_due(now, priority, hours=sla_hours),
    )
    proposed = None
    checklist = money_out_checklist(book, policy_no, amount_pence=amount_pence)
    if all(row["verdict"] == "pass" for row in checklist):
        proposed = record_transaction(policy_no=policy_no, kind="withdrawal",
                                      amount_pence=amount_pence, reason=request,
                                      actor="front office", at=now)

    result = run_compliance_check(checklist)
    queue.attach_precheck(
        case.case_id, checklist=result["checklist"], recommendation=result["recommendation"],
        proposed=proposed if result["recommendation"] == "proceed" else None,
    )
    return case


def _pick(book: Any, product: str, *, at_least_pence: int = 0) -> str:
    """The lowest-numbered in-force policy of a product, by number.

    **Chosen by property, never named.** Naming three policy numbers tied the
    demo to the seeded book, so pointing the console at the world would have
    raised four cases against policies that do not exist there — and it made
    three policies special in a system whose claim is that none are. Sorted, so
    the demo is the same demo on every boot.
    """
    for policy in sorted(book.list_policies(), key=lambda p: p.policy_no):
        if policy.product == product and policy.status == "in_force" \
                and book.current_value(policy.policy_no) >= at_least_pence:
            return policy.policy_no
    raise LookupError(f"the book holds no in-force {product} worth "
                      f"{at_least_pence} pence — the demo cannot be seeded")


def seed_demo_cases(queue: CaseQueue, book: Any, now: str) -> list[Any]:
    """Populate ``queue`` with a spread of illustrative cases for the demo."""
    protection = _pick(book, "lifelong_protection")
    pension = _pick(book, "retirement_account")
    bond = _pick(book, "horizon_bond", at_least_pence=gbp(3_000))

    # 1 · a protection surrender — a pending high-priority case (ledger untouched).
    _raise(queue, book, now, policy_no=protection,
           request="partial surrender £2,000",
           priority="high", amount_pence=gbp(2_000), sla_hours=4)
    # 2 · a pension cash request — the AI blocks it: a Retirement Account pays out
    #     only through a benefit route, never a plain withdrawal.
    _raise(queue, book, now, policy_no=pension, request="cash withdrawal",
           priority="low", amount_pence=gbp(1_000), sla_hours=96)
    # 3 · a bond withdrawal already two hours past its SLA — an oversight breach.
    _raise(queue, book, now, policy_no=bond, request="partial surrender £1,500",
           priority="medium", amount_pence=gbp(1_500), sla_hours=-2)
    # 4 · a smaller bond withdrawal, worked and human-approved → throughput + one ledger move.
    done = _raise(queue, book, now, policy_no=bond,
                  request="partial surrender £1,000",
                  priority="medium", amount_pence=gbp(1_000), sla_hours=24)
    approve_case(queue, book, done.case_id, reviewer="back office", at=now,
                 txn_id=f"TXN-{done.case_id}")
    return queue.all()
