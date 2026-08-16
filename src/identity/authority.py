"""The third-party authority path (AD-CL-033).

`05-OPS:5.0` is the whole shape of this module: authority must be **verified**,
*and* the request must fall **within the verified scope**. Fail either and the
specific instruction is refused — with what would make it acceptable, and the
customer-direct route — and nothing is disclosed "to be helpful".

Two limits are deliberately **not** taken from the scope tuple, because they
come from what the instrument *is* rather than what someone typed:

* an LOA does not authorise receiving claim/surrender proceeds or changing the
  customer's bank details (`05-OPS:5.1`);
* trusteeship is **personal** — an attorney is not a trustee, and replacement
  runs by deed under s.36 Trustee Act 1925 (`05-OPS:5.8`, `01-WOL:II.6.13`).

A scope tuple is data, and data can be typed wrong. Those two cannot be, which
is why they live here and not in the record.

This module decides; it does not write. The caller records the outcome, so the
refusal path and the gate event log stay separable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from src.records.models import require_in

# The overarching rule, and the route when authority cannot be verified.
OVERARCHING_SOURCE = "05-OPS:5.0"
CANNOT_VERIFY_SOURCE = "05-OPS:5.7"
# Trusteeship is personal — the product doc states the lifecycle rules.
TRUSTEE_SOURCES = ("05-OPS:5.8", "01-WOL:II.6.13")

AUTHORITY_SOURCES = {
    "LOA": "05-OPS:5.1",
    "LPA": "05-OPS:5.2",
    "EPA": "05-OPS:5.3",
    "deputy": "05-OPS:5.4",
    "PR": "05-OPS:5.5",
    "mandate": "05-OPS:5.6",
    "one_off": "05-OPS:5.6",
    "trustee": "05-OPS:5.8",
}

AUTHORITY_ACTIONS = frozenset({
    "information", "servicing", "switches", "withdrawals",
    "bank_change", "claim_proceeds", "trustee_change",
})

# Structural limits: refused for these types whatever the scope tuple says.
# An LOA's two exclusions are named outright in `05-OPS:5.1`; `trustee_change`
# is excluded for every instrument except actual trusteeship (`05-OPS:5.8`).
_NEVER_BY_TYPE: dict[str, frozenset[str]] = {
    "LOA": frozenset({"claim_proceeds", "bank_change", "trustee_change"}),
    "LPA": frozenset({"trustee_change"}),
    "EPA": frozenset({"trustee_change"}),
    "deputy": frozenset({"trustee_change"}),
    "PR": frozenset({"trustee_change"}),
    "mandate": frozenset({"trustee_change"}),
    "one_off": frozenset({"trustee_change"}),
    "trustee": frozenset(),
}


@dataclass(frozen=True)
class AuthorityDecision:
    """Whether this third party may do this, and why — with its sources.

    ``reason`` and ``remedy`` are caller-facing and carry no policy data: a
    refusal must not become a side channel for what it is refusing.
    """

    allowed: bool
    reason: str
    sources: tuple[str, ...]
    remedy: str = ""
    authority_id: Optional[str] = None
    customer_direct_route: bool = False


def resolve_authority(records: Iterable[Any], *, party_id: str,
                      claimed: str) -> Optional[Any]:
    """The record backing this caller's claimed relationship, if there is one.

    Both the person and the instrument must match. "I hold power of attorney"
    against a record that is only an adviser LOA resolves to nothing — the
    claim is not evidenced, which is a different failure from having no record
    at all, and both end in the same refusal.
    """
    for record in records:
        if record.party_id == party_id and record.type == claimed:
            return record
    return None


def authorise(authority: Optional[Any], *, action: str) -> AuthorityDecision:
    """Decide whether ``authority`` may perform ``action`` on its policy."""
    require_in("authority decision", "action", action, AUTHORITY_ACTIONS)

    if authority is None:
        return AuthorityDecision(
            allowed=False,
            reason="no verified authority is held for this caller",
            sources=(OVERARCHING_SOURCE, CANNOT_VERIFY_SOURCE),
            remedy=("provide the signed instrument and evidence of identity, "
                    "or ask the customer to contact us directly"),
            customer_direct_route=True)

    type_source = AUTHORITY_SOURCES.get(authority.type, OVERARCHING_SOURCE)

    if authority.status != "active":
        return AuthorityDecision(
            allowed=False,
            reason=f"the authority held is {authority.status}, not active",
            sources=(CANNOT_VERIFY_SOURCE, type_source),
            remedy=("re-evidence the instrument so it can be verified, "
                    "or ask the customer to contact us directly"),
            authority_id=authority.authority_id,
            customer_direct_route=True)

    if action in _NEVER_BY_TYPE.get(authority.type, frozenset()):
        # The instrument does not confer this, so the record cannot grant it by
        # being typed generously.
        sources = ((type_source,) + TRUSTEE_SOURCES if action == "trustee_change"
                   else (type_source,))
        return AuthorityDecision(
            allowed=False,
            reason=f"a {authority.type} does not confer authority to {action}",
            sources=tuple(dict.fromkeys(sources)),
            remedy=_remedy_for(action, authority.type),
            authority_id=authority.authority_id,
            customer_direct_route=True)

    if action not in tuple(authority.scope):
        return AuthorityDecision(
            allowed=False,
            reason=f"the verified scope does not cover {action}",
            sources=(OVERARCHING_SOURCE, type_source),
            remedy=("widen the authority to cover this instruction and "
                    "re-evidence it, or ask the customer to contact us directly"),
            authority_id=authority.authority_id,
            customer_direct_route=True)

    return AuthorityDecision(
        allowed=True,
        reason=f"{authority.type} verified and {action} is within its scope",
        sources=(OVERARCHING_SOURCE, type_source),
        authority_id=authority.authority_id)


def _remedy_for(action: str, authority_type: str) -> str:
    """What would actually make this instruction acceptable."""
    if action == "trustee_change":
        return ("trusteeship is personal — appoint or replace trustees by deed "
                "under s.36 Trustee Act 1925; an attorney cannot act as trustee")
    if action == "bank_change":
        return ("a bank change must come from the customer directly, under "
                "enhanced verification")
    if action == "claim_proceeds":
        return ("proceeds are payable to the customer, their personal "
                "representatives or the trustees — not under this instrument")
    return "ask the customer to contact us directly"
