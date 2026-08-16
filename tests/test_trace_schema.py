"""v4 phase 5 · Task 1 — TraceRecord, the `06-RAGOPS:4.1` shape.

One record per agent query. The five metrics in ``src/traces/metrics.py`` are
pure folds over these, so what this type refuses to hold is as important as what
it holds: a field that can quietly be wrong is a dashboard that quietly lies.

Three fields have **no producer anywhere in the codebase** — ``resolved_intent``
(the KB points at a Doc 5 §20 intent taxonomy CalmLine never built),
``handoff`` beyond the case reference, and ``feedback``. They are nullable and
left null rather than given an invented source.

``user_role`` carries CalmLine's own role strings, not the KB's
[customer|agent|ops]: the repo wins on facts, and `front_office` /
`back_office` / `ops` are what the session actually holds.
"""

import pytest
from pydantic import ValidationError

from src.agent.reply import Citation, ConsoleReply
from src.agent.trace import DecisionTrace, to_trace_record
from src.traces.schema import TraceRecord

TS = "2026-04-12T10:30:00"
MODEL = "claude-haiku-4-5"  # the phase-6 model; new fixtures name no other


def _record(**over):
    kw = dict(
        trace_id="TR-0001",
        cn_ref="CN-2026041201",
        ts=TS,
        channel="console",
        user_role="front_office",
        answer_text="It was worth £84,000.00 as at 15 March.",
        mode="live",
        model_id="claude-sonnet-5",
    )
    kw.update(over)
    return TraceRecord(**kw)


# ── the shape ──────────────────────────────────────────────────────────

def test_a_record_carries_its_interaction():
    # cn_ref from the start, not retrofitted: AD-CL-037 scopes the conversation
    # to the interaction, so every trace belongs to one.
    assert _record().cn_ref == "CN-2026041201"


def test_retrieved_chunks_carry_their_version_score_and_rank():
    rec = _record(retrieved=[{"chunk_id": "02-BOND:4.9", "version": 4,
                              "score": 0.91, "rank": 1}])
    assert rec.retrieved[0].chunk_id == "02-BOND:4.9"
    assert rec.retrieved[0].version == 4
    assert rec.retrieved[0].rank == 1


def test_cited_chunks_carry_chunk_id_and_version():
    # This pair is what stale_citation_rate folds over. A cited chunk with no
    # version is a citation the freshness metric cannot judge.
    rec = _record(cited=[{"chunk_id": "02-BOND:4.9", "version": 4}])
    assert rec.cited[0].version == 4


def test_filters_applied_records_what_narrowed_the_search():
    rec = _record(filters_applied={"aud": "front_office", "doc": "02-BOND"})
    assert rec.filters_applied.aud == "front_office"


def test_latency_is_split_into_retrieve_and_generate():
    rec = _record(latency_ms={"retrieve": 12, "generate": 840})
    assert rec.latency_ms.retrieve == 12 and rec.latency_ms.generate == 840


def test_the_three_fields_with_no_producer_default_to_null():
    # Nullable and honest. Inventing a source for these would put a number on
    # the ops screen that nothing in the system actually measured.
    rec = _record()
    assert rec.resolved_intent is None
    assert rec.handoff is None
    assert rec.feedback is None


# ── mode and model_id, the D-CL-061 invariant ──────────────────────────

def test_mode_says_which_path_answered():
    assert _record(mode="keyword", model_id=None).mode == "keyword"


def test_an_unknown_mode_is_refused():
    with pytest.raises(ValidationError):
        _record(mode="offline")


def test_the_keyword_path_may_not_name_a_model():
    # CONTEXT.md is explicit: the keyword path names no model, because naming
    # one that never ran is the pretence the field exists to prevent. With two
    # models' traces in one store this is what keeps a model_id slice honest.
    with pytest.raises(ValidationError):
        _record(mode="keyword", model_id="claude-sonnet-5")


def test_the_live_path_must_name_its_model():
    # The mirror image: a live answer whose model is unrecorded cannot be
    # attributed, and every metric takes a model_id filter.
    with pytest.raises(ValidationError):
        _record(mode="live", model_id=None)


# ── abstention ─────────────────────────────────────────────────────────

def test_an_abstention_states_its_reason():
    rec = _record(abstained={"flag": True, "reason": "caller not verified"})
    assert rec.abstained.flag is True
    assert rec.abstained.reason == "caller not verified"


def test_an_abstention_without_a_reason_is_refused():
    # An unexplained abstention inflates abstention_rate with nothing behind it.
    with pytest.raises(ValidationError):
        _record(abstained={"flag": True})


def test_not_abstaining_is_the_default():
    assert _record().abstained.flag is False


# ── the constrained vocabularies ───────────────────────────────────────

def test_user_role_uses_calmlines_own_roles():
    assert _record(user_role="ops").user_role == "ops"


def test_a_role_the_console_cannot_issue_is_refused():
    with pytest.raises(ValidationError):
        _record(user_role="customer")


def test_handoff_accepts_the_reference_grammars():
    assert _record(handoff="CW-300218754").handoff == "CW-300218754"


def test_handoff_refuses_something_that_is_not_a_route():
    with pytest.raises(ValidationError):
        _record(handoff="escalated")


# ── the bridge: DecisionTrace + ConsoleReply -> TraceRecord ────────────
#
# Two inputs, not one (AD-CL-031 stands; only the signature changes). The trace
# holds what the agent DID — which tools ran, what they returned. The reply holds
# what it SAID — the answer, its citations, whether it abstained. Neither alone
# can build a record, and the fields belonging to neither (who asked, when, on
# which interaction, at what latency) are passed explicitly rather than grown
# onto DecisionTrace, which the eval path shares.

