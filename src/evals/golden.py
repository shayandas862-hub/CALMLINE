"""Golden-case shapes, validation, and loading.

The golden set is the frozen exam paper. **v4 shape (`06-RAGOPS §3.0`):** one
case per question, on one of six tiers — **R** retrieval/single-hop · **M**
multi-hop · **X** cross-document · **T** temporal · **G** guardrail/refusal ·
**O** operational. Tier G is **binary**: a guardrail case passes or it does not,
and there is no partial credit for nearly refusing.

**Every `expected_chunks` ref is checked against the Phase 1 parser at load
time.** A set naming chunks the KB no longer contains is an exam marked against
the answer sheet for a different paper: it would keep scoring, and every score
would be wrong. That check is what "evals cannot rot" means.

Validation is strict and fail-loud: a malformed case raises rather than being
silently skipped, because a dropped case quietly inflates every rate computed
over the set.

The v3 `call`/`action` shape this replaces is gone, together with the scorer
that read it. The two were a coupled pair — `score()` read `case["label"]` —
so they were removed in one commit rather than leaving the suite red across a
boundary (D-CL-075).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Optional

# `06-RAGOPS §3.0`. Tier G alone is binary — see the module docstring.
TIERS = ("R", "M", "X", "T", "G", "O")
BINARY_TIERS = frozenset({"G"})

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_KB_DIR = Path(__file__).resolve().parents[2] / "data" / "kb"


class GoldenValidationError(ValueError):
    """Raised when a golden case does not conform to its shape."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GoldenValidationError(message)


# ── the v4 six-tier case ───────────────────────────────────────────────

def is_binary(tier: str) -> bool:
    """Is this tier scored pass/fail, with no partial credit? Tier G alone is."""
    return tier in BINARY_TIERS


def kb_chunk_ids() -> set[str]:
    """Every chunk id the KB currently parses to — what a ref is checked against.

    Imported locally so ``golden.py`` can be read and its shape validated
    without pulling the corpus parser in behind it; callers who already hold the
    ids pass them instead.
    """
    from src.corpus.kb_parser import parse_kb  # local: evals -> corpus, one way

    return {chunk.chunk_id for chunk in parse_kb(_KB_DIR)}


def validate_case(case: dict[str, Any], *,
                  known_chunks: Optional[Iterable[str]] = None) -> None:
    """Validate one six-tier case in place; raise on any problem.

    ``known_chunks`` defaults to the live KB. Injecting a set keeps unit tests
    off the parser, but the **default has to be the thing that can rot** — a
    validator that only checks refs when asked is one nobody remembers to ask.
    """
    _require(isinstance(case.get("id"), str) and bool(case.get("id")),
             "case needs a non-empty id")
    case_id = case["id"]
    _require(case.get("tier") in TIERS,
             f"{case_id}: tier must be one of {list(TIERS)}, got {case.get('tier')!r}")
    _require(isinstance(case.get("question"), str) and bool(case.get("question")),
             f"{case_id}: case needs a non-empty question")
    _require(bool(case.get("failure_watched")),
             f"{case_id}: case must name the failure it watches for")

    keys = case.get("answer_keys")
    # A case with no keys scores 100% for saying nothing.
    _require(isinstance(keys, list) and len(keys) >= 1 and all(keys),
             f"{case_id}: case needs at least one non-empty answer key")

    chunks = case.get("expected_chunks")
    # recall@5 has nothing to measure against otherwise.
    _require(isinstance(chunks, list) and len(chunks) >= 1 and all(chunks),
             f"{case_id}: case needs at least one expected chunk")
    known = set(known_chunks) if known_chunks is not None else kb_chunk_ids()
    unknown = [ref for ref in chunks if ref not in known]
    _require(not unknown,
             f"{case_id}: expected chunks not in the KB: {', '.join(unknown)} — "
             "the golden set has rotted against the corpus")

    operative_date = case.get("operative_date")
    if operative_date is not None:
        _require(isinstance(operative_date, str) and bool(_ISO_DATE.match(operative_date)),
                 f"{case_id}: operative_date must be an ISO date, got {operative_date!r}")


def load_golden_set(path: Path | str,
                    *, known_chunks: Optional[Iterable[str]] = None) -> list[dict[str, Any]]:
    """Load and validate the six-tier set from one JSONL file, in file order.

    The whole set is checked against one resolved chunk-id set, so the parser
    runs once rather than 44 times.
    """
    known = set(known_chunks) if known_chunks is not None else kb_chunk_ids()
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            raise GoldenValidationError(f"line {number} is not valid JSON: {exc}") from exc
        validate_case(case, known_chunks=known)
        _require(case["id"] not in seen, f"duplicate case id: {case['id']}")
        seen.add(case["id"])
        cases.append(case)
    return cases


def tier_counts(cases: Iterable[dict[str, Any]]) -> dict[str, int]:
    """How many cases sit on each tier — the KB's own totals are 9/9/6/4/8/8."""
    counts: dict[str, int] = {}
    for case in cases:
        counts[case["tier"]] = counts.get(case["tier"], 0) + 1
    return counts
