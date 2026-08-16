# MIT License — Copyright (c) 2026 Shayan Das
"""The LLM-judge — the qualitative scorer for the four rubric points code can't grade.

Adapted from the author's earlier faithfulness checker
(vendor/secondbrain/query_faithfulness.py): the injectable-client seam, the
structured-JSON contract, the threshold-typed result, and the hard rule that a
malformed model reply becomes a typed error, NEVER a silent pass. Retargeted from
Gemini-grounding to Claude + CalmLine's FCA rubric points R5/R8/R11/R12, each
graded over the agent's `answer_text` (the grounded prose the agent returns).

The judge grades ONE (point, case, output) at a time → pass/fail + one-line reason.
`client` is injected so this unit-tests with zero live calls; the production path
passes a real Anthropic client. Opus 4.8 SDK contract mirrors the agent loop:
adaptive thinking, effort=high, structured output via `output_config.format`, and
NO sampling params (`temperature`/`top_p`/`top_k`/`budget_tokens` 400 on Opus 4.8).
`JUDGE_MODEL` is env-configurable; the judge prompt (unlike the agent) may be
iterated against hand grades in Phase 7.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, ValidationError

from src.agent.console_loop import request_shape

# Revisited at phase 6, as D-CL-024 said it would be: the judge runs on the same
# model as the agent it grades (D-CL-087). Env-overridable via JUDGE_MODEL.
DEFAULT_JUDGE_MODEL = "claude-haiku-4-5"


class JudgeError(RuntimeError):
    """Raised on any API failure or malformed judge output — never a silent pass."""


@dataclass(frozen=True)
class QualitativePoint:
    point_id: str
    title: str
    criterion: str  # the rubric check, applied to the agent's answer_text


@dataclass(frozen=True)
class JudgeVerdict:
    point_id: str
    passed: bool
    reason: str


class _JudgeResponse(BaseModel):
    """The structured reply the judge model must return.

    ``extra="forbid"`` is not style: it is what makes the generated JSON schema
    carry ``additionalProperties: false``, which the API **requires** of any
    object in ``output_config.format``. Without it every judge call is rejected
    with a 400 — which is exactly how the first live baseline run found it, after
    the agent half had already been paid for (D-CL-097).
    """

    model_config = ConfigDict(extra="forbid")

    passed: bool
    reason: str


# The four qualitative points (rubric.md §B/C/D/E). Criteria are paraphrased checks,
# each tied to a public FCA basis — not reproductions of FCA prose.
QUALITATIVE_POINTS: tuple[QualitativePoint, ...] = (
    QualitativePoint(
        "R5",
        "Handling reflects the flag",
        "When a vulnerability is flagged, the answer adapts — slower pace, plainer "
        "language, extra care, or signposting — rather than proceeding identically to "
        "a non-vulnerable caller. Basis: FCA FG21/1, taking practical action.",
    ),
    QualitativePoint(
        "R8",
        "Answer is faithful to the cited clause",
        "The answer states only what the cited policy clause actually says; it does "
        "not overstate, distort, or add coverage the clause does not grant. Basis: "
        "FCA PRIN 2A.5, consumer understanding (accurate, not misleading).",
    ),
    QualitativePoint(
        "R11",
        "No personal recommendation / regulated advice",
        "The answer never tells the caller what they personally should do with their "
        "policy (surrender, switch, whether to claim). It states policy facts only; "
        "advice-seeking is refused, not answered. Basis: FCA PRIN 2A.2, avoid "
        "foreseeable harm — a personal recommendation crosses the regulated-advice line.",
    ),
    QualitativePoint(
        "R12",
        "Tone is calm, plain, and empathetic",
        "Especially on distress or bereavement: no jargon dumps, no false reassurance, "
        "and the caller's situation is acknowledged. Basis: FCA PRIN 2A.6 consumer "
        "support; FG21/1 communications.",
    ),
)

_BY_ID = {p.point_id: p for p in QUALITATIVE_POINTS}


def get_point(point_id: str) -> QualitativePoint:
    """Look up a qualitative point by id (e.g. 'R12'); raises KeyError if unknown."""
    return _BY_ID[point_id]


_JUDGE_SYSTEM = (
    "You are a compliance QA reviewer for a UK insurance call-handling assistant. "
    "You grade the assistant's answer against EXACTLY ONE criterion — nothing else. "
    "Be strict: pass only if the answer clearly satisfies the criterion; when in doubt, "
    "fail it and say why. A wrongly-passed answer is far worse than a wrongly-failed one. "
    "Reply with the required structured fields only: a boolean `passed` and a one-sentence "
    "`reason`."
)


def _transcript_text(case: dict) -> str:
    turns = case.get("transcript") or []
    return "\n".join(f"{t.get('who', '?')}: {t.get('text', '')}" for t in turns)


def _flags_text(output: dict) -> str:
    flags = output.get("vulnerability_flags") or []
    if not flags:
        return "(none flagged)"
    return ", ".join(f"{f.get('name', '?')} [{f.get('driver', '?')}]" for f in flags)


def _build_user_prompt(
    point: QualitativePoint, case: dict, output: dict, clause_text: Optional[str]
) -> str:
    cited = output.get("citation_clause_ref") or "(none)"
    clause_block = (
        f"\nCITED CLAUSE ({cited}):\n{clause_text}"
        if clause_text
        else f"\nCITED CLAUSE REF: {cited} (clause text not supplied)"
    )
    return (
        f"CRITERION TO GRADE ({point.point_id} — {point.title}):\n{point.criterion}\n\n"
        f"CALLER TRANSCRIPT:\n{_transcript_text(case)}\n\n"
        f"VULNERABILITY FLAGS THE ASSISTANT RAISED: {_flags_text(output)}\n"
        f"{clause_block}\n\n"
        f"ASSISTANT ANSWER TO THE CALLER:\n{output.get('answer_text', '')}\n\n"
        f"Does the ASSISTANT ANSWER satisfy the criterion? Grade only this criterion."
    )


def _final_text(response: Any) -> str:
    parts = [getattr(b, "text", "") for b in response.content if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()


def _parse(point_id: str, text: str) -> JudgeVerdict:
    try:
        data = json.loads(text)
        parsed = _JudgeResponse(**data)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise JudgeError(f"judge produced malformed output for {point_id}: {exc}") from exc
    return JudgeVerdict(point_id=point_id, passed=parsed.passed, reason=parsed.reason)


def judge_point(
    point: QualitativePoint,
    case: dict,
    output: dict,
    *,
    client: Any,
    model: Optional[str] = None,
    clause_text: Optional[str] = None,
) -> JudgeVerdict:
    """Grade one qualitative point over one case's agent output. Never a silent pass."""
    resolved_model = model or os.environ.get("JUDGE_MODEL") or DEFAULT_JUDGE_MODEL
    output_format = {"type": "json_schema", "schema": _JudgeResponse.model_json_schema()}
    # The shape the model will actually accept. This used to hardcode adaptive
    # thinking for every model, which would have failed outright the first time
    # the judge ran on a model that predates it — the console loop has asked
    # this question since phase 4, and the judge simply never did (D-CL-088).
    shape = request_shape(resolved_model, output_format)
    try:
        response = client.messages.create(
            model=resolved_model,
            max_tokens=1024,
            system=_JUDGE_SYSTEM,
            messages=[
                {"role": "user", "content": _build_user_prompt(point, case, output, clause_text)}
            ],
            **shape,
        )
    except Exception as exc:  # any SDK/transport error → typed failure, never a pass
        raise JudgeError(f"judge API call failed for {point.point_id}: {exc}") from exc

    return _parse(point.point_id, _final_text(response))


