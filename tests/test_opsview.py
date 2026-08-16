"""v4 phase 5 · Task 5 — the three lenses, rebuilt around whether the AI behaves.

The v3 screen answered "how is the queue doing". This one answers "is the AI
behaving", which is a different question with different failure modes. Two
lenses are replaced; **Operations survives**, because the queue and ledger
numbers were honest and the reconciliation self-check still earns its place
(D-CL-017 applies — this is the one v3 surface v4 deliberately replaces).

Every number folds over stored traces, gate events, the record book or the case
queue. Nothing is invented and nothing is averaged across models by accident:
**each lens names the model(s) behind its numbers and can be filtered to one**.
A screen that silently mixes two models breaks the fabricated-number rule by
averaging rather than by invention (D-CL-061).
"""

from src.casework.models import Case
from src.identity.events import GateEventLog
from src.opsview.lenses import (
    grounding_lens,
    operations_lens,
    ops_snapshot,
    safety_lens,
)
from src.records.seed import build_seed_book
from src.traces.schema import TraceRecord
from src.traces.store import InMemoryTraceStore

NOW = "2026-07-13T09:00:00"
CN = "CN-2026041201"
POLICY = "LP-20419876"
CURRENT = {"02-BOND:4.9": 4, "01-WOL:3.10": 1}


def _case(cid, policy_no=POLICY, *, priority="medium", status="pending_review",
          recommendation="proceed", checklist=None, sla_due=None, audit=None):
    return Case(
        case_id=cid, policy_no=policy_no, request="partial surrender",
        priority=priority, status=status, recommendation=recommendation,
        checklist=checklist or [], sla_due=sla_due, audit=audit or [],
    )


def _sample_cases():
    completed = _case(
        "CW-300218754", priority="high", status="completed",
        checklist=[{"requirement": "in force", "clause_ref": "WL-1.2",
                    "verdict": "pass"}],
        sla_due="2026-07-13T13:00:00",
        audit=[{"event": "approved", "at": NOW, "actor": "ops"},
               {"event": "committed_to_ledger", "at": NOW, "actor": "ops",
                "txn_id": "T1"}])
    overdue = _case("CW-300218755", policy_no="HB-40582213",
                    sla_due="2026-07-13T06:00:00")
    return [completed, overdue]


def _trace(trace_id="TR-1", *, model_id="claude-sonnet-5", mode="live", **over):
    kw = dict(trace_id=trace_id, cn_ref=CN, ts="2026-07-13T08:00:00",
              user_role="front_office", mode=mode, model_id=model_id)
    kw.update(over)
    return TraceRecord(**kw)


def _store(*records):
    store = InMemoryTraceStore()
    for r in records:
        store.append(r)
    return store


def _clean_gate_log():
    log = GateEventLog()
    log.record(kind="presented", policy_no=POLICY, actor="a", at="t1", cn_ref=CN)
    log.record(kind="passed", policy_no=POLICY, actor="a", at="t2", cn_ref=CN)
    log.record(kind="disclosure", policy_no=POLICY, actor="a", at="t3", cn_ref=CN)
    return log


# ── LENS 1 · safety & gates ────────────────────────────────────────────

def test_safety_reports_zero_bypasses_on_a_clean_flow():
    lens = safety_lens(_store(_trace()), _clean_gate_log())
    assert lens["gate_bypass"]["value"] == 0
    assert lens["gate_bypass"]["target"] == 0


def test_safety_detects_a_disclosure_with_nothing_behind_it():
    log = GateEventLog()
    log.record(kind="disclosure", policy_no=POLICY, actor="a", at="t1", cn_ref=CN)
    assert safety_lens(_store(_trace()), log)["gate_bypass"]["value"] == 1


def test_safety_shows_the_join_that_proves_the_zero():
    # A zero nobody can audit is a zero nobody should believe. The offending
    # events are listed, so 0 means "these were checked and none offended".
    lens = safety_lens(_store(_trace()), _clean_gate_log())
    assert lens["gate_bypass"]["events_examined"] == 3
    assert lens["gate_bypass"]["offenders"] == []


def test_safety_counts_advice_boundary_violations_separately():
    store = _store(_trace("TR-1", guardrail_events=["advice-boundary: told them"]),
                   _trace("TR-2", guardrail_events=["refusal: not verified"]))
    lens = safety_lens(store, _clean_gate_log())
    assert lens["advice_boundary"]["value"] == 1
    assert lens["advice_boundary"]["target"] == 0


def test_safety_groups_every_guardrail_event_by_type():
    store = _store(_trace("TR-1", guardrail_events=["refusal: a", "refusal: b"]),
                   _trace("TR-2", guardrail_events=["advice-boundary: c"]))
    by_type = safety_lens(store, _clean_gate_log())["guardrail_events_by_type"]
    assert by_type["refusal"] == 2
    assert by_type["advice-boundary"] == 1


def test_safety_shows_abstention_beside_routing():
    # Abstention is only good when the handoff was right — the two numbers are
    # meaningless apart, so the lens never shows one without the other.
    store = _store(
        _trace("TR-1", abstained={"flag": True, "reason": "not verified"},
               handoff="CW-300218754"),
        _trace("TR-2"))
    lens = safety_lens(store, _clean_gate_log())
    assert lens["abstention"]["value"] == 0.5
    assert lens["correct_routing"]["value"] == 1.0


# ── LENS 2 · grounding & freshness ─────────────────────────────────────

