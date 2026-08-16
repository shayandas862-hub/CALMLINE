"""Operational attributes reconciled with the parties the policy actually has.

Phase 4 measured the fault this module removes: **the skeleton drew channels
and evidence requirements without consulting the policy's parties.** 112 of 473
cases carried evidence asserting a trustee, adviser or attorney the policy does
not have; 240 of 301 `adviser_portal` contacts sat on policies with no adviser
mandate; two refusals said a trust was never executed on trusts the record says
were. The same class of fault as start dates drawn without the holder's date of
birth, which phase 3 found and fixed.

**Everything here is a remap after the draw, never a different draw.** The
skeleton's per-policy RNG streams are left byte-identical — filtering the pool
at the draw site would shift every subsequent draw on that policy and renumber
histories that prose has already been written against. Substitutes are chosen
by the reference's own digits: deterministic, seed-free, and varied enough not
to collapse into a monoculture.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from world.operations.shapes import PlannedCase, PlannedContact, PolicyOperations

# Where an adviser-portal message really lands when there is no adviser.
FALLBACK_CHANNELS = ("portal", "email", "phone", "post")

# Requirements any policy can satisfy, whoever it has around it.
GENERIC_MET = (
    ("identity confirmed to standard verification", "05-OPS:3.2"),
    ("written instruction received", "05-OPS:6.1"),
    ("bank mandate verified", "05-OPS:6.3"),
    ("source of funds evidenced", "05-OPS:13"),
)
GENERIC_REFUSAL = ("identity could not be verified to the required standard",
                   "05-OPS:3.2")
TRUSTEE_REFUSAL = ("all trustees must instruct and one did not", "05-OPS:5.8")

NEEDS_TRUST = frozenset({"trustee signatures obtained",
                         "all trustees must instruct and one did not"})
NEEDS_UNEXECUTED_TRUST = frozenset({"the trust was never properly executed"})
NEEDS_LOA = frozenset({
    "adviser authority checked against the FCA Register",
    "an LOA cannot change the customer's bank details",
    "instruction fell outside the verified adviser scope"})
NEEDS_ATTORNEY = frozenset({
    "the power of attorney is not yet registered with the OPG"})


def _digits(reference: str) -> int:
    return int("".join(c for c in reference if c.isdigit()) or "0")


def reconcile_operations(operations: Mapping[str, PolicyOperations], *,
                         trusts: Mapping, adviser_mandates: Mapping,
                         authorities: Mapping) -> dict[str, PolicyOperations]:
    """Every contact and every piece of evidence, made true of its policy."""
    reconciled = {}
    for policy_no, ops in operations.items():
        contacts = tuple(
            _true_channel(c, policy_no in adviser_mandates)
            for c in ops.contacts)
        channels = {c.cn_ref: c.channel for c in contacts}
        cases = tuple(
            _true_case(case, channels[case.cn_ref],
                       trust=trusts.get(policy_no),
                       has_loa=policy_no in adviser_mandates,
                       has_attorney=any(a.type in ("LPA", "EPA") for a in
                                        authorities.get(policy_no, ())))
            for case in ops.cases)
        reconciled[policy_no] = PolicyOperations(policy_no, contacts, cases)
    return reconciled


def _true_channel(contact: PlannedContact, has_loa: bool) -> PlannedContact:
    """The adviser portal is a mandate-holder's door. Without a mandate the
    message arrived some ordinary way — picked by the reference's own digits."""
    if contact.channel != "adviser_portal" or has_loa:
        return contact
    return replace(contact, channel=FALLBACK_CHANNELS[
        _digits(contact.cn_ref) % len(FALLBACK_CHANNELS)])


def _true_case(case: PlannedCase, channel: str, *, trust, has_loa: bool,
               has_attorney: bool) -> PlannedCase:
    evidence = tuple(
        replace(item,
                received_via=channel,
                **_true_requirement(item, trust=trust, has_loa=has_loa,
                                    has_attorney=has_attorney))
        for item in case.evidence)
    return replace(case, evidence=evidence)


def _true_requirement(item, *, trust, has_loa: bool,
                      has_attorney: bool) -> dict[str, str]:
    """The requirement this case can actually have had, given who exists.

    Met requirements fall back to the generic pool; refusal reasons fall back
    to the one refusal every policy supports — identity. The single graded case
    is a trust that exists but is executed: "never properly executed" is false
    of it, while "all trustees must instruct" is exactly how an executed trust
    refuses, so the substitution stays inside trust law rather than jumping to
    identity.
    """
    need = item.requirement
    if need in NEEDS_TRUST and trust is None:
        pass
    elif need in NEEDS_UNEXECUTED_TRUST and trust is None:
        pass
    elif need in NEEDS_UNEXECUTED_TRUST and trust.executed != "no":
        requirement, source = TRUSTEE_REFUSAL
        return {"requirement": requirement, "requirement_source": source}
    elif need in NEEDS_LOA and not has_loa:
        pass
    elif need in NEEDS_ATTORNEY and not has_attorney:
        pass
    else:
        return {}

    if item.satisfies == "yes":
        requirement, source = GENERIC_MET[
            _digits(item.evidence_id) % len(GENERIC_MET)]
    else:
        requirement, source = GENERIC_REFUSAL
    return {"requirement": requirement, "requirement_source": source}
