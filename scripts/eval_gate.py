#!/usr/bin/env python3
"""The release gate — a safety regression cannot ship.

Re-scores a CACHED run against the recorded baseline and fails (non-zero exit,
naming the metric + delta) if any protected metric dropped. The guardrail
verdict is protected first. Zero live calls, zero spend — it scores committed
outputs only, so it runs in CI with no secrets.

    python scripts/eval_gate.py <run-id>
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.run_evals import GOLDEN_PATH, RUNS_DIR, score_cached_run  # noqa: E402
from src.evals.baseline import load_baseline  # noqa: E402

BASELINE_PATH = Path(__file__).resolve().parent.parent / "src" / "evals" / "baseline.json"

# Protected metrics — the guardrail verdict first. A drop in any blocks merge.
PROTECTED = ("tier_g_pass_rate", "recall_at_5", "answer_key_coverage")


def accepted_failures(baseline: dict[str, Any]) -> list[str]:
    """Tier G cases the recorded baseline already knows about.

    **The only way to accept a guardrail failure is to re-record
    `src/evals/baseline.json`** — a committed file, in a reviewable diff, from a
    real run. There is no flag, no allow-list constant and no environment
    variable, because each of those would let a failure be waved through in the
    same commit that caused it.
    """
    return sorted(baseline.get("tier_g_failures") or [])


def gate(
    baseline: dict[str, Any],
    current: dict[str, Any],
    protected: tuple[str, ...] = PROTECTED,
) -> tuple[bool, list[str]]:
    """Return (passed, failures). Three rules, in order of severity.

    1. **Any NEW Tier G failure blocks**, regardless of every other metric. This
       is absolute, not a comparison: it cannot be offset by a perfect scorecard
       elsewhere. A guardrail case that did not withhold is a failed run
       whatever the averages say.

       *New* means "not already in the recorded baseline". v4 phase 7 needed
       this: E34 fails on a blocked citation fabrication, the operator's
       instruction was to clear **or knowingly baseline** the known failures,
       and a gate that is red on every PR for ever is a gate people learn to
       merge past — so the day it goes red for a new reason, nobody looks.
       Rule 2 still holds the line underneath: `tier_g_pass_rate` is a protected
       metric, so a run where *more* guardrail cases fail is blocked anyway,
       even if every failure is named in the baseline.
    2. A protected headline metric below its baseline blocks.
    3. A **per-tier** regression blocks, because averages hide tiers. Temporal
       reasoning collapsing while cross-document improves can leave `recall@5`
       flat, and "no change" is the one thing that would not be true.
    """
    accepted = set(accepted_failures(baseline))
    failures = [
        f"Tier G FAILURE: {case_id} — a guardrail case that did not withhold. "
        "This blocks regardless of every other metric."
        for case_id in (current.get("tier_g_failures") or [])
        if case_id not in accepted
    ]
    failures.extend(_regressions(baseline, current, protected))
    failures.extend(_tier_regressions(baseline, current, protected))
    return (not failures, failures)


def _regressions(baseline: dict[str, Any], current: dict[str, Any],
                 protected: tuple[str, ...], prefix: str = "") -> list[str]:
    """Protected metrics that fell below their recorded baseline."""
    failures: list[str] = []
    for metric in protected:
        base = baseline.get(metric)
        if not isinstance(base, (int, float)):
            continue  # not baselined → not gated
        cur = current.get(metric)
        if not isinstance(cur, (int, float)):
            failures.append(f"{prefix}{metric}: missing in the current run")
            continue
        if cur < base:
            failures.append(
                f"{prefix}{metric}: {cur:.2f} < baseline {base:.2f} (Δ {cur - base:+.2f})")
    return failures


def _tier_regressions(baseline: dict[str, Any], current: dict[str, Any],
                      protected: tuple[str, ...]) -> list[str]:
    """The same comparison, tier by tier — a headline average hides a tier."""
    base_tiers = baseline.get("per_tier") or {}
    cur_tiers = current.get("per_tier") or {}
    failures: list[str] = []
    for tier in sorted(base_tiers):
        failures.extend(_regressions(base_tiers[tier], cur_tiers.get(tier, {}),
                                     protected, prefix=f"tier {tier} · "))
    return failures


def run_gate(
    golden_path: Path | str,
    run_dir: Path | str,
    baseline_path: Path | str,
) -> tuple[bool, list[str]]:
    """Score the cached run and gate it against the baseline file."""
    if not Path(baseline_path).exists():
        raise FileNotFoundError(f"no recorded baseline at {baseline_path} — cannot gate")
    baseline = load_baseline(baseline_path).get("metrics", {})
    current, _table = score_cached_run(golden_path, run_dir)
    return gate(baseline, current)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: eval_gate.py <run-id>", file=sys.stderr)
        return 2
    run_dir = RUNS_DIR / argv[1]
    try:
        passed, failures = run_gate(GOLDEN_PATH, run_dir, BASELINE_PATH)
        carried = accepted_failures(load_baseline(BASELINE_PATH).get("metrics", {}))
    except FileNotFoundError as exc:
        print(f"GATE ERROR: {exc}", file=sys.stderr)
        return 2
    # Printed on PASS as loudly as on FAIL. A gate that goes quiet about what it
    # is carrying is how the carrying becomes permanent.
    for case_id in carried:
        print(f"eval gate: CARRYING a known Tier G failure — {case_id}. "
              f"It does not block; a NEW one still does. Recorded in "
              f"{BASELINE_PATH.name}.")
    if passed:
        print("eval gate: PASS — no protected metric regressed"
              + (" and no new guardrail failure." if carried else "."))
        return 0
    print("eval gate: FAIL — protected metric(s) regressed:", file=sys.stderr)
    for failure in failures:
        print(f"  - {failure}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
