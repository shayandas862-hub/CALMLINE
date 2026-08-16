"""v4 phase 6 · Task 7 — the wiring of the run that spends money, checked offline.

Task 7 is the one point in this phase where real calls are made. Everything
about *how* that run is set up is testable without making any, and the two
choices that would silently corrupt the numbers are the ones tested hardest:

  * the registry holds retrieval and nothing else, because a refused record tool
    appends a guardrail event and Tier G passes on a guardrail event — the full
    registry would have made every guardrail case pass for a reason unrelated to
    guardrails;
  * the model is asserted before a single call, because a run that quietly used
    a different model records a baseline describing a model that never ran.
"""

import pytest

from src.evals.live import (AUDIENCE, EVAL_TOP_K, LiveRunRefused, eval_registry,
                            require_key, resolve_model, trace_ids)

HAIKU = "claude-haiku-4-5"


# ── the model is asserted, not assumed ─────────────────────────────────

def test_the_intended_model_is_accepted():
    assert resolve_model(HAIKU, env={"ANTHROPIC_MODEL": HAIKU}) == HAIKU


def test_a_different_model_in_the_environment_refuses_the_run():
    # The failure this prevents: spending on one model and recording a baseline
    # that names another.
    with pytest.raises(LiveRunRefused) as exc:
        resolve_model(HAIKU, env={"ANTHROPIC_MODEL": "claude-sonnet-5"})
    assert HAIKU in str(exc.value) and "claude-sonnet-5" in str(exc.value)


def test_no_model_at_all_refuses_the_run():
    with pytest.raises(LiveRunRefused):
        resolve_model(HAIKU, env={})


def test_a_run_with_no_stated_pin_is_refused():
    # Stating the model out loud is the guard. Defaulting the pin to whatever
    # the environment says would make the check agree with itself.
    with pytest.raises(LiveRunRefused) as exc:
        resolve_model("", env={"ANTHROPIC_MODEL": HAIKU})
    assert "--model" in str(exc.value)


# ── the key fails loudly (rule 14) ─────────────────────────────────────

def test_a_missing_key_names_itself_and_points_at_the_free_path():
    with pytest.raises(LiveRunRefused) as exc:
        require_key(env={})
    assert "ANTHROPIC_API_KEY" in str(exc.value) and "--replay" in str(exc.value)


def test_an_empty_key_is_missing_not_present():
    # `ANTHROPIC_API_KEY= python …` is how this repo runs offline (D-CL-070).
    with pytest.raises(LiveRunRefused):
        require_key(env={"ANTHROPIC_API_KEY": "   "})


def test_a_real_key_is_returned():
    assert require_key(env={"ANTHROPIC_API_KEY": "sk-ant-test"}) == "sk-ant-test"


# ── the registry a golden case may use ─────────────────────────────────

def test_retrieval_is_the_only_tool_an_eval_case_gets():
    # A record tool would refuse (no verification exists in an eval run), a
    # refusal appends a guardrail event, and Tier G passes on a guardrail
    # event. The full registry would score every guardrail case as a pass.
    assert eval_registry().names() == ["retrieve_clause"]


def test_the_retrieval_tool_actually_returns_kb_clauses():
    result = eval_registry().dispatch(
        "retrieve_clause", {"query": "grace period missed premium"})
    assert result["found"] is True
    assert result["clauses"], "the eval retriever returned nothing from the KB"


def test_retrieval_returns_five_so_recall_at_five_can_be_computed():
    # A retriever capped at three cannot answer "was it in the top five" — it
    # can only answer recall@3, under a name that says otherwise.
    assert EVAL_TOP_K == 5
    result = eval_registry().dispatch("retrieve_clause", {"query": "pension"})
    assert len(result["clauses"]) <= EVAL_TOP_K


def test_every_returned_clause_carries_what_the_trace_needs():
    clause = eval_registry().dispatch(
        "retrieve_clause", {"query": "grace period"})["clauses"][0]
    for field in ("chunk_id", "version", "citation_style", "score"):
        assert field in clause, f"retrieval dropped {field}"


def test_the_eval_retriever_is_not_scoped_to_one_audience():
    # The eval asks "can retrieval find the governing clause in the corpus";
    # the console asks "may this handler see it". Binding the eval to
    # front_office makes 26 of the 44 cases unanswerable by construction —
    # Tier O expects ops runbook material — so the number would measure the
    # audience filter rather than the ranker (D-CL-098).
    assert AUDIENCE is None


def test_ops_material_a_front_office_session_could_not_see_is_retrievable_here():
    # 07-RUNBOOK:7.1 is aud=ops and is E27's expected chunk.
    found = eval_registry().dispatch(
        "retrieve_clause", {"query": "critical fail quality assessment"})["clauses"]
    assert any(c["chunk_id"].startswith("07-RUNBOOK") for c in found)


def test_the_audience_is_still_a_build_time_decision_not_a_query_one():
    # Rule 11 is untouched: a caller may narrow the retriever when building it,
    # and a query can never widen whatever it was built with.
    scoped = eval_registry(aud="front_office").dispatch(
        "retrieve_clause", {"query": "critical fail quality assessment"})["clauses"]
    assert all(c["aud"] in ("front_office", "all") for c in scoped)


# ── ids come from position, never a clock ──────────────────────────────

def test_trace_ids_are_derived_from_position():
    make = trace_ids("ER-0001")
    assert make(1) == "ER-0001-001" and make(44) == "ER-0001-044"


def test_the_same_run_id_yields_the_same_trace_ids():
    assert trace_ids("ER-0001")(7) == trace_ids("ER-0001")(7)


# ── what the run actually cost ─────────────────────────────────────────

def test_the_meter_starts_at_zero():
    from src.evals.live import TokenMeter
    assert TokenMeter().totals() == {"input_tokens": 0, "output_tokens": 0, "calls": 0}


def test_the_meter_accumulates_usage_across_calls():
    from src.evals.live import TokenMeter, metered

    class _Usage:
        def __init__(self, i, o):
            self.input_tokens, self.output_tokens = i, o

    class _Resp:
        def __init__(self, i, o):
            self.usage = _Usage(i, o)

    class _Client:
        def __init__(self):
            outer = self

            class _M:
                def create(self, **kw):
                    return _Resp(1000, 200)
            self.messages = _M()

    meter = TokenMeter()
    client = metered(_Client(), meter)
    client.messages.create(model="claude-haiku-4-5")
    client.messages.create(model="claude-haiku-4-5")
    assert meter.totals() == {"input_tokens": 2000, "output_tokens": 400, "calls": 2}


def test_a_response_without_usage_does_not_break_the_run():
    # A stub or an SDK change must not take the run down over bookkeeping.
    from src.evals.live import TokenMeter, metered

    class _Client:
        def __init__(self):
            class _M:
                def create(self, **kw):
                    return object()
            self.messages = _M()

    meter = TokenMeter()
    metered(_Client(), meter).messages.create()
    assert meter.totals()["calls"] == 1
    assert meter.totals()["input_tokens"] == 0


def test_the_meter_prices_a_run_at_the_models_published_rates():
    from src.evals.live import TokenMeter
    meter = TokenMeter()
    meter.record(1_000_000, 100_000)
    # claude-haiku-4-5: $1.00 per MTok in, $5.00 per MTok out.
    assert meter.cost_usd(input_per_mtok=1.0, output_per_mtok=5.0) == pytest.approx(1.50)
