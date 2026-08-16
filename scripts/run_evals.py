#!/usr/bin/env python3
"""Run or replay the CalmLine eval.

    python scripts/run_evals.py --replay <run-id>   # score a cached run, print the table (offline)
    python scripts/run_evals.py                      # LIVE run — needs ANTHROPIC_API_KEY

The `--replay` path is deterministic, offline and **free**: it scores committed
raw outputs against the frozen six-tier golden set and prints the tier table.
That is the path CI takes, which is why the gate needs no secrets.

`--replay` defaults to the run the baseline was recorded from, so the common
case is one word with no id to remember.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.evals.baseline import load_baseline, save_baseline  # noqa: E402
from src.evals.golden import load_golden_set  # noqa: E402
from src.evals.report import render_table  # noqa: E402
from src.evals.runner import load_run  # noqa: E402
from src.evals.scoring import score  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = ROOT / "data" / "golden" / "golden_evals.jsonl"
RUNS_DIR = ROOT / "data" / "cached_runs"
BASELINE_PATH = ROOT / "src" / "evals" / "baseline.json"
DEFAULT_RUN = "baseline"


def score_cached_run(
    golden_path: Path | str,
    run_dir: Path | str,
    baseline_path: Optional[Path | str] = None,
) -> tuple[dict[str, Any], str]:
    """Score a cached run against the golden set; return (metrics, markdown table)."""
    cases = load_golden_set(golden_path)
    records = load_run(run_dir)
    metrics = score(cases, records)
    baseline = None
    if baseline_path and Path(baseline_path).exists():
        baseline = load_baseline(baseline_path).get("metrics")
    return metrics, render_table(metrics, baseline=baseline)


def live_run(*, run_id: str, model: str, ts: str, operative_date: str,
             record_baseline: bool = False,
             resume: bool = False) -> tuple[dict[str, Any], str]:
    """Run every golden case through the agent, cache it, score it. SPENDS MONEY.

    The order matters: the model is asserted and the key demanded **before** the
    first call, so a misconfigured run costs nothing rather than costing a run
    that then has to be thrown away.
    """
    from src.evals.answer_keys import grade_run
    from src.evals.freeze import verify_frozen
    from src.evals.live import (TokenMeter, anthropic_client, eval_registry,
                                metered, require_key, resolve_model, trace_ids)
    from src.evals.runner import console_answer, run_over_golden, write_run
    from src.corpus.facts import corpus_facts
    from src.web.console.offline_agent import searchable_chunks

    resolved = resolve_model(model)
    key = require_key()
    cases = load_golden_set(GOLDEN_PATH)
    verify_frozen(GOLDEN_PATH)  # score the set that was frozen, or none at all
    kb_version = corpus_facts(searchable_chunks())["kb_version"]

    meter = TokenMeter()
    client = metered(anthropic_client(key), meter)
    registry = eval_registry()
    make_id = trace_ids(run_id)
    order = {case["id"]: index for index, case in enumerate(cases, start=1)}

    print(f"LIVE · {len(cases)} cases · model {resolved} · kb {kb_version}",
          file=sys.stderr)

    def answer(case: dict[str, Any]) -> dict[str, Any]:
        print(f"  {case['id']} ({case['tier']}) …", file=sys.stderr, flush=True)
        return console_answer(
            case, client=client, registry=registry, model=resolved,
            audience="front_office", operative_date=operative_date,
            trace_id=make_id(order[case["id"]]), ts=ts, kb_version=kb_version)

    run_dir = RUNS_DIR / run_id
    records = load_run(run_dir) if resume and run_dir.exists() else None
    if records:
        print(f"  resuming: {len(records)} cached answers, no agent calls",
              file=sys.stderr)
    else:
        records = run_over_golden(cases, answer)
        # Cached BEFORE grading, always. The agent half is the expensive half,
        # and the first live run lost all 44 of its answers to a judge error
        # that happened after them (D-CL-097). Spend is never thrown away for a
        # failure in a later stage.
        write_run(records, run_dir, eval_run_id=run_id, kb_version=kb_version,
                  model_id=resolved)

    print("  grading answer keys …", file=sys.stderr, flush=True)
    records = grade_run(cases, records, client=client, model=resolved)
    write_run(records, run_dir, eval_run_id=run_id, kb_version=kb_version,
              model_id=resolved)

    spend = meter.totals()
    print(f"  spent: {spend['calls']} calls · {spend['input_tokens']:,} in / "
          f"{spend['output_tokens']:,} out tokens", file=sys.stderr)

    metrics = score(cases, records)
    metrics["_spend"] = spend
    if record_baseline:
        save_baseline(metrics, run_id=run_id, path=BASELINE_PATH)
    return metrics, render_table(metrics)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run or replay the CalmLine eval.")
    parser.add_argument("--replay", metavar="RUN_ID", nargs="?", const=DEFAULT_RUN,
                        help="score a cached run offline (default: the baseline run)")
    parser.add_argument("--cached", metavar="RUN_ID", help=argparse.SUPPRESS)
    parser.add_argument("--live", action="store_true",
                        help="RUN THE AGENT FOR REAL — spends against ANTHROPIC_API_KEY")
    parser.add_argument("--run-id", default=DEFAULT_RUN, help="name for the cached run")
    parser.add_argument("--model", default="",
                        help="the model this run is pinned to — REQUIRED for --live")
    parser.add_argument("--ts", default="", help="the timestamp stamped on every trace")
    parser.add_argument("--operative-date", default="",
                        help="the date answers are given as at (rule 8: never a clock)")
    parser.add_argument("--record-baseline", action="store_true",
                        help="write src/evals/baseline.json from this run — arms the gate")
    parser.add_argument("--resume", action="store_true",
                        help="reuse cached answers if the run exists; grade only")
    args = parser.parse_args(argv[1:])

    if args.live:
        if not args.ts or not args.operative_date:
            print("--live requires --ts and --operative-date: nothing here reads "
                  "the clock (rule 8).", file=sys.stderr)
            return 2
        try:
            _, table = live_run(run_id=args.run_id, model=args.model, ts=args.ts,
                                operative_date=args.operative_date,
                                record_baseline=args.record_baseline,
                                resume=args.resume)
        except Exception as exc:
            print(f"LIVE RUN REFUSED: {exc}", file=sys.stderr)
            return 2
        print(table)
        return 0

    run_id = args.replay or args.cached
    if run_id:
        run_dir = RUNS_DIR / run_id
        if not run_dir.exists():
            print(f"no cached run at {run_dir}", file=sys.stderr)
            return 1
        _, table = score_cached_run(GOLDEN_PATH, run_dir, BASELINE_PATH)
        print(table)
        return 0

    print(
        "LIVE eval spends real money: `--live --ts <iso> --operative-date <iso>`, "
        "and it needs ANTHROPIC_API_KEY. Use `--replay <run-id>` to score "
        "committed outputs offline and free.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
