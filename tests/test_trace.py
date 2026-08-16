"""The decision trace records each step in order for the audit log."""

from src.agent.trace import DecisionTrace


def test_records_steps_in_order():
    t = DecisionTrace()
    t.tool_call("policy_lookup", {"query": "grace period"})
    t.tool_result("policy_lookup", "3 clauses, top TL-4.2")
    t.verdict("ANSWER TL-4.2")
    kinds = [s["kind"] for s in t.as_list()]
    assert kinds == ["tool_call", "tool_result", "verdict"]


def test_tool_call_captures_name_and_args():
    t = DecisionTrace()
    t.tool_call("policy_lookup", {"query": "x"})
    step = t.as_list()[0]
    assert step["tool"] == "policy_lookup" and step["args"] == {"query": "x"}


def test_tool_result_captures_the_retrieved_refs():
    # the refs are what lets the scorer verify a citation was actually retrieved (R6)
    t = DecisionTrace()
    t.tool_result("policy_lookup", "2 clauses", refs=["TL-4.2", "TL-1.1"])
    step = t.as_list()[0]
    assert step["refs"] == ["TL-4.2", "TL-1.1"]


def test_as_list_is_a_copy():
    t = DecisionTrace()
    t.verdict("v")
    snapshot = t.as_list()
    t.verdict("v2")
    assert len(snapshot) == 1  # earlier snapshot not mutated


# ── where retrieval placed each chunk (phase 6 task 0) ─────────────────
#
# `recall@5` asks "was the expected chunk in the top five retrieval returned".
# That needs a RANKING, and `retrieved_refs()` is not one: it merges the ids
# from every tool call into a single insertion-ordered set. So the rank is
# recorded per retrieval call, in the order the searcher returned them.


def test_refs_stay_a_plain_list_of_ids_when_a_ranking_is_recorded():
    # The ranking is ADDITIVE. `refs` is read by the eval scorer and pinned by
    # four other tests; changing its shape would break both.
    t = DecisionTrace()
    t.tool_result("retrieve_clause", "2 clause(s)",
                  refs=["TL-4.2", "TL-1.1"],
                  ranked=[{"chunk_id": "TL-4.2", "rank": 1, "score": 0.91},
                          {"chunk_id": "TL-1.1", "rank": 2, "score": 0.62}])
    assert t.as_list()[0]["refs"] == ["TL-4.2", "TL-1.1"]


def test_retrieved_ranked_reports_where_retrieval_placed_each_chunk():
    t = DecisionTrace()
    t.tool_result("retrieve_clause", "2 clause(s)",
                  refs=["TL-4.2", "TL-1.1"],
                  ranked=[{"chunk_id": "TL-4.2", "rank": 1, "score": 0.91},
                          {"chunk_id": "TL-1.1", "rank": 2, "score": 0.62}])
    assert t.retrieved_ranked() == [
        {"chunk_id": "TL-4.2", "rank": 1, "score": 0.91},
        {"chunk_id": "TL-1.1", "rank": 2, "score": 0.62},
    ]


def test_a_chunk_returned_by_two_calls_keeps_the_best_rank_it_earned():
    # Retrieval found it in the top five if ANY call put it there. Keeping the
    # last call's rank would report a miss for a chunk that was found, and
    # keeping the first would report one for a chunk a later query found better.
    t = DecisionTrace()
    t.tool_result("retrieve_clause", "1 clause(s)", refs=["TL-1.1"],
                  ranked=[{"chunk_id": "TL-1.1", "rank": 7, "score": 0.3}])
    t.tool_result("retrieve_clause", "1 clause(s)", refs=["TL-1.1"],
                  ranked=[{"chunk_id": "TL-1.1", "rank": 2, "score": 0.8}])
    assert t.retrieved_ranked() == [{"chunk_id": "TL-1.1", "rank": 2, "score": 0.8}]


def test_a_tool_that_does_not_retrieve_contributes_no_ranking():
    # A valuation has no clauses and therefore no rank — different from a
    # retrieval that ranked nothing.
    t = DecisionTrace()
    t.tool_result("get_valuation", "found")
    assert t.retrieved_ranked() == []


def test_retrieved_refs_is_unchanged_by_the_ranking():
    t = DecisionTrace()
    t.tool_result("retrieve_clause", "1 clause(s)", refs=["TL-4.2"],
                  ranked=[{"chunk_id": "TL-4.2", "rank": 1, "score": 0.9}])
    assert t.retrieved_refs() == ["TL-4.2"]
