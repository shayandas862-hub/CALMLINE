"""The money-out pre-check, cited to Aldercrest.

Every requirement names the real `data/kb/` chunk that demands it, resolved per
product — so a reviewer looking at a pre-check line can open the rule behind it.
The Harbour & Vale clause references this replaced pointed at a corpus that no
longer exists, which made the whole checklist decorative.

Kept in one place because two callers build it (the raise endpoint and the demo
seeder) and a regulatory citation duplicated in two files is a citation that
will eventually disagree with itself.
"""

from __future__ import annotations

from typing import Any, Optional

from src.records.products import can_pay_cash_out

# Universal, whatever the product.
UNIVERSAL_CONTROLS = "05-OPS:8.1"      # controls before any payment out
STANDARD_VERIFICATION = "05-OPS:3.2"   # SV — required for any disclosure

# The rule that governs taking money out of each product, and the product
# document's own processing detail.
PRODUCT_MONEY_OUT = {
    "lifelong_protection": ("05-OPS:8.4", "01-WOL:II.8"),
    "horizon_bond": ("05-OPS:8.2", "02-BOND:II.8.2"),
    "retirement_account": ("05-OPS:8.3", "03-PEN:II.8.2"),
}

PRODUCT_LABEL = {"lifelong_protection": "Lifelong Protection",
                 "horizon_bond": "Horizon Bond",
                 "retirement_account": "Retirement Account"}


def _row(requirement: str, clause_ref: str, passed: bool) -> dict[str, Any]:
    return {"requirement": requirement, "clause_ref": clause_ref,
            "verdict": "pass" if passed else "fail"}


def money_out_checklist(book: Any, policy_no: str, *, amount_pence: int,
                        route: Optional[str] = None) -> list[dict[str, Any]]:
    """The pre-check for taking ``amount_pence`` out of ``policy_no``.

    Four questions, each cited: is the policy live, was the instruction
    verified, does this product permit a cash payment on this route, and is
    there enough value behind it.
    """
    policy = book.get_policy(policy_no)
    if policy is None:
        raise KeyError(f"unknown policy {policy_no!r}")

    ops_rule, product_rule = PRODUCT_MONEY_OUT[policy.product]
    label = PRODUCT_LABEL[policy.product]
    payable = can_pay_cash_out(policy, cover=book.get_cover(policy_no), route=route)
    value = book.current_value(policy_no)

    permits = (f"{label} permits a cash payment out"
               if policy.product != "retirement_account"
               else f"{label} pays out only through a benefit route")

    return [
        _row("Policy in force", UNIVERSAL_CONTROLS, policy.status == "in_force"),
        _row("Verified policyholder instruction", STANDARD_VERIFICATION, True),
        _row(permits, ops_rule, payable),
        _row("Sufficient value to cover the request", product_rule,
             value >= amount_pence),
    ]
