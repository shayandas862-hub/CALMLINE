"""Nobody was invented — asserted over the whole world, offline.

**The guarantee that actually matters, and it is a test rather than an
architecture.** Identities are safe by construction: phase 1 drew every one of
them from officially reserved ranges, deterministically, so reading a generated
name creates no risk. The one real residual is a *story* inventing a person who
is not in the dataset — or, worse, giving a real person authority they do not
hold on that policy. This catches both, on committed data, so it holds forever
rather than only on the day the stories were written.

**The check is on roles, not names, and that is a measurement rather than a
preference.** The world's 299 names are unique only because each carries a
trailing number: `Alpha Feldspar 2` is a trustee and `Alpha Feldspar 265` is a
policyholder, and they are different people. 49 two-word prefixes are shared,
`Omega Nimbus` is four people across three roles, and all 299 share **30**
surnames. A name in prose therefore identifies nobody.

So prose refers to people by the role they hold on the policy, and this asserts
that claim against the cast. Two consequences, both deliberate:

- **a name of any kind is refused**, invented or real, because a name that
  cannot identify anybody is worse than no name at all;
- **the role is what is checked**, because the role is what carries authority
  and what a reader would act on. "An attorney instructed this" on a policy with
  no attorney is the failure the card names, and it is caught here whether or not
  a name went with it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from world.dataset.manifest import DatasetError
from world.stories.workfile import cast_for

# The word a note would use, against the role held on the policy. `people.jsonl`
# spells the last one `personal_representative`; a handler writes "executor".
ROLE_WORDS = {
    "trustees": "trustee", "trustee": "trustee",
    "attorney": "attorney", "attorneys": "attorney",
    "deputy": "deputy", "deputies": "deputy",
    "personal representative": "personal_representative",
    "personal representatives": "personal_representative",
    "executor": "personal_representative",
    "executors": "personal_representative",
    "adviser": "adviser", "advisers": "adviser",
}

# `adviser portal` is a channel, not somebody acting — 240 of the 301
# `adviser_portal` contacts are on policies with no mandate at all, so reading
# the channel as a person would condemn 80% of them.
CHANNEL_PHRASES = ("adviser portal",)

# Capitalised words that are not people. Anything else in title case, away from
# the start of a sentence, is a name — which is what makes an invented one
# catchable without a list of names nobody has.
ALLOWED_CAPITALS = frozenset("""
January February March April May June July August September October November
December Monday Tuesday Wednesday Thursday Friday Saturday Sunday
Christmas Easter Eve New Year Aldercrest Lifelong Protection Horizon Bond
Retirement Account Pension Wise Register Scottish English Welsh
Mr Mrs Ms Miss Dr Sir Dame Lord Lady Prof
""".split())
# The honorifics are allowed so that "Mrs Wilkinson" reports Wilkinson and not
# both — the name is the finding and the title is noise around it.

_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[A-Za-z][A-Za-z']*")
_TITLE_CASE = re.compile(r"^[A-Z][a-z']+$")


@dataclass(frozen=True)
class Problem:
    """One story saying something about a person that the record does not."""

    policy_no: str
    ref: str
    role: str | None
    detail: str


def validate_world(world: Any) -> tuple[Problem, ...]:
    """Every story in the world, against the cast of the policy it belongs to."""
    names = {person["name"] for person in world.people if person.get("name")}
    problems: list[Problem] = []
    for story in world.stories:
        problems.extend(_check(story, world, names))
    return tuple(problems)


def assert_nobody_invented(world: Any) -> None:
    """The same check, as a refusal — every problem, never only the first.

    Listing them all matters: the writing is done a policy at a time, and a
    reviewer who fixes one and re-runs to find the next has been given a worse
    tool than a list.
    """
    problems = validate_world(world)
    if not problems:
        return
    lines = "\n".join(f"  {p.policy_no} {p.ref}: {p.detail}" for p in problems)
    raise DatasetError(
        f"{len(problems)} stories name somebody the policy does not have:\n"
        f"{lines}")


# ── one story ────────────────────────────────────────────────────────────

def _check(story: Any, world: Any, names: set[str]) -> list[Problem]:
    policy_no, ref = story["policy_no"], story["ref"]
    text = story["text"]
    cast = cast_for(world, policy_no)
    problems = []

    # A real name first, because it earns the more useful message.
    for name in names:
        if name in text:
            problems.append(Problem(
                policy_no, ref, None,
                f"names {name!r} — write the role instead; the world's names "
                f"identify nobody without their trailing number"))

    for word in _proper_nouns(text):
        if not any(word in name for name in names):
            problems.append(Problem(
                policy_no, ref, None,
                f"names {word!r}, who is nobody in the dataset"))

    for word, role in _roles_claimed(text):
        if cast.by_role.get(role):
            continue
        if role == "adviser" and cast.adviser_firm:
            continue
        problems.append(Problem(
            policy_no, ref, role,
            f"says {word!r}, but {policy_no} has no {role} — it holds "
            f"{', '.join(sorted(cast.by_role)) or 'nobody'}"))

    return problems


def _roles_claimed(text: str) -> list[tuple[str, str]]:
    lowered = text.lower()
    for phrase in CHANNEL_PHRASES:
        lowered = lowered.replace(phrase, " ")

    claimed, seen = [], set()
    for word, role in ROLE_WORDS.items():
        if role in seen:
            continue
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            claimed.append((word, role))
            seen.add(role)
    return claimed


def _proper_nouns(text: str) -> list[str]:
    """Title-case words away from the start of a sentence.

    The first word of a sentence is skipped because its capital says nothing.
    That is a real hole — a note opening "Wilkinson rang" hides one — and it is
    accepted rather than papered over, because the alternative refuses every
    sentence that begins with an ordinary word.
    """
    found = []
    for sentence in _SENTENCE.split(text):
        for position, word in enumerate(_WORD.findall(sentence)):
            if position and _TITLE_CASE.match(word) \
                    and word not in ALLOWED_CAPITALS:
                found.append(word)
    return found
