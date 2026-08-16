# MIT License — Copyright (c) 2026 Shayan Das
"""Judge-vs-hand-label agreement — how far the LLM-judge can be trusted.

The Phase 7 credibility number: over the qualitative points that BOTH the judge
and the human grader graded, what fraction did they agree on. Only intersecting (case, point)
pairs count — a point graded by one side but not the other can neither confirm nor
contradict, so it is excluded rather than silently scored. Every disagreement is
surfaced (they are the interesting cases and where the judge prompt gets tuned).

Pure computation — no client, no I/O. A grade is a mapping with `case_id`,
`point_id`, and a boolean `passed`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class AgreementResult:
    total: int  # (case, point) pairs graded by both sides
    agreed: int
    agreement: float  # agreed / total, or 0.0 when nothing overlaps
    per_point: dict[str, float]  # point_id → agreement fraction over its overlapping pairs
    disagreements: list[dict]  # {case_id, point_id, judge, hand}, sorted deterministically


def _index(grades: Iterable[dict]) -> dict[tuple[str, str], bool]:
    """Map (case_id, point_id) → passed. Later duplicates overwrite earlier ones."""
    out: dict[tuple[str, str], bool] = {}
    for g in grades:
        out[(g["case_id"], g["point_id"])] = bool(g["passed"])
    return out


def agreement(judge_grades: Iterable[dict], hand_grades: Iterable[dict]) -> AgreementResult:
    """Percent agreement between judge and hand grades over the pairs both graded."""
    judge = _index(judge_grades)
    hand = _index(hand_grades)
    shared = sorted(set(judge) & set(hand))  # sorted → deterministic output

    agreed = 0
    disagreements: list[dict] = []
    point_totals: dict[str, int] = {}
    point_agreed: dict[str, int] = {}

    for key in shared:
        case_id, point_id = key
        j, h = judge[key], hand[key]
        point_totals[point_id] = point_totals.get(point_id, 0) + 1
        if j == h:
            agreed += 1
            point_agreed[point_id] = point_agreed.get(point_id, 0) + 1
        else:
            disagreements.append(
                {"case_id": case_id, "point_id": point_id, "judge": j, "hand": h}
            )

    total = len(shared)
    per_point = {
        pid: point_agreed.get(pid, 0) / point_totals[pid] for pid in sorted(point_totals)
    }
    return AgreementResult(
        total=total,
        agreed=agreed,
        agreement=(agreed / total if total else 0.0),
        per_point=per_point,
        disagreements=disagreements,
    )


def verdicts_to_grades(case_id: str, verdicts: Iterable[Any]) -> list[dict]:
    """Turn a case's JudgeVerdict objects into grade records for `agreement`."""
    return [
        {"case_id": case_id, "point_id": v.point_id, "passed": bool(v.passed)} for v in verdicts
    ]
