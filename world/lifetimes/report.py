"""The refusal report — what the world could not legally build, and why.

A refused movement stops its policy, and this is where it lands. Nothing here
decides anything; the engine decides and this records, which is why they are two
modules rather than one.

The report is the phase's evidence. A build ending with an empty report built
every policy by the rules. A build that does not says exactly which policy,
which day, which movement and which rule — enough to fix the *generator*, which
is the only correct response. Adjusting the movement until it fits would produce
a book that passes its own tests and breaks the insurer's.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Refusal:
    """One movement the rulebook would not accept, and the policy it stopped.

    Five fields because a report you cannot act on is not a report: which
    policy, which day, what was proposed, how much, and the rule that said no.
    """

    policy_no: str
    on: date
    kind: str
    amount_pence: int
    reason: str

    def render(self) -> str:
        """One readable line. The build prints these."""
        return (f"{self.policy_no}  {self.on.isoformat()}  "
                f"{self.kind} {self.amount_pence}p  — {self.reason}")


class RefusalReport:
    """Every refusal a build hit, in the order it hit them.

    Append-only by construction: `refusals` hands back a tuple of frozen
    dataclasses, so a caller holding the result cannot quietly edit the evidence.
    """

    def __init__(self) -> None:
        self._refusals: list[Refusal] = []

    @property
    def refusals(self) -> tuple[Refusal, ...]:
        """An immutable snapshot, oldest first."""
        return tuple(self._refusals)

    def __len__(self) -> int:
        return len(self._refusals)

    def is_empty(self) -> bool:
        """True when every movement offered was accepted."""
        return not self._refusals

    def record(self, refusal: Refusal) -> None:
        """Append a refusal. There is no path that removes one."""
        self._refusals.append(refusal)

    def for_policy(self, policy_no: str) -> tuple[Refusal, ...]:
        """Just this policy's refusals — what stopped it, in order."""
        return tuple(r for r in self._refusals if r.policy_no == policy_no)

    def render(self) -> str:
        """The whole report, readable. An empty one says so rather than
        rendering as nothing, because a blank page and a clean build look
        identical on a terminal and mean opposite things."""
        if not self._refusals:
            return ("No refusals — every movement offered was accepted by the "
                    "rulebook.")
        lines = [f"{len(self._refusals)} refusal(s), oldest first:"]
        lines.extend(r.render() for r in self._refusals)
        return "\n".join(lines)
