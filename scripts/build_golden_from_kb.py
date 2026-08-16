#!/usr/bin/env python3
"""Regenerate the golden eval set from the knowledge base itself.

    python scripts/build_golden_from_kb.py          # rewrite data/golden/golden_evals.jsonl
    python scripts/build_golden_from_kb.py --check  # exit 1 if the committed file is stale

`06-RAGOPS §3.1–3.6` specifies all 44 cases in six atomic markdown tables —
question, answer keys, expected chunks, and the failure each case watches for.
`golden_evals.jsonl` was named in §3.0 and never delivered, so the set is
**derived from the corpus** rather than typed out beside it. Both the script and
its output are committed: the output is what the harness loads, and the script
is what proves the output was not invented.

The tables are read **positionally**, not by column heading. Tier G's table
titles its columns "Prompt" and "Required behaviour" where the others say
"Question" and "Answer keys"; the columns mean the same thing in the same order,
and matching on heading text would break on that difference alone.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

KB_DOC = ROOT / "data" / "kb" / "06_RAG_Ops_Evals_and_Change_Management.md"
GOLDEN_PATH = ROOT / "data" / "golden" / "golden_evals.jsonl"

# `### 3.1 Tier R — retrieval and single-hop (atomic)` → ("3.1", "R")
_TIER_HEADING = re.compile(r"^###\s+3\.(\d)\s+Tier\s+([RMXTGO])\b", re.M)
# A table row: `| E01 | question | keys | chunks | failure |`
_ROW = re.compile(r"^\|\s*(E\d{2})\s*\|(.+?)\|?\s*$", re.M)
# The one asked-at date the KB states, on E24: `(asked 13 Jul 2026)`.
_ASKED_AT = re.compile(r"\s*\(asked\s+(\d{1,2})\s+([A-Za-z]{3})\w*\s+(\d{4})\)")

_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


class GoldenBuildError(RuntimeError):
    """The KB does not contain what the generator expects. Never a partial set."""


def build_cases(doc: str | None = None) -> list[dict[str, Any]]:
    """Every case in `06-RAGOPS §3`, in document order, tier by tier."""
    text = doc if doc is not None else KB_DOC.read_text(encoding="utf-8")
    sections = _tier_sections(text)
    if not sections:
        raise GoldenBuildError(f"no tier tables found in {KB_DOC.name}")
    cases: list[dict[str, Any]] = []
    for tier, body in sections:
        cases.extend(_cases_in(tier, body))
    return cases


def _tier_sections(text: str) -> list[tuple[str, str]]:
    """(tier letter, section body) for each of the six tier tables, in order."""
    marks = list(_TIER_HEADING.finditer(text))
    return [(m.group(2), text[m.end():(marks[i + 1].start() if i + 1 < len(marks) else len(text))])
            for i, m in enumerate(marks)]


def _cases_in(tier: str, body: str) -> list[dict[str, Any]]:
    cases = []
    for match in _ROW.finditer(body):
        columns = [c.strip() for c in match.group(2).split("|")]
        if len(columns) < 4:
            raise GoldenBuildError(
                f"{match.group(1)}: expected 4 columns after the id, got {len(columns)}")
        question, keys, chunks, failure = columns[:4]
        case: dict[str, Any] = {
            "id": match.group(1),
            "tier": tier,
            "question": question,
            "answer_keys": _split(keys, ";"),
            "expected_chunks": _split(chunks, ","),
            "failure_watched": failure,
        }
        _apply_asked_at(case)
        cases.append(case)
    return cases


def _split(cell: str, separator: str) -> list[str]:
    """The table's own separator. Answer keys use `;`, chunk lists use `,`.

    Nothing is split on `+`: the tables use it inside a single requirement
    ("RAS 20% + claim extra"), so splitting there would turn one answer key into
    two fragments neither of which is the thing being asked for.
    """
    return [part.strip().strip("*") for part in cell.split(separator) if part.strip()]


def _apply_asked_at(case: dict[str, Any]) -> None:
    """Lift `(asked 13 Jul 2026)` out of the question and into the case.

    Only where the KB states one. The other three temporal cases express their
    time split inside their answer keys, which is where the table puts it and
    what the judge grades — giving them a date the corpus never stated would be
    inventing structure (D-CL-078).
    """
    found = _ASKED_AT.search(case["question"])
    if not found:
        return
    day, month, year = found.group(1), found.group(2).lower(), found.group(3)
    if month not in _MONTHS:
        raise GoldenBuildError(f"{case['id']}: unrecognised month {found.group(2)!r}")
    case["question"] = _ASKED_AT.sub("", case["question"]).strip()
    case["operative_date"] = f"{year}-{_MONTHS[month]:02d}-{int(day):02d}"


def render_jsonl(cases: list[dict[str, Any]]) -> str:
    """One case per line, keys in a fixed order — a stable diff, re-run to re-run."""
    order = ("id", "tier", "question", "answer_keys", "expected_chunks",
             "failure_watched", "operative_date")
    lines = [json.dumps({k: case[k] for k in order if k in case}, ensure_ascii=False)
             for case in cases]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Regenerate the golden eval set from the KB.")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if the committed file is stale, write nothing")
    args = parser.parse_args(argv[1:])

    from src.evals.golden import tier_counts, validate_case  # noqa: E402

    cases = build_cases()
    for case in cases:  # every ref checked against the live parser before it is written
        validate_case(case)
    body = render_jsonl(cases)

    if args.check:
        current = GOLDEN_PATH.read_text(encoding="utf-8") if GOLDEN_PATH.exists() else ""
        if current != body:
            print("golden set is STALE — re-run scripts/build_golden_from_kb.py",
                  file=sys.stderr)
            return 1
        print(f"golden set is current · {len(cases)} cases {tier_counts(cases)}")
        return 0

    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_PATH.write_text(body, encoding="utf-8")
    print(f"wrote {GOLDEN_PATH.relative_to(ROOT)} · {len(cases)} cases {tier_counts(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