def _trace_and_reply():
    trace = DecisionTrace()
    trace.tool_call("retrieve_clause", {"query": "withdrawal"})
    trace.tool_result("retrieve_clause", "1 clause(s)", refs=["02-BOND:4.9"])
    reply = ConsoleReply(
        answer_text="A withdrawal that size needs back-office approval.",
        citations=[Citation(chunk_id="02-BOND:4.9",
                            citation_style="cite_source", version=4)],
        tools_used=["retrieve_clause"],
    )
    return trace, reply


def _bridged(**over):
    trace, reply = _trace_and_reply()
    kw = dict(trace_id="TR-0001", ts=TS, user_role="front_office",
              mode="live", model_id="claude-sonnet-5",
              cn_ref="CN-2026041201")
    kw.update(over)
    return to_trace_record(trace, reply, **kw)


def test_the_bridge_takes_the_answer_from_the_reply():
    assert _bridged().answer_text.startswith("A withdrawal that size")


def test_the_bridge_takes_cited_chunks_with_their_versions_from_the_reply():
    # The citations were themselves backfilled from retrieval in task 0, so the
    # version here is one retrieval read — not one the model remembered.
    cited = _bridged().cited
    assert [(c.chunk_id, c.version) for c in cited] == [("02-BOND:4.9", 4)]


def test_the_bridge_takes_what_retrieval_returned_from_the_trace():
    # The trace is the only record of which chunks came back, and the reply
    # cannot be trusted to say — that is the grounding argument again.
    assert [r.chunk_id for r in _bridged().retrieved] == ["02-BOND:4.9"]


def test_the_bridge_carries_an_abstention_and_its_reason():
    trace, _ = _trace_and_reply()
    reply = ConsoleReply(answer_text="I can't confirm that from the wordings.",
                         abstained=True, abstention_reason="caller not verified")
    rec = to_trace_record(trace, reply, trace_id="TR-2", ts=TS,
                          user_role="front_office", mode="live",
                          model_id="claude-sonnet-5")
    assert rec.abstained.flag is True
    assert rec.abstained.reason == "caller not verified"


def test_the_bridge_refuses_to_invent_a_model_for_the_keyword_path():
    # The schema invariant holds through the bridge too — it is not a way in.
    trace, reply = _trace_and_reply()
    with pytest.raises(ValidationError):
        to_trace_record(trace, reply, trace_id="TR-3", ts=TS,
                        user_role="front_office", mode="keyword",
                        model_id="claude-sonnet-5")


# ── retrieved[] answers the question evals ask (phase 6 task 0) ────────
#
# `RetrievedChunk` declares rank, score and version; until now the bridge wrote
# none of the three, so `recall@5` had no ranking to take a top five from and
# `retrieved[].version` was None on every stored trace.


def _ranked_trace():
    trace = DecisionTrace()
    trace.tool_call("retrieve_clause", {"query": "withdrawal"})
    trace.tool_result(
        "retrieve_clause", "2 clause(s)",
        refs=["02-BOND:4.9", "02-BOND:5"],
        ranked=[{"chunk_id": "02-BOND:4.9", "rank": 1, "score": 0.88},
                {"chunk_id": "02-BOND:5", "rank": 2, "score": 0.51}])
    return trace


def test_the_bridge_states_where_retrieval_placed_each_chunk():
    _, reply = _trace_and_reply()
    rec = to_trace_record(_ranked_trace(), reply, trace_id="TR-4", ts=TS,
                          user_role="front_office", mode="live",
                          model_id=MODEL)
    assert [(r.chunk_id, r.rank, r.score) for r in rec.retrieved] == [
        ("02-BOND:4.9", 1, 0.88), ("02-BOND:5", 2, 0.51)]


def test_the_bridge_states_the_version_retrieval_read_each_chunk_at():
    # `versions` is the provenance map the loop already builds for the citation
    # backfill. Given it, retrieved[] says which version was read.
    _, reply = _trace_and_reply()
    rec = to_trace_record(_ranked_trace(), reply, trace_id="TR-5", ts=TS,
                          user_role="front_office", mode="live", model_id=MODEL,
                          versions={"02-BOND:4.9": {"version": 4},
                                    "02-BOND:5": {"version": 2}})
    assert [(r.chunk_id, r.version) for r in rec.retrieved] == [
        ("02-BOND:4.9", 4), ("02-BOND:5", 2)]


def test_without_a_provenance_map_the_version_is_null_not_guessed():
    _, reply = _trace_and_reply()
    rec = to_trace_record(_ranked_trace(), reply, trace_id="TR-6", ts=TS,
                          user_role="front_office", mode="live", model_id=MODEL)
    assert [r.version for r in rec.retrieved] == [None, None]


def test_a_trace_with_no_ranking_still_lists_what_retrieval_returned():
    # The keyword path builds its trace without ranks. Its chunks are still
    # recorded — with a null rank, which is honest, rather than a made-up one.
    trace, reply = _trace_and_reply()
    rec = to_trace_record(trace, reply, trace_id="TR-7", ts=TS,
                          user_role="front_office", mode="keyword",
                          model_id=None)
    assert [(r.chunk_id, r.rank) for r in rec.retrieved] == [("02-BOND:4.9", None)]
