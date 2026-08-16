"""v4 phase 5 · Task 3 — the five KB metrics, as pure folds.

Each returns a ``Metric`` carrying its value, its target, how many records it
folded over, and which model's traces it describes. The **basis** matters: a
rate over nothing is not 0%, it is "no data", and a tile that shows 0% either
way is a tile that lies on its quietest day.

**Every metric takes a `model_id` filter — except gate-bypass, which cannot.**
An operator swaps models to compare them on the same questions (D-CL-061), so an
unsliced average over a mixed run describes no model that actually ran. But a
gate bypass happens *before* any model is reached: the identity gate runs at the
endpoint, and a disclosure without a verification is a property of the gate, not
of whatever answered afterwards. Accepting a `model_id` there and quietly
ignoring it would be a worse lie than not offering it.

Windowing is the store's job (`query(since=, until=)`), not each metric's. That
keeps these folds pure and keeps the clock in exactly one place.
"""

from src.identity.events import GateEventLog
from src.traces.metrics import (
    abstention_rate,
    advice_boundary_violations,
    containment,
    correct_routing_rate,
    gate_bypass_count,
    stale_citation_rate,
)
from src.traces.schema import TraceRecord

CN = "CN-2026041201"
POLICY = "HB-40582213"


def _rec(trace_id="TR-1", *, mode="live", model_id="claude-sonnet-5", **over):
    kw = dict(trace_id=trace_id, cn_ref=CN, ts="2026-04-12T10:00:00",
              user_role="front_office", mode=mode, model_id=model_id)
    kw.update(over)
    return TraceRecord(**kw)


def _abstains(trace_id, reason="not verified", handoff=None):
    return _rec(trace_id, abstained={"flag": True, "reason": reason},
                handoff=handoff)


# ── gate_bypass_count — the join, not a re-derivation ──────────────────

def test_a_clean_flow_reports_zero_bypasses():
    log = GateEventLog()
    log.record(kind="presented", policy_no=POLICY, actor="a", at="t1", cn_ref=CN)
    log.record(kind="passed", policy_no=POLICY, actor="a", at="t2", cn_ref=CN)
    log.record(kind="disclosure", policy_no=POLICY, actor="a", at="t3", cn_ref=CN)
    metric = gate_bypass_count(log)
    assert metric.value == 0
    assert metric.target == 0


def test_a_disclosure_with_no_verification_behind_it_is_counted():
    # The metric detects; it does not decorate.
    log = GateEventLog()
    log.record(kind="disclosure", policy_no=POLICY, actor="a", at="t1", cn_ref=CN)
    assert gate_bypass_count(log).value == 1


def test_a_pass_that_arrives_after_the_disclosure_is_still_a_bypass():
    # Tidy paperwork, written afterwards. src/identity already decides this;
    # the metric consults it rather than forming its own opinion.
    log = GateEventLog()
    log.record(kind="disclosure", policy_no=POLICY, actor="a", at="t1", cn_ref=CN)
    log.record(kind="passed", policy_no=POLICY, actor="a", at="t2", cn_ref=CN)
    assert gate_bypass_count(log).value == 1


def test_gate_bypass_names_no_model():
    # It runs before any model does. Attributing it to one would be a
    # fabricated attribution, which is the same sin as a fabricated number.
    log = GateEventLog()
    log.record(kind="disclosure", policy_no=POLICY, actor="a", at="t1", cn_ref=CN)
    assert gate_bypass_count(log).model_id is None


# ── advice_boundary_violations ─────────────────────────────────────────

def test_advice_boundary_violations_counts_only_that_guardrail():
    traces = [
        _rec("TR-1", guardrail_events=["advice-boundary: told them what to do"]),
        _rec("TR-2", guardrail_events=["refusal: no verification"]),
        _rec("TR-3", guardrail_events=[]),
    ]
    metric = advice_boundary_violations(traces)
    assert metric.value == 1
    assert metric.target == 0


def test_one_trace_breaching_twice_counts_twice():
    traces = [_rec("TR-1", guardrail_events=["advice-boundary: a",
                                             "advice-boundary: b"])]
    assert advice_boundary_violations(traces).value == 2


# ── stale_citation_rate — only possible because task 0 carries version ─

CURRENT = {"02-BOND:4.9": 4, "01-WOL:3.10": 1}


def test_a_citation_at_the_current_version_is_fresh():
    traces = [_rec("TR-1", cited=[{"chunk_id": "02-BOND:4.9", "version": 4}])]
    metric = stale_citation_rate(traces, current_versions=CURRENT)
    assert metric.value == 0.0
    assert metric.basis == 1


def test_a_citation_whose_chunk_was_re_embedded_is_stale():
    # The headline case: the chunk moved on, the answer did not.
    traces = [_rec("TR-1", cited=[{"chunk_id": "02-BOND:4.9", "version": 3}])]
    assert stale_citation_rate(traces, current_versions=CURRENT).value == 1.0