def test_grounding_counts_citations_by_style():
    store = _store(_trace("TR-1", cited=[{"chunk_id": "02-BOND:4.9", "version": 4}]))
    lens = grounding_lens(store, current_versions=CURRENT,
                          citation_styles={"02-BOND:4.9": "cite_source"},
                          kb_version="441", corpus_clauses=441)
    assert lens["citations_by_style"]["cite_source"] == 1


def test_grounding_reports_the_stale_rate():
    store = _store(_trace("TR-1", cited=[{"chunk_id": "02-BOND:4.9", "version": 3}]))
    lens = grounding_lens(store, current_versions=CURRENT, citation_styles={},
                          kb_version="441", corpus_clauses=441)
    assert lens["stale_citations"]["value"] == 1.0
    assert lens["stale_citations"]["target"] == 0


def test_grounding_says_no_data_rather_than_zero_when_nothing_was_cited():
    # The tile that would otherwise look perfect on an empty store.
    lens = grounding_lens(_store(), current_versions=CURRENT, citation_styles={},
                          kb_version="441", corpus_clauses=441)
    assert lens["stale_citations"]["value"] is None
    assert lens["stale_citations"]["basis"] == 0


def test_grounding_names_the_corpus_it_is_judging_against():
    lens = grounding_lens(_store(), current_versions=CURRENT, citation_styles={},
                          kb_version="441", corpus_clauses=441)
    assert lens["kb_version"] == "441"
    assert lens["corpus_clauses"] == 441


def test_grounding_reports_which_filters_retrieval_actually_applied():
    store = _store(_trace("TR-1", filters_applied={"aud": "front_office"}),
                   _trace("TR-2", filters_applied={}))
    lens = grounding_lens(store, current_versions=CURRENT, citation_styles={},
                          kb_version="441", corpus_clauses=441)
    assert lens["filter_hit_rate"]["value"] == 0.5


def test_every_tile_says_whether_it_is_a_count_or_a_rate():
    # Found on the rendered board: filter_hit_rate was hand-rolled as a dict
    # rather than built through Metric, so it carried no unit and a 0% share
    # rendered as a bare "0". Every tile goes through the same door now.
    store = _store(_trace("TR-1", cited=[{"chunk_id": "02-BOND:4.9", "version": 4}]))
    lens = grounding_lens(store, current_versions=CURRENT, citation_styles={},
                          kb_version="441", corpus_clauses=441)
    assert lens["stale_citations"]["unit"] == "rate"
    assert lens["filter_hit_rate"]["unit"] == "rate"
    safety = safety_lens(store, _clean_gate_log())
    assert safety["gate_bypass"]["unit"] == "count"
    assert safety["containment"]["unit"] == "rate"


# ── LENS 3 · operations, kept honest from v3 ───────────────────────────

def test_operations_still_reports_the_queue():
    lens = operations_lens(_sample_cases(), NOW, book=build_seed_book())
    assert lens["open"] == 1
    assert lens["completed"] == 1
    assert lens["overdue"] == 1


def test_operations_keeps_the_ledger_reconciliation_self_check():
    # Every balance recomputed from its own history. This survived the rebuild
    # because it is the one number that checks the store against itself.
    lens = operations_lens(_sample_cases(), NOW, book=build_seed_book())
    assert lens["ledgers_reconciled"] == lens["ledgers_total"]
    assert lens["ledgers_total"] > 0


# ── every lens names its model (D-CL-061) ──────────────────────────────

def test_a_lens_names_the_models_behind_its_numbers():
    store = _store(_trace("TR-1", model_id="claude-sonnet-5"),
                   _trace("TR-2", model_id="claude-haiku-4-5"))
    lens = safety_lens(store, _clean_gate_log())
    assert lens["models"] == ("claude-haiku-4-5", "claude-sonnet-5")
    assert lens["model_id"] is None


def test_a_lens_filtered_to_one_model_ignores_the_others_traces():
    store = _store(
        _trace("TR-1", model_id="claude-sonnet-5"),
        _trace("TR-2", model_id="claude-haiku-4-5",
               abstained={"flag": True, "reason": "not verified"}))
    lens = safety_lens(store, _clean_gate_log(), model_id="claude-haiku-4-5")
    assert lens["model_id"] == "claude-haiku-4-5"
    assert lens["abstention"]["value"] == 1.0


# ── the composed snapshot ──────────────────────────────────────────────

def test_the_snapshot_carries_all_three_lenses_and_the_clock():
    snap = ops_snapshot(build_seed_book(), _sample_cases(), NOW,
                        traces=_store(_trace()), gate_events=_clean_gate_log(),
                        corpus_clauses=441, kb_version="441",
                        current_versions=CURRENT, citation_styles={},
                        tool_names=["retrieve_clause"], mode="keyword")
    assert snap["now"] == NOW
    assert set(snap) >= {"safety", "grounding", "operations"}


def test_the_snapshot_can_be_filtered_to_one_model_throughout():
    snap = ops_snapshot(build_seed_book(), _sample_cases(), NOW,
                        traces=_store(_trace(model_id="claude-sonnet-5")),
                        gate_events=_clean_gate_log(), corpus_clauses=441,
                        kb_version="441", current_versions=CURRENT,
                        citation_styles={}, tool_names=[], mode="live",
                        model_id="claude-sonnet-5")
    assert snap["safety"]["model_id"] == "claude-sonnet-5"
    assert snap["grounding"]["model_id"] == "claude-sonnet-5"
