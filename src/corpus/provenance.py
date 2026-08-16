"""Parse a chunk's `data=` marking into aspects and a citation style (AD-CL-027).

The KB grounds every chunk one of three ways — real UK law and tax, an invented
Aldercrest operating standard, or a mix — and some chunks qualify that with a
parenthetical, optionally one per aspect:

    data=real
    data=fictional (rules real)
    data=real (not yet in force)
    data=real (structure) / fictional (terms)

That marking decides how an answer may cite the chunk, so it is parsed into a
structure and reduced to exactly one of four **citation styles**:

    cite_source              give the source URL (real law, in force)
    aldercrest_standard      label it "Aldercrest operating standard"
    mixed_explain            say which part is real and which is Aldercrest's
    effective_date_required  state the effective date — legislated, not yet live

The grammar is narrow on purpose. An unrecognised pattern **raises**: defaulting
would mean silently citing a fictional threshold as though it were law.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

CITE_SOURCE = "cite_source"
ALDERCREST_STANDARD = "aldercrest_standard"
MIXED_EXPLAIN = "mixed_explain"
EFFECTIVE_DATE_REQUIRED = "effective_date_required"

CITATION_STYLES = frozenset({
    CITE_SOURCE, ALDERCREST_STANDARD, MIXED_EXPLAIN, EFFECTIVE_DATE_REQUIRED,
})

REAL = "real"
FICTIONAL = "fictional"
MIXED = "mixed"
BASES = frozenset({REAL, FICTIONAL, MIXED})

# One aspect: a base, optionally qualified by a non-empty paren-free note.
_ASPECT = re.compile(
    rf"^(?P<base>{REAL}|{FICTIONAL}|{MIXED})(?:\s*\((?P<note>[^()]+)\))?$"
)
# A note that names the *other* provenance, e.g. "fictional (rules real)" —
# a mixed claim written as a single aspect.
_NAMES_REAL = re.compile(rf"\b{REAL}\b")
_NAMES_FICTIONAL = re.compile(rf"\b{FICTIONAL}\b")


class ProvenanceError(ValueError):
    """A `data=` value that does not fit the grammar. Never swallowed."""


@dataclass(frozen=True)
class Aspect:
    """One `base (note)` term of a `data=` value."""
    base: str
    note: str | None


@dataclass(frozen=True)
class Provenance:
    """A parsed `data=` value. Build it with `parse_provenance`, never directly."""
    raw: str
    base: str
    note: str | None
    aspects: tuple[Aspect, ...]
    citation_style: str


def parse_provenance(value: str) -> Provenance:
    """Parse a `data=` value. Raises `ProvenanceError` on anything unrecognised."""
    raw = value.strip()
    if not raw:
        raise ProvenanceError("empty data= value: provenance is never optional")

    aspects = tuple(_parse_aspect(raw, term) for term in raw.split("/"))
    return Provenance(
        raw=raw,
        base=aspects[0].base,
        note=aspects[0].note,
        aspects=aspects,
        citation_style=_citation_style(aspects),
    )


def _parse_aspect(raw: str, term: str) -> Aspect:
    match = _ASPECT.match(term.strip())
    if not match:
        raise ProvenanceError(
            f"unrecognised data= value {raw!r}: the term {term.strip()!r} is not "
            f"one of {sorted(BASES)} optionally followed by a '(note)'. "
            "Extend the grammar deliberately — never default a citation style."
        )
    return Aspect(base=match.group("base"), note=match.group("note"))


def _citation_style(aspects: tuple[Aspect, ...]) -> str:
    """Reduce parsed aspects to the one style an answer must cite by."""
    # A rule legislated but not yet live outranks everything else: the answer is
    # wrong unless it states the effective date.
    if any(a.base == REAL and a.note and "in force" in a.note.lower() for a in aspects):
        return EFFECTIVE_DATE_REQUIRED

    bases = {a.base for a in aspects}
    if MIXED in bases or {REAL, FICTIONAL} <= bases:
        return MIXED_EXPLAIN
    # A single aspect whose note names the opposite provenance is a mixed claim.
    if any(_note_names_opposite(a) for a in aspects):
        return MIXED_EXPLAIN
    return CITE_SOURCE if bases == {REAL} else ALDERCREST_STANDARD


def _note_names_opposite(aspect: Aspect) -> bool:
    if not aspect.note:
        return False
    other = _NAMES_FICTIONAL if aspect.base == REAL else _NAMES_REAL
    return bool(other.search(aspect.note.lower()))
