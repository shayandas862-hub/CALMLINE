"""RAGAS-style eval runner for the source project's query pipeline.

Metrics: faithfulness (engine Gemini), answer_relevance (embedding cosine sim),
context_precision and context_recall (item_id matching, deterministic).

CLI: cd backend && python -m evals.ragas.runner [--limit N] [--user-id UUID] [--verbose]
Pass --user-id matching the Supabase account that owns the ingested documents.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_GOLDEN_PATH = Path(__file__).parents[1] / "golden" / "golden_dataset.json"
_REPORTS_DIR = Path(__file__).parents[1] / "reports"

THRESHOLDS = {
    "faithfulness": 0.85,
    "answer_relevance": 0.80,
    "context_precision": 0.70,
    "context_recall": 0.75,
}


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def load_golden_dataset(path: Path = _GOLDEN_PATH) -> list[dict]:
    """Load and return the golden QA pairs from *path*."""
    with open(path) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def compute_context_precision(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    """Fraction of retrieved item IDs that are in the expected set."""
    if not retrieved_ids:
        return 1.0 if not expected_ids else 0.0
    if not expected_ids:
        return 0.0
    return len(set(retrieved_ids) & set(expected_ids)) / len(set(retrieved_ids))


def compute_context_recall(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    """Fraction of expected item IDs that were retrieved."""
    if not expected_ids:
        return 1.0  # correct refusal: nothing expected, nothing needed
    if not retrieved_ids:
        return 0.0
    return len(set(retrieved_ids) & set(expected_ids)) / len(set(expected_ids))


async def compute_answer_relevance(question: str, answer: str) -> float:
    """Cosine similarity between question and answer embeddings (0–1 proxy for relevance)."""
    if not answer.strip():
        return 0.0
    try:
        from openai import AsyncOpenAI
        from app.core.config import get_settings

        client = AsyncOpenAI(api_key=get_settings().OPENAI_API_KEY)
        resp = await client.embeddings.create(
            model="text-embedding-3-small",
            input=[question, answer],
        )
        q_emb = resp.data[0].embedding
        a_emb = resp.data[1].embedding
        dot = sum(x * y for x, y in zip(q_emb, a_emb))
        norm_q = sum(x ** 2 for x in q_emb) ** 0.5
        norm_a = sum(x ** 2 for x in a_emb) ** 0.5
        return float(dot / (norm_q * norm_a + 1e-10))
    except Exception as exc:
        logger.warning("answer_relevance computation failed: %s", exc)
        return 0.0


# ---------------------------------------------------------------------------
# Single-item runner
# ---------------------------------------------------------------------------

async def run_single(item: dict, user_id: str, runner) -> dict:
    """Run one golden item through *runner* and return a scored result record."""
    result = await runner(item["question"], user_id)

    # Extract retrieved item_ids from source metadata (requires assembler fix)
    retrieved_ids = list({
        s.get("metadata", {}).get("item_id", "")
        for s in result.sources
        if s.get("metadata", {}).get("item_id")
    })
    expected_ids: list[str] = item.get("expected_source_item_ids", [])

    # Faithfulness: use engine score; assign 1.0/0.0 for correct/wrong refusals
    if result.faithfulness is not None:
        faithfulness_score: float | None = result.faithfulness.overall_score
    elif result.is_refusal:
        faithfulness_score = 1.0 if not expected_ids else 0.0
    else:
        faithfulness_score = None

    answer_relevance = await compute_answer_relevance(item["question"], result.answer)

    return {
        "id": item["id"],
        "question": item["question"],
        "category": item["category"],
        "intent": item["intent"],
        "answer": result.answer,
        "is_refusal": result.is_refusal,
        "contexts_count": len([s for s in result.sources if s.get("content")]),
        "retrieved_ids": retrieved_ids,
        "expected_ids": expected_ids,
        "faithfulness": faithfulness_score,
        "answer_relevance": answer_relevance,
        "context_precision": compute_context_precision(retrieved_ids, expected_ids),
        "context_recall": compute_context_recall(retrieved_ids, expected_ids),
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _safe_mean(values: list) -> float:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def _category_stats(items: list[dict]) -> dict:
    return {
        "count": len(items),
        "faithfulness": _safe_mean([r["faithfulness"] for r in items]),
        "answer_relevance": _safe_mean([r["answer_relevance"] for r in items]),
        "context_precision": _safe_mean([r["context_precision"] for r in items]),
        "context_recall": _safe_mean([r["context_recall"] for r in items]),
    }


def aggregate_metrics(results: list[dict]) -> dict:
    """Compute overall and per-category mean metrics."""
    by_category: dict[str, list] = {}
    for r in results:
        by_category.setdefault(r["category"], []).append(r)

    return {
        "overall": _category_stats(results),
        "per_category": {cat: _category_stats(items) for cat, items in by_category.items()},
    }


# ---------------------------------------------------------------------------
# Threshold check + report writer
# ---------------------------------------------------------------------------

def check_thresholds(metrics: dict) -> tuple[bool, list[str]]:
    """Return (passed, list_of_failure_strings) based on THRESHOLDS."""
    failures = []
    for key, threshold in THRESHOLDS.items():
        score = metrics["overall"].get(key, 0.0)
        if score < threshold:
            failures.append(f"{key}={score:.3f} < threshold={threshold}")
    return len(failures) == 0, failures


def write_report(results: list[dict], metrics: dict, report_dir: Path = _REPORTS_DIR) -> Path:
    """Write a timestamped JSON report to *report_dir* and return the path."""
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = report_dir / f"eval_{ts}.json"
    passed, failures = check_thresholds(metrics)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_questions": len(results),
        "thresholds": THRESHOLDS,
        "passed": passed,
        "threshold_failures": failures,
        "metrics": metrics,
        "results": results,
    }
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2)
    logger.info("Report written: %s  passed=%s", path, passed)
    return path


# ---------------------------------------------------------------------------
# Main eval orchestrator
# ---------------------------------------------------------------------------

async def run_eval(
    golden_path: Path = _GOLDEN_PATH,
    report_dir: Path = _REPORTS_DIR,
    user_id: str = "eval-runner",
    limit: int | None = None,
    runner=None,
) -> tuple[dict, Path]:
    """Run the full eval. runner defaults to engine.run_query.

    Args:
        golden_path: Path to golden_dataset.json.
        report_dir:  Directory for the timestamped JSON report.
        user_id:     Supabase user_id that owns the ingested documents.
        limit:       Cap number of questions (smoke-test shortcut).
        runner:      Callable(question, user_id) -> QueryResult.

    Returns:
        (metrics_dict, report_path)
    """
    from app.query.engine import run_query
    _runner = runner if runner is not None else run_query

    dataset = load_golden_dataset(golden_path)
    if limit is not None:
        dataset = dataset[:limit]

    logger.info("Starting eval: %d questions, user_id=%s", len(dataset), user_id)
    results: list[dict] = []

    for i, item in enumerate(dataset):
        logger.info("[%d/%d] %s — %s", i + 1, len(dataset), item["id"], item["question"][:60])
        try:
            record = await run_single(item, user_id, _runner)
        except Exception as exc:
            logger.error("Error on %s: %s", item["id"], exc)
            record = {
                "id": item["id"],
                "question": item["question"],
                "category": item["category"],
                "intent": item["intent"],
                "answer": "",
                "is_refusal": False,
                "contexts_count": 0,
                "retrieved_ids": [],
                "expected_ids": item.get("expected_source_item_ids", []),
                "faithfulness": 0.0,
                "answer_relevance": 0.0,
                "context_precision": 0.0,
                "context_recall": 0.0,
                "error": str(exc),
            }
        results.append(record)

    metrics = aggregate_metrics(results)
    path = write_report(results, metrics, report_dir)
    passed, failures = check_thresholds(metrics)

    if not passed:
        logger.warning("THRESHOLD FAILURES: %s", failures)

    return metrics, path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="RAGAS eval runner (vendored reference)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--user-id", default="eval-runner")
    parser.add_argument("--out", default=str(_REPORTS_DIR))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)

    metrics, path = asyncio.run(run_eval(
        report_dir=Path(args.out),
        user_id=args.user_id,
        limit=args.limit,
    ))

    overall = metrics["overall"]
    print(f"\n{'='*54}")
    print("  RAGAS Eval Results")
    print(f"{'='*54}")
    for key in ("faithfulness", "answer_relevance", "context_precision", "context_recall"):
        score = overall.get(key, 0.0)
        threshold = THRESHOLDS[key]
        status = "PASS" if score >= threshold else "FAIL"
        print(f"  {key:<22}  {score:.3f}   [{status}]  (min={threshold})")
    print(f"\n  Report: {path}\n")

    passed, _ = check_thresholds(metrics)
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