def test_a_tombstoned_chunk_is_stale_however_current_its_version():
    traces = [_rec("TR-1", cited=[{"chunk_id": "02-BOND:4.9", "version": 4}])]
    metric = stale_citation_rate(traces, current_versions=CURRENT,
                                 tombstoned={"02-BOND:4.9"})
    assert metric.value == 1.0


def test_a_citation_that_cannot_say_what_it_read_is_not_counted_as_fresh():
    # A null version means the loop never backfilled it. Fresh-by-default there
    # would report 0% stale on exactly the traces that lost their provenance.
    traces = [_rec("TR-1", cited=[{"chunk_id": "02-BOND:4.9"}])]
    assert stale_citation_rate(traces, current_versions=CURRENT).value == 1.0


def test_the_rate_is_over_citations_not_over_traces():
    traces = [_rec("TR-1", cited=[{"chunk_id": "02-BOND:4.9", "version": 3},
                                  {"chunk_id": "01-WOL:3.10", "version": 1}])]
    metric = stale_citation_rate(traces, current_versions=CURRENT)
    assert metric.value == 0.5 and metric.basis == 2


def test_no_citations_at_all_is_no_data_not_zero_percent():
    metric = stale_citation_rate([], current_versions=CURRENT)
    assert metric.basis == 0
    assert metric.value is None


# ── abstention and routing, which only mean anything together ──────────

def test_abstention_rate_is_the_share_of_answers_declined():
    traces = [_rec("TR-1"), _abstains("TR-2"), _rec("TR-3"), _rec("TR-4")]
    assert abstention_rate(traces).value == 0.25


def test_correct_routing_counts_abstentions_that_went_somewhere():
    # Abstention is only good when the handoff was right (07-RUNBOOK:8.5-8.6).
    traces = [_abstains("TR-1", handoff="CW-300218754"),
              _abstains("TR-2", handoff=None)]
    metric = correct_routing_rate(traces)
    assert metric.value == 0.5
    assert metric.basis == 2


def test_correct_routing_ignores_answers_that_did_not_abstain():
    traces = [_rec("TR-1"), _abstains("TR-2", handoff="CW-300218754")]
    assert correct_routing_rate(traces).basis == 1


# ── containment — tracked, never targeted (E43) ────────────────────────

def test_containment_carries_no_target_structurally():
    # E43 answers "should the AI aim to contain more contacts?" with a flat no.
    # The absence of a target is a fact about the metric, not a missing config.
    metric = containment([_rec("TR-1")])
    assert metric.target is None
    assert metric.tracked_never_targeted is True


def test_containment_is_the_share_that_needed_no_handoff():
    traces = [_rec("TR-1"), _abstains("TR-2", handoff="CW-300218754")]
    assert containment(traces).value == 0.5


# ── the model_id slice (D-CL-061) ──────────────────────────────────────

def test_a_metric_filtered_to_one_model_ignores_the_others_traces():
    traces = [_rec("TR-1", model_id="claude-sonnet-5"),
              _abstains("TR-2"),
              _rec("TR-3", model_id="claude-haiku-4-5"),
              _rec("TR-4", model_id="claude-haiku-4-5")]
    traces[1] = _rec("TR-2", model_id="claude-haiku-4-5",
                     abstained={"flag": True, "reason": "not verified"})
    metric = abstention_rate(traces, model_id="claude-haiku-4-5")
    assert metric.basis == 3
    assert metric.value == 1 / 3


def test_a_filtered_metric_says_which_model_it_describes():
    traces = [_rec("TR-1", model_id="claude-sonnet-5")]
    assert abstention_rate(traces, model_id="claude-sonnet-5").model_id \
        == "claude-sonnet-5"


def test_an_unfiltered_metric_over_two_models_says_so_rather_than_naming_one():
    # The averaging trap: a number describing neither model must not be
    # presented as though it described one.
    traces = [_rec("TR-1", model_id="claude-sonnet-5"),
              _rec("TR-2", model_id="claude-haiku-4-5")]
    metric = abstention_rate(traces)
    assert metric.model_id is None
    assert metric.models == ("claude-haiku-4-5", "claude-sonnet-5")


def test_the_keyword_path_shows_up_as_a_named_absence_not_a_model():
    traces = [_rec("TR-1", mode="keyword", model_id=None)]
    assert abstention_rate(traces).models == ()


# ── a metric says whether it is a count or a rate ──────────────────────
#
# Found by looking at the rendered board: `filter hit rate` showed "0" and
# `containment` showed "1", because a rate of 0.0 and a count of 0 are the same
# float and the renderer was guessing. A metric that cannot say what it is
# forces every consumer to re-derive it, and one of them will get it wrong.

def test_a_rate_says_it_is_a_rate():
    assert abstention_rate([_rec("TR-1")]).unit == "rate"
    assert containment([_rec("TR-1")]).unit == "rate"
    assert stale_citation_rate([], current_versions={}).unit == "rate"


def test_a_count_says_it_is_a_count():
    log = GateEventLog()
    log.record(kind="disclosure", policy_no=POLICY, actor="a", at="t1", cn_ref=CN)
    assert gate_bypass_count(log).unit == "count"
    assert advice_boundary_violations([_rec("TR-1")]).unit == "count"