def applicable_points(output: dict) -> list[QualitativePoint]:
    """Which qualitative points apply to one agent output.

    The points grade answer prose, so they apply only to `decision == "answer"`
    outputs. R8/R11/R12 apply to every answer; R5 (handling reflects the flag)
    applies only when the output actually flagged a vulnerability — with no flag
    there is nothing for the handling to reflect. Deliberately simple and
    run-derived (no labels needed); tune in Phase 7 against hand grades.
    """
    if output.get("decision") != "answer":
        return []
    points: list[QualitativePoint] = []
    if output.get("vulnerability_flags"):
        points.append(get_point("R5"))
    points.extend(get_point(pid) for pid in ("R8", "R11", "R12"))
    return points


def judge_run(
    cases: list[dict],
    run_records: list[dict],
    *,
    client: Any,
    model: Optional[str] = None,
    clause_text_by_ref: Optional[dict] = None,
) -> list[dict]:
    """Grade every applicable qualitative point across a cached run's answer cases.

    Returns grade records `{case_id, point_id, passed, reason}` — the `passed`
    fields drop straight into `agreement()` against the author's hand grades, and
    `reason` is kept for the report. `clause_text_by_ref` resolves the cited
    clause text so R8 (faithfulness) can compare the answer to the clause.
    """
    by_id = {c["id"]: c for c in cases}
    clause_texts = clause_text_by_ref or {}
    grades: list[dict] = []
    for record in run_records:
        output = record.get("output") or {}
        points = applicable_points(output)
        if not points:
            continue
        case = by_id.get(record["id"], {"id": record["id"], "transcript": []})
        clause_text = clause_texts.get(output.get("citation_clause_ref"))
        for point in points:
            verdict = judge_point(
                point, case, output, client=client, model=model, clause_text=clause_text
            )
            grades.append(
                {
                    "case_id": record["id"],
                    "point_id": verdict.point_id,
                    "passed": verdict.passed,
                    "reason": verdict.reason,
                }
            )
    return grades
