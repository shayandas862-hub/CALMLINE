"""The recorded baseline the release gate compares against.

A baseline file pins the per-metric scores and the cached-run id they came
from. `compare` yields per-metric deltas; the gate (Phase 8) fails a PR when a
protected metric drops below the baseline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

_NUMERIC = (int, float)


def save_baseline(metrics: dict[str, Any], *, run_id: str, path: Path | str) -> None:
    """Record the metrics and their source run-id."""
    path = Path(path)
    path.write_text(
        json.dumps({"run_id": run_id, "metrics": metrics}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_baseline(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare(baseline_metrics: dict[str, Any], current_metrics: dict[str, Any]) -> dict[str, float]:
    """Per-metric delta (current − baseline) for every numeric metric present in both."""
    deltas: dict[str, float] = {}
    for key, prior in baseline_metrics.items():
        current = current_metrics.get(key)
        if isinstance(prior, _NUMERIC) and isinstance(current, _NUMERIC):
            deltas[key] = current - prior
    return deltas
