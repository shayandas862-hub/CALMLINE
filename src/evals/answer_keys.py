"""Grade an answer against the KB's own answer keys — the coverage score.

`06-RAGOPS §3.0`'s second score: did the answer say the things the KB says it
must. The keys come from the golden case; the prose comes from the reply.

**One call per key.** The judge's standing discipline is "grade EXACTLY ONE
criterion — nothing else", and asking for five verdicts in one reply is how a
grader starts averaging them into a general impression. Strictness is the whole
point of the number.

**The judge is never shown the expected chunks.** Retrieval is scored by
recall@5, separately and without an opinion in it. A judge that could see what
*should* have been retrieved would let a well-worded miss read as a hit.

This grader blocks nothing on its own. The verdict that blocks a release —
Tier G — is computed programmatically in `scoring.py`, with no model involved.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from pydantic import ValidationError

from src.agent.console_loop import request_shape
from src.evals.judge import (DEFAULT_JUDGE_MODEL, JudgeError, _final_text,
                             _JudgeResponse)

_SYSTEM = (
    "You are a compliance QA reviewer for a UK insurance call-handling assistant. "
    "You are given ONE answer key and the assistant's answer. Decide only whether "
    "the answer COVERS that key — states the fact, or makes the point, in "
    "substance. Wording need not match. Be strict: if the answer does not clearly "
    "cover the key, fail it and say why. A wrongly-passed key is far worse than a "
    "wrongly-failed one. Reply with the required structured fields only: a boolean "
    "`passed` and a one-sentence `reason`."
)


def _prompt(case: dict[str, Any], answer_text: str, key: str) -> str:
    return (
        f"QUESTION PUT TO THE ASSISTANT:\n{case.get('question', '')}\n\n"
        f"ANSWER KEY TO CHECK FOR:\n{key}\n\n"
        f"ASSISTANT ANSWER:\n{answer_text}\n\n"
        "Does the ASSISTANT ANSWER cover that one answer key?"
    )


def _resolve(model: Optional[str]) -> str:
    return model or os.environ.get("JUDGE_MODEL") or DEFAULT_JUDGE_MODEL


def grade_answer_keys(case: dict[str, Any], record: dict[str, Any], *,
                      client: Any, model: Optional[str] = None) -> list[dict[str, Any]]:
    """Grade every answer key of one case. Raises rather than passing silently."""
    resolved = _resolve(model)
    answer_text = (record.get("reply") or {}).get("answer_text", "")
    output_format = {"type": "json_schema", "schema": _JudgeResponse.model_json_schema()}
    shape = request_shape(resolved, output_format)

    grades: list[dict[str, Any]] = []
    for key in case.get("answer_keys") or []:
        try:
            response = client.messages.create(
                model=resolved,
                max_tokens=1024,
                system=_SYSTEM,
                messages=[{"role": "user", "content": _prompt(case, answer_text, key)}],
                **shape,
            )
        except Exception as exc:  # any SDK/transport error → typed failure, never a pass
            raise JudgeError(f"judge API call failed for {case['id']} / {key!r}: {exc}") from exc
        grades.append({"key": key, **_verdict(case["id"], key, _final_text(response))})
    return grades


def _verdict(case_id: str, key: str, text: str) -> dict[str, Any]:
    try:
        parsed = _JudgeResponse(**json.loads(text))
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise JudgeError(
            f"judge produced malformed output for {case_id} / {key!r}: {exc}") from exc
    return {"covered": parsed.passed, "reason": parsed.reason}


def grade_run(cases: list[dict[str, Any]], records: list[dict[str, Any]], *,
              client: Any, model: Optional[str] = None) -> list[dict[str, Any]]:
    """Return the records with their answer keys graded. The input is not mutated.

    A case that **errored** is skipped: there is no answer to grade, and
    spending a call to be told so is waste. Its empty grade list reads as
    *ungraded* in the scorer, which is not the same as zero coverage.
    """
    by_id = {case["id"]: case for case in cases}
    graded: list[dict[str, Any]] = []
    for record in records:
        case = by_id.get(record["id"])
        if case is None or "error" in record:
            graded.append({**record, "answer_keys": record.get("answer_keys", [])})
            continue
        graded.append({**record,
                       "answer_keys": grade_answer_keys(case, record, client=client,
                                                        model=model)})
    return graded
