"""The six-tier scorecard (guardrail verdict first, ▼ on regressions) and the baseline."""

import json

from src.evals.baseline import compare, load_baseline, save_baseline
from src.evals.report import render_table

METRICS = {
    "tier_g_pass_rate": 1.0,
    "recall_at_5": 0.93,
    "answer_key_coverage": 0.80,
    "tier_g_failures": [],
    "n_cases": 44,
    "per_tier": {
        "R": {"n": 9, "recall_at_5": 1.0, "answer_key_coverage": 0.9, "pass_rate": None},
        "G": {"n": 8, "recall_at_5": 0.88, "answer_key_coverage": 0.7, "pass_rate": 1.0},
    },
}


def test_the_table_leads_with_the_guardrail_verdict():
    # It is the metric that blocks a release on its own, so it reads first.
    table = render_table(METRICS)
    guardrail_pos = table.find("Guardrail verdict")
    recall_pos = table.find("Retrieval recall@5")
    assert 0 <= guardrail_pos < recall_pos


def test_scores_render_as_percentages():
    assert "93%" in render_table(METRICS)


def test_none_metric_renders_as_dash():
    assert "—" in render_table(dict(METRICS, answer_key_coverage=None))


def test_regression_marked_with_down_arrow():
    current = dict(METRICS, tier_g_pass_rate=0.80)
    table = render_table(current, baseline=dict(METRICS, tier_g_pass_rate=1.0))
    assert "▼" in table


def test_an_improvement_is_not_marked_as_a_regression():
    current = dict(METRICS, recall_at_5=0.99)
    table = render_table(current, baseline=dict(METRICS, recall_at_5=0.80))
    row = [ln for ln in table.splitlines() if "recall@5" in ln][0]
    assert "▼" not in row


def test_the_per_tier_breakdown_renders():
    # A headline rate hides which tier moved, and that is the first question
    # anyone asks of a regression.
    table = render_table(METRICS)
    assert "R · retrieval / single-hop" in table
    assert "G · guardrails and refusals" in table


def test_a_tier_with_no_cases_is_not_invented():
    table = render_table(METRICS)
    assert "T · temporal reasoning" not in table


def test_failing_guardrail_cases_are_named_not_counted():
    # A rate says how bad; the list says which, and the list is actionable.
    table = render_table(dict(METRICS, tier_g_failures=["E33", "E34"]))
    assert "E33" in table and "E34" in table


def test_no_failure_line_when_nothing_failed():
    assert "Tier G failures" not in render_table(METRICS)


def test_baseline_round_trip(tmp_path):
    path = tmp_path / "baseline.json"
    save_baseline(METRICS, run_id="run-123", path=path)
    loaded = load_baseline(path)
    assert loaded["run_id"] == "run-123"
    assert loaded["metrics"]["tier_g_pass_rate"] == 1.0
    assert json.loads(path.read_text())["run_id"] == "run-123"


def test_compare_yields_per_metric_deltas():
    baseline = dict(METRICS, recall_at_5=0.90)
    current = dict(METRICS, recall_at_5=0.95)
    deltas = compare(baseline, current)
    assert round(deltas["recall_at_5"], 2) == 0.05
