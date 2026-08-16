"""The reference sheet — what a person needs to use the world.

Two hundred policies are no use to anybody who cannot get past the identity
gate on one, and the gate deliberately discloses nothing: it presents questions
without their answers, so a handler who does not already know the caller's
details cannot bluff. This sheet is the other side of that — the answers, for a
world where nobody is real.

Every row carries the four `05-OPS:3.2` checks a caller can be asked against
(policy number, name and date of birth, address or the last four of the
collection account) and then the things that make one policy worth picking over
another: its product, its status, whether it is written in trust, and who else
holds authority over it.

**Generated from the dataset, never hand-written.** A sheet somebody maintains
by hand is one that drifts the first time the world is rebuilt, and a stale
answer key is worse than none — it sends a handler to a policy that is no longer
there. `test_world_reference.py` reads the committed sheet back and fails if it
is not exactly what this module renders.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

SHEET_PATH = (Path(__file__).resolve().parents[1] / "data" / "world"
              / "reference-sheet.md")

PRODUCT_LABEL = {"lifelong_protection": "Lifelong Protection",
                 "horizon_bond": "Horizon Bond",
                 "retirement_account": "Retirement Account"}

AUTHORITY_LABEL = {"lpa": "LPA", "epa": "EPA", "deputy": "deputy",
                   "personal_representative": "personal rep"}


@dataclass(frozen=True)
class ReferenceRow:
    """One policy, and everything needed to verify a caller against it."""

    policy_no: str
    holder_name: str
    dob: str
    address: str
    bank_last4: Optional[str]
    product: str
    status: str
    in_trust: bool
    authority: str
    note: str


def reference_rows(world: Any) -> list[ReferenceRow]:
    """One row per policy, in policy-number order."""
    people = {person["party_id"]: person for person in world.people
              if "party_id" in person}

    rows = []
    for policy in sorted(world.policies, key=lambda p: p.policy_no):
        holder = people.get(policy.holder_party_id, {})
        mandate = world.bank_mandates.get(policy.policy_no)
        rows.append(ReferenceRow(
            policy_no=policy.policy_no,
            holder_name=holder.get("name", ""),
            dob=holder.get("dob", ""),
            address=holder.get("registered_address", ""),
            bank_last4=mandate.account_last4 if mandate else None,
            product=policy.product,
            status=policy.status,
            in_trust=policy.policy_no in world.trusts,
            authority=_authority_of(world, policy.policy_no),
            note=_note_of(world, policy, mandate)))
    return rows


def _authority_of(world: Any, policy_no: str) -> str:
    """Who else may act, in the shortest form that is still true."""
    parts = []
    loa = world.adviser_mandates.get(policy_no)
    if loa is not None:
        parts.append(f"adviser {loa.firm}")
    for record in world.authorities.get(policy_no, ()):
        parts.append(AUTHORITY_LABEL.get(record.type, record.type))
    return ", ".join(parts) or "—"


#: ``Trust.executed`` is a ``str`` carrying **two different meanings**: the
#: world's allocator writes ``"yes"`` / ``"no"``, and the corpus's specimen
#: records write the date the trust was executed. Both are truthy, so
#: ``if trust.executed`` waves through all six of the never-executed trusts §4
#: exists to have refused. Named here rather than guessed at; the field wants
#: splitting, and that is not this task's file to change.
NOT_EXECUTED = "no"


def _is_executed(trust: Any) -> bool:
    return str(trust.executed).strip().lower() != NOT_EXECUTED


def _note_of(world: Any, policy: Any, mandate: Any) -> str:
    """The one thing about this policy a demonstration would reach for.

    Only ever states what the record holds — a bank mandate on hold, a trust
    nobody executed — because a note that summarises rather than reports is a
    figure traceable to nothing.
    """
    notes = []
    trust = world.trusts.get(policy.policy_no)
    if trust is not None and not _is_executed(trust):
        notes.append("trust never executed")
    elif trust is not None and trust.registrable and not trust.urn:
        notes.append("registrable trust, unregistered")
    if mandate is not None and mandate.hold_until:
        notes.append("bank on hold")
    elif mandate is not None and not mandate.verified:
        notes.append("bank unverified")
    if mandate is not None and mandate.change_history:
        notes.append("bank changed")
    if policy.status != "in_force":
        notes.append(policy.status.replace("_", " "))
    return "; ".join(notes) or "—"


def render_sheet(world: Any) -> str:
    """The whole sheet, as markdown. Deterministic — same world, same bytes."""
    rows = reference_rows(world)
    lines = [
        "# The reference sheet — every policy, and how to get past the gate",
        "",
        f"> Generated from `data/world/` by `world/reference.py`. "
        f"**Never edit this file** — it is rendered from the dataset and a "
        f"test fails if the two disagree.",
        ">",
        f"> The world's birth date is **{world.born.isoformat()}**. "
        f"Two hundred policies, "
        f"{sum(len(p.entries) for p in world.policies):,} movements.",
        "",
        "The identity gate asks three checks, or four where a memorable datum "
        "is recorded, and **discloses none of the answers** — it presents the "
        "questions only. This is the answer key, for a world in which nobody "
        "is real.",
        "",
        "| Policy | Holder | Date of birth | Registered address | Bank | "
        "Product | Status | Trust | Other authority | Worth knowing |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row.policy_no}` | {row.holder_name} | {row.dob} | "
            f"{row.address} | {row.bank_last4 or '—'} | "
            f"{PRODUCT_LABEL.get(row.product, row.product)} | "
            f"{row.status.replace('_', ' ')} | "
            f"{'yes' if row.in_trust else '—'} | {row.authority} | {row.note} |")

    lines += ["", "## What each column is for", "",
              "- **Holder, date of birth, registered address, bank** — the "
              "three askable checks. A caller needs all three, because the "
              "threshold is a flat three (D-CL-046) and most records hold "
              "exactly three.",
              "- **Trust** — a policy in trust cannot be dealt with by the "
              "holder alone, and trusteeship is personal (`05-OPS:5.8`).",
              "- **Other authority** — an adviser mandate names its firm; an "
              "LPA, EPA, deputy or personal representative names none of the "
              "structural limits away.",
              "- **Worth knowing** — the reason to pick this row when "
              "demonstrating a refusal.", ""]
    return "\n".join(lines)


def write_sheet(world: Any, path: Path = SHEET_PATH) -> Path:
    path.write_text(render_sheet(world), encoding="utf-8")
    return path
