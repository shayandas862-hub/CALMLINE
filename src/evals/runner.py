# MIT License — Copyright (c) 2026 Shayan Das
# Skeleton adapted from the author's earlier original work
# (vendor/secondbrain/evals_runner.py): injectable runner + JSON run records.
"""Run the six-tier golden set through the console's own loop, and cache it.

**The runner drives `console_loop.py`, not `loop.py`** (D-CL-084). `loop.py`
returns a `CallVerdict`; `to_trace_record` reads a `ConsoleReply` and cannot
bridge one, and task 3 already scores Tier G from a `ConsoleReply`. Running the
console loop makes an eval run and a console answer **the same shape by
construction**, which is what "eval runs write the same trace shape" was asking
for — rather than a second pipeline that has to be kept in step by hand.

A case whose run raised is recorded as `{"error": …}` and **never dropped**: a
missing case quietly raises every rate computed over the set.

`write_run` / `load_run` persist a run for offline replay. The run's
`{eval_run_id, kb_version, model_id}` sit in a `_run.json` manifest beside the
per-case files (`06-RAGOPS §3.0`) — a run without its `kb_version` cannot be
compared with another, because nobody can say whether the corpus moved
underneath it. The manifest is prefixed so the case loader never scores it as
one more case.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional

from src.agent.console_loop import run_console_agent
from src.agent.trace import to_trace_record

AnswerFn = Callable[[dict[str, Any]], dict[str, Any]]

MANIFEST = "_run.json"


def console_answer(
    case: dict[str, Any],
    *,
    client: Any,
    registry: Any,
    model: str,
    audience: str,
    operative_date: str,
    trace_id: str,
    ts: str,
    kb_version: Optional[str] = None,
    user_role: str = "front_office",
) -> dict[str, Any]:
    """Run one case through the console loop and shape what the scorer reads.

    The case's own ``operative_date`` wins where it has one — E24 asks its
    question on a stated date, and answering it on today's would score the
    right answer to a different question.

    ``answer_keys`` comes back empty: the judge grades them separately, from
    cached output, and an empty list reads as *not yet graded* rather than as
    zero coverage.
    """
    result = run_console_agent(
        case["question"],
        client=client,
        registry=registry,
        model=model,
        operative_date=case.get("operative_date") or operative_date,
        audience=audience,
    )
    record = to_trace_record(
        result.trace, result.reply,
        trace_id=trace_id,
        ts=ts,
        user_role=user_role,
        mode="live",
        model_id=model,
        channel="eval",
        kb_version=kb_version,
        versions=result.retrieved,
    )
    return {
        "retrieved": [chunk.model_dump() for chunk in record.retrieved],
        "reply": result.reply.model_dump(),
        "trace_id": record.trace_id,
        "answer_keys": [],
    }


def run_over_golden(cases: list[dict[str, Any]], answer_fn: AnswerFn) -> list[dict[str, Any]]:
    """One record per case, in the given order. A case that raises is recorded."""
    records: list[dict[str, Any]] = []
    for case in cases:
        record = {"id": case["id"], "tier": case.get("tier")}
        try:
            record.update(answer_fn(case))
        except Exception as exc:  # a failed case is a failed case, recorded not dropped
            record["error"] = f"{type(exc).__name__}: {exc}"
        records.append(record)
    return records


def write_run(records: list[dict[str, Any]], run_dir: Path | str, *,
              eval_run_id: Optional[str] = None,
              kb_version: Optional[str] = None,
              model_id: Optional[str] = None) -> None:
    """Write each record to `<run_dir>/<id>.json`, plus the run manifest."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        path = run_dir / f"{record['id']}.json"
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {"eval_run_id": eval_run_id, "kb_version": kb_version,
                "model_id": model_id, "n_cases": len(records)}
    (run_dir / MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_run(run_dir: Path | str) -> list[dict[str, Any]]:
    """Load a cached run, ordered by id — deterministic, no agent involved."""
    run_dir = Path(run_dir)
    return [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(run_dir.glob("*.json"))
            if not path.name.startswith("_")]


def load_run_manifest(run_dir: Path | str) -> dict[str, Any]:
    """The run's `{eval_run_id, kb_version, model_id, n_cases}`, or empty if absent."""
    path = Path(run_dir) / MANIFEST
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
