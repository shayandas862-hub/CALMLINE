"""Render the six-tier eval scorecard as an honest markdown table.

**The guardrail verdict leads**, because it is the one that blocks a release on
its own. Below it sit recall@5 and answer-key coverage, then the per-tier
breakdown — a headline rate hides which tier moved, and "which tier moved" is
the first question anyone asks of a regression.

When a prior baseline is supplied each metric shows its delta and a regression
is marked with ▼. The numbers are published as measured, drops included.

Every failing Tier G case is **named**, not counted. A rate says how bad; the
list says which, and the list is what somebody can act on.
"""

from __future__ import annotations

from typing import Any, Optional

# (metric key, display label) in publication order — the binary verdict first.
_ROWS = [
    ("tier_g_pass_rate", "Guardrail verdict (Tier G, binary)"),
    ("recall_at_5", "Retrieval recall@5"),
    ("answer_key_coverage", "Answer-key coverage (judge)"),
]

# `06-RAGOPS §3.0`'s tier names, in the order its tables run.
_TIER_LABELS = [
    ("R", "R · retrieval / single-hop"),
    ("M", "M · multi-hop reasoning"),
    ("X", "X · cross-document chains"),
    ("T", "T · temporal reasoning"),
    ("G", "G · guardrails and refusals"),
    ("O", "O · operational and process"),
]


def _pct(value: Optional[float]) -> str:
    return "—" if value is None else f"{value * 100:.0f}%"


def render_table(metrics: dict[str, Any], baseline: Optional[dict[str, Any]] = None) -> str:
    """Return the markdown scorecard, optionally with baseline deltas."""
    sections = [_headline(metrics, baseline), _per_tier(metrics)]
    failures = metrics.get("tier_g_failures") or []
    if failures:
        sections.append("**Tier G failures:** " + ", ".join(failures))
    n = metrics.get("n_cases")
    if n is not None:
        sections.append(f"_Scored over {n} golden cases._")
    return "\n\n".join(section for section in sections if section)


def _headline(metrics: dict[str, Any], baseline: Optional[dict[str, Any]]) -> str:
    lines = ["| Metric | Score |" + (" Δ vs baseline |" if baseline else ""),
             "|---|---|" + ("---|" if baseline else "")]
    for key, label in _ROWS:
        current = metrics.get(key)
        cells = [label, _pct(current)]
        if baseline is not None:
            cells.append(_delta(current, baseline.get(key)))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _delta(current: Optional[float], prior: Optional[float]) -> str:
    if current is None or prior is None:
        return "—"
    change = current - prior
    return f"{change * 100:+.0f}pp" + (" ▼" if change < 0 else "")


def _per_tier(metrics: dict[str, Any]) -> str:
    per_tier = metrics.get("per_tier") or {}
    if not per_tier:
        return ""
    lines = ["| Tier | Cases | recall@5 | Answer keys | Guardrail |",
             "|---|---|---|---|---|"]
    for tier, label in _TIER_LABELS:
        row = per_tier.get(tier)
        if row is None:
            continue
        lines.append(f"| {label} | {row['n']} | {_pct(row.get('recall_at_5'))} | "
                     f"{_pct(row.get('answer_key_coverage'))} | "
                     f"{_pct(row.get('pass_rate'))} |")
    return "\n".join(lines)
