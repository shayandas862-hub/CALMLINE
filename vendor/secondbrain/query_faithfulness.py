"""Faithfulness checker — Gemini Flash evaluates answer claims against context.

For each factual claim in the generated answer, Gemini scores how well it is
supported by the retrieved context (0.0–1.0). Claims below 0.7 are flagged.
The overall score is the arithmetic mean of per-claim scores (0.0 when no
claims are found).

Early return: empty answers are not sent to Gemini — they receive a zero score
with no claims and no span.

Inject _client in tests. _client must expose:
    async def evaluate_faithfulness(answer: str, context_text: str) -> dict
where dict = {"claims": [{"claim": str, "score": float}, ...]}
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.observability.tracer import _NoopTrace
from app.query.assembler import AssembledContext

log = get_logger("app.query.faithfulness")


_FAITHFULNESS_THRESHOLD = 0.7
_GEMINI_MODEL = "gemini-2.5-flash"

_EVAL_PROMPT = """\
You are evaluating whether an answer is faithful to the provided context.

CONTEXT:
{context}

ANSWER:
{answer}

Extract each distinct factual claim from the ANSWER. Score how well each claim \
is supported by the CONTEXT on a scale of 0.0 to 1.0:
  1.0 = fully and explicitly supported by the context
  0.5 = partially supported or reasonably implied
  0.0 = not supported, contradicted, or hallucinated

Return ONLY valid JSON in this exact format:
{{
  "claims": [
    {{"claim": "exact claim text", "score": 0.95}},
    {{"claim": "another claim", "score": 0.0}}
  ]
}}

If the answer makes no factual claims, return: {{"claims": []}}"""


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

@dataclass
class ClaimScore:
    claim: str
    score: float
    is_faithful: bool   # score >= _FAITHFULNESS_THRESHOLD


@dataclass
class FaithfulnessResult:
    overall_score: float        # mean of per-claim scores; 0.0 when no claims
    claims: list[ClaimScore]
    is_faithful: bool           # overall_score >= _FAITHFULNESS_THRESHOLD


# ---------------------------------------------------------------------------
# Production client (Gemini Flash with JSON mode)
# ---------------------------------------------------------------------------

class _GeminiFaithfulnessClient:
    def __init__(self, api_key: str) -> None:
        from google import genai
        self._client = genai.Client(api_key=api_key)

    async def evaluate_faithfulness(self, answer: str, context_text: str) -> dict:
        from google.genai import types

        prompt = _EVAL_PROMPT.format(context=context_text, answer=answer)
        response = await self._client.aio.models.generate_content(
            model=_GEMINI_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_result(raw_claims: list[dict]) -> FaithfulnessResult:
    """Convert raw claim dicts from the client into a FaithfulnessResult."""
    claims = [
        ClaimScore(
            claim=entry["claim"],
            score=float(entry["score"]),
            is_faithful=float(entry["score"]) >= _FAITHFULNESS_THRESHOLD,
        )
        for entry in raw_claims
    ]
    if not claims:
        return FaithfulnessResult(overall_score=0.0, claims=[], is_faithful=False)
    overall = sum(c.score for c in claims) / len(claims)
    return FaithfulnessResult(
        overall_score=overall,
        claims=claims,
        is_faithful=overall >= _FAITHFULNESS_THRESHOLD,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def check_faithfulness(
    answer: str,
    context: AssembledContext,
    *,
    max_retries: int = 3,
    _client: Any = None,
    _trace: Any = None,
) -> FaithfulnessResult:
    """Evaluate how faithfully *answer* is grounded in *context*.

    Retries the client call up to `max_retries` times with exponential backoff
    (BUG #8 + BUG #10) so transient Gemini failures don't fail the whole query.
    Returns a zero-score result immediately for empty answers without calling
    the client or opening a trace span.
    """
    if not answer.strip():
        return FaithfulnessResult(overall_score=0.0, claims=[], is_faithful=False)

    trace = _trace or _NoopTrace()
    client = _client or _GeminiFaithfulnessClient(get_settings().GEMINI_API_KEY)

    with trace.span(
        "faithfulness_check",
        input={"answer_length": len(answer), "context_length": len(context.context_text)},
    ):
        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                raw = await client.evaluate_faithfulness(answer, context.context_text)
                return _build_result(raw.get("claims", []))
            except Exception as exc:
                last_error = exc
                log.warning("faithfulness_attempt_failed", attempt=attempt, error=str(exc))
                if attempt < max_retries:
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))

        raise RuntimeError(
            f"Faithfulness check failed after {max_retries} attempts: {last_error}"
        )
