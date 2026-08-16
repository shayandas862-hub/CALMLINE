"""The knowledge-base release gate — non-zero exit blocks the release.

    python -m src.corpus.kb_validate data/kb

Five invariants, each one a way the corpus can go wrong *quietly*:

  1. **chunk_id uniqueness** — a collision leaves one chunk unreachable by
     citation and un-upsertable by id.
  2. **vocabulary conformance** — `doc`/`aud`/`type` come from closed sets. A
     typo'd audience does not error; it removes the chunk from every filtered
     search, which looks like a retrieval-quality problem forever after.
  3. **provenance parseability** — every `data=` value must resolve to a
     citation style, or an answer could attribute an Aldercrest invention as
     though it were law.
  4. **statable effective dates** — a rule legislated but not yet in force is
     only answerable if the chunk states its commencement date (AD-CL-032).
  5. **count reconciliation** — the parsed total must match the count
     `data/kb/README.md` declares. Editing the corpus without updating its own
     change record fails the gate instead of drifting unnoticed (KB README §5).

The gate **reports**; it never tracebacks. A corpus that will not parse is a
failure line, because a release gate that crashes tells you less than one that
explains.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.corpus.kb_parser import KbChunk, KbParseError, parse_kb
from src.corpus.provenance import EFFECTIVE_DATE_REQUIRED, ProvenanceError

# The closed vocabularies (`data/kb/README.md` §3).
DOCS = frozenset({
    "01-WOL", "02-BOND", "03-PEN", "04-FCA", "05-OPS", "06-RAGOPS", "07-RUNBOOK",
})
AUDIENCES = frozenset({"customer", "back_office", "ops", "regulatory", "all"})
TYPES = frozenset({
    "overview", "eligibility", "product_rule", "tax_rule", "journey", "procedure",
    "claims", "table", "legal", "ops", "glossary", "faq", "customer_info",
    "sample_record", "case_study", "routing", "sources", "worked_example",
    "caveats", "data_dictionary", "script",
})

# The corpus's own "as at" date, stated in README.md §Grounding rule and in every
# document's frontmatter. It is the corpus's property, not the wall clock — a
# "not yet in force" rule is one commencing after THIS date, whenever the gate
# happens to run. Override via `validate(kb_date=...)`.
KB_DATE = date(2026, 7, 13)

_MONTHS = ("january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december")
# "6 April 2027" or "April 2027" — a day is optional.
_DATE = re.compile(
    rf"\b(?:(?P<day>\d{{1,2}})\s+)?(?P<month>{'|'.join(_MONTHS)})\s+(?P<year>\d{{4}})\b",
    re.IGNORECASE,
)
# The README's own claim, e.g. "**441 chunks**".
_DECLARED_COUNT = re.compile(r"\*\*(\d+)\s+chunks\*\*")


@dataclass(frozen=True)
class ValidationReport:
    chunk_count: int
    embedded_count: int
    declared_count: int | None
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


def validate(kb_dir: Path | str, *, declared_count: int | None = None,
             kb_date: date = KB_DATE) -> ValidationReport:
    """Run every check over `kb_dir`. Never raises — parse failures are reported."""
    kb_dir = Path(kb_dir)
    declared = (declared_count if declared_count is not None
                else declared_chunk_count(kb_dir))
    try:
        chunks = parse_kb(kb_dir)
    except (KbParseError, ProvenanceError) as error:
        return ValidationReport(chunk_count=0, embedded_count=0,
                                declared_count=declared,
                                failures=(f"corpus does not parse: {error}",))

    failures: list[str] = []
    failures.extend(_uniqueness_failures(kb_dir))
    failures.extend(_vocabulary_failures(chunks))
    failures.extend(_effective_date_failures(chunks, kb_date))
    failures.extend(_count_failures(chunks, declared))
    return ValidationReport(
        chunk_count=len(chunks),
        embedded_count=sum(1 for c in chunks if c.embed),
        declared_count=declared,
        failures=tuple(failures),
    )


def duplicate_chunk_ids(kb_dir: Path | str) -> dict[str, list[str]]:
    """`chunk_id -> the headings claiming it`, for every id claimed twice or more."""
    claimants: dict[str, list[str]] = {}
    for chunk in parse_kb(kb_dir):
        claimants.setdefault(chunk.chunk_id, []).append(chunk.heading)
    return {cid: headings for cid, headings in claimants.items() if len(headings) > 1}


def declared_chunk_count(kb_dir: Path | str) -> int | None:
    """The chunk count `README.md` claims, or `None` if it claims none."""
    readme = Path(kb_dir) / "README.md"
    if not readme.exists():
        return None
    match = _DECLARED_COUNT.search(readme.read_text(encoding="utf-8"))
    return int(match.group(1)) if match else None


# --- the checks -----------------------------------------------------------

def _uniqueness_failures(kb_dir: Path) -> list[str]:
    return [
        f"chunk_id {chunk_id!r} is claimed by {len(headings)} headings "
        f"({', '.join(repr(h) for h in headings)}) — one of them is unreachable"
        for chunk_id, headings in duplicate_chunk_ids(kb_dir).items()
    ]


def _vocabulary_failures(chunks: list[KbChunk]) -> list[str]:
    failures: list[str] = []
    for chunk in chunks:
        for field, value, allowed in (
            ("doc", chunk.doc, DOCS),
            ("aud", chunk.aud, AUDIENCES),
            ("type", chunk.type, TYPES),
        ):
            if value not in allowed:
                failures.append(
                    f"{chunk.chunk_id}: {field}={value!r} is outside the "
                    f"vocabulary {sorted(allowed)}"
                )
    return failures


def _effective_date_failures(chunks: list[KbChunk], kb_date: date) -> list[str]:
    """A `not yet in force` chunk must state a date *after* the corpus's own date.

    "Any date present" is too weak a test: the savings-rate chunk also cites its
    Royal Assent (18 March 2026) and the Budget that announced it (26 November
    2025). Neither tells a handler when the rule bites. The commencement date is
    the one in the corpus's future.
    """
    return [
        f"{chunk.chunk_id}: provenance {chunk.provenance.raw!r} requires the "
        f"answer to state an effective date, but the chunk states no date after "
        f"the knowledge-base date ({kb_date.isoformat()})"
        for chunk in chunks
        if chunk.citation_style == EFFECTIVE_DATE_REQUIRED
        and not _states_a_date_after(f"{chunk.heading}\n{chunk.text}", kb_date)
    ]


def _states_a_date_after(text: str, kb_date: date) -> bool:
    for match in _DATE.finditer(text):
        month = _MONTHS.index(match.group("month").lower()) + 1
        # No day given → the earliest the rule could commence in that month.
        day = int(match.group("day") or 1)
        try:
            stated = date(int(match.group("year")), month, day)
        except ValueError:
            continue  # "31 February 2027" is not a date; ignore it
        if stated > kb_date:
            return True
    return False


def _count_failures(chunks: list[KbChunk], declared: int | None) -> list[str]:
    if declared is None or declared == len(chunks):
        return []
    return [
        f"count does not reconcile: README.md declares {declared} chunks, the "
        f"parser yields {len(chunks)} — update the corpus's own change record"
    ]


# --- CLI ------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Print the verdict and the real chunk count. Non-zero exit blocks release."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m src.corpus.kb_validate <kb_dir>")
        return 2

    report = validate(args[0])
    if report.passed:
        print(f"PASS — {report.chunk_count} chunks "
              f"({report.embedded_count} embeddable, "
              f"{report.chunk_count - report.embedded_count} withheld)")
        return 0

    print(f"FAIL — {len(report.failures)} problem(s) "
          f"across {report.chunk_count} chunks:")
    for failure in report.failures:
        print(f"  - {failure}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
