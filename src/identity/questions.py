"""The standard-verification check set — `05-OPS:3.2`, on the tick model.

**Three of four**: policy number; full name + DOB; registered correspondence
address *or* the last four digits of the collection account; the memorable-data
item set at onboarding. The "or" sits **inside** the third check, so there are
four checks and never five.

Since D-CL-114 each check carries what the record **holds**, because the screen
is the handler's: a handler who cannot see the details cannot judge whether
what the caller says matches them. The caller-facing rules of
`07-RUNBOOK:4.1` survive intact and are structural here, not cosmetic:

* a ``prompt`` — the words read aloud — never contains the value it checks;
* the memorable item is flagged ``ask_only``: shown to the handler, never read
  out, because a memorable word spoken by the handler verifies nobody;
* a check the record cannot answer is **not shown**. A tick against a value
  the record does not hold would be a tick against nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# The rule and its source, kept together so a reader never has to guess which
# clause produced the threshold (AD-CL-028).
SV_SOURCE = "05-OPS:3.2"
SV_THRESHOLD = 3

# Order matters: this is the order a handler works down the four checks.
QUESTION_KINDS = ("policy_no", "name_dob", "address_or_bank", "memorable")

_PROMPTS = {
    "policy_no": "Please read me your policy number.",
    "name_dob": "Please confirm your full name and date of birth.",
    "address_or_bank": (
        "Please confirm the address we hold for you — or, if you would rather, "
        "the last four digits of the account your payments come from."
    ),
    "memorable": "Please give me the memorable item set up on the account.",
}


@dataclass(frozen=True)
class HeldField:
    """One held value the handler compares the caller's words against.

    ``ask_only`` marks a value that must never be read out — the caller has to
    state it unprompted. ``mono`` is a display hint for reference-shaped data.
    """

    label: str
    value: str
    mono: bool = False
    ask_only: bool = False


@dataclass(frozen=True)
class HeldCheck:
    """One `05-OPS:3.2` check: the prompt read aloud, and the held values.

    ``prompt`` carries no held value — everything the handler compares against
    sits in ``fields``, on the screen, never in the spoken words.
    """

    kind: str
    prompt: str
    fields: tuple[HeldField, ...] = field(default_factory=tuple)
    source: str = SV_SOURCE


def askable_kinds(party: Any, policy: Any) -> tuple[str, ...]:
    """The checks this record can actually answer, in order."""
    kinds = ["policy_no", "name_dob", "address_or_bank"]
    if getattr(party, "memorable", None):
        kinds.append("memorable")
    return tuple(kinds)


def _fields_for(kind: str, party: Any, policy: Any) -> tuple[HeldField, ...]:
    if kind == "policy_no":
        return (HeldField("Policy number", policy.policy_no, mono=True),)
    if kind == "name_dob":
        return (HeldField("Full name", party.name),
                HeldField("Date of birth", party.dob, mono=True))
    if kind == "address_or_bank":
        fields = [HeldField("Registered address", party.registered_address)]
        last4 = getattr(policy, "bank_last4", None)
        if last4:
            fields.append(HeldField("Account last 4", last4, mono=True))
        return tuple(fields)
    return (HeldField("Memorable item", party.memorable, ask_only=True),)


def held_checks(party: Any, policy: Any) -> tuple[HeldCheck, ...]:
    """The panel for this party/policy pair: prompt aloud, held values shown."""
    return tuple(HeldCheck(kind=kind, prompt=_PROMPTS[kind],
                           fields=_fields_for(kind, party, policy))
                 for kind in askable_kinds(party, policy))
