"""v4 phase 6 · Task 4 — the runner drives the console's own loop.

**The decision this task had to make, and made:** `loop.py` returns a
`CallVerdict`; `to_trace_record` reads a `ConsoleReply` and cannot bridge one.
Task 3 already scores Tier G "from ConsoleReply". So the runner uses
`console_loop.py`, which makes an eval run and a console answer **the same
shape by construction** — which is what "eval runs write the same trace shape"
was asking for (D-CL-084).

The **model** is stubbed, not the loop. A runner tested against a stubbed loop
proves the runner can call a function; stubbing only the client means the real
tool dispatch, the real grounding check and the real provenance backfill all run.

Every run carries `{eval_run_id, kb_version, per_case}` per `06-RAGOPS §3.0`.
Both are injected — rule 8 has no exception for eval bookkeeping, and a run id
taken from the clock is a run nobody can reproduce.
"""

import json

import pytest

from src.agent.tools.registry import Tool, ToolRegistry
from src.evals.runner import (console_answer, load_run, load_run_manifest,
                              run_over_golden, write_run)

TS = "2026-07-26T09:00:00"
MODEL = "claude-haiku-4-5"

CASE = {"id": "E01", "tier": "R", "question": "Grace period after a missed premium?",
        "answer_keys": ["30 days"], "expected_chunks": ["01-WOL:3.10"],
        "failure_watched": "wrong figure"}

REPLY_JSON = json.dumps({
    "answer_text": "Thirty days, and the claim is paid net of the premium.",
    "citations": [{"chunk_id": "01-WOL:3.10"}],
    "abstained": False,
    "tools_used": [],
})


# ── a stubbed model, a real loop ───────────────────────────────────────

class _Blk:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Resp:
    def __init__(self, stop_reason, content):
        self.stop_reason, self.content = stop_reason, content


class _Client:
    def __init__(self, responses):
        self.messages = type("M", (), {
            "create": lambda _self, **kw: responses.pop(0)})()


def _clause(chunk_id="01-WOL:3.10"):
    return {"chunk_id": chunk_id, "doc": "01-WOL", "clause_type": "rule",
            "text": "A premium is due within 30 days.", "aud": "all",
            "citation_style": "cite_source", "version": 1, "score": 0.94}


def _registry(fn=None):
    def retrieve_clause(query: str, product_code: str = "",
                        operative_date: str = "") -> dict:
        return {"found": True, "query": query, "product_code": product_code,
                "operative_date": operative_date, "clauses": [_clause()]}

    registry = ToolRegistry()
    registry.register(Tool(name="retrieve_clause", description="Look up a clause.",
                           fn=fn or retrieve_clause))
    return registry


def _answer(case=CASE, *, responses=None, registry=None, **over):
    kw = dict(client=_Client(responses if responses is not None else [
                  _Resp("tool_use", [_Blk(type="tool_use", name="retrieve_clause",
                                          input={"query": "grace period"}, id="tu_1")]),
                  _Resp("end_turn", [_Blk(type="text", text=REPLY_JSON)])]),
              registry=registry or _registry(), model=MODEL,
              audience="front_office", operative_date="2026-07-26",
              trace_id="EV-000001", ts=TS, kb_version="abc123def456")
    kw.update(over)
    return console_answer(case, **kw)


# ── what one case produces ─────────────────────────────────────────────

def test_a_case_produces_the_reply_the_console_would_have_produced():
    record = _answer()
    assert record["reply"]["answer_text"].startswith("Thirty days")


def test_the_record_carries_what_retrieval_returned_with_its_rank():
    # Straight from the trace, which is what recall@5 reads.
    retrieved = _answer()["retrieved"]
    assert [(r["chunk_id"], r["rank"]) for r in retrieved] == [("01-WOL:3.10", 1)]


def test_the_record_carries_the_version_retrieval_read():
    assert _answer()["retrieved"][0]["version"] == 1


def test_the_record_carries_the_score_retrieval_gave():
    assert _answer()["retrieved"][0]["score"] == pytest.approx(0.94)


def test_the_record_names_the_trace_it_came_from():
    # An eval result you cannot trace back to a run is a number with no receipt.
    assert _answer()["trace_id"] == "EV-000001"


def test_the_answer_keys_start_ungraded():
    # The judge fills these later, from cached output. An empty list is
    # "not yet graded", which the scorer reads as None rather than zero.
    assert _answer()["answer_keys"] == []


def test_a_case_with_its_own_operative_date_is_asked_at_that_date():
    seen = {}

    def spy(query: str, product_code: str = "", operative_date: str = "") -> dict:
        seen["operative_date"] = operative_date
        return {"found": True, "query": query, "product_code": product_code,
                "operative_date": operative_date, "clauses": [_clause()]}

    _answer({**CASE, "operative_date": "2026-07-13"}, registry=_registry(spy),
            responses=[
                _Resp("tool_use", [_Blk(type="tool_use", name="retrieve_clause",
                                        input={"query": "iht",
                                               "operative_date": "2026-07-13"},
                                        id="tu_1")]),
                _Resp("end_turn", [_Blk(type="text", text=REPLY_JSON)])])
    assert seen["operative_date"] == "2026-07-13"


# ── the fold over the set ──────────────────────────────────────────────

def test_every_case_gets_a_record_carrying_its_id_and_tier():
    records = run_over_golden([CASE], lambda case: {"reply": {}, "retrieved": []})
    assert records[0]["id"] == "E01" and records[0]["tier"] == "R"


def test_a_case_that_raises_is_recorded_as_an_error_never_dropped():
    # A dropped case quietly raises every rate computed over the set.
    def explode(case):
        raise RuntimeError("the agent fell over")

    records = run_over_golden([CASE], explode)
    assert len(records) == 1
    assert "the agent fell over" in records[0]["error"]
    assert records[0]["id"] == "E01"


def test_one_failing_case_does_not_stop_the_rest():
    cases = [CASE, {**CASE, "id": "E02"}]
    records = run_over_golden(
        cases, lambda case: (_ for _ in ()).throw(ValueError("x"))
        if case["id"] == "E01" else {"reply": {}, "retrieved": []})
    assert [r["id"] for r in records] == ["E01", "E02"]
    assert "error" in records[0] and "error" not in records[1]


# ── the cached run on disk ─────────────────────────────────────────────

def _write(tmp_path, records=None):
    run_dir = tmp_path / "runs" / "baseline"
    write_run(records if records is not None else [{"id": "E01", "tier": "R"}],
              run_dir, eval_run_id="ER-0001", kb_version="abc123def456",
              model_id=MODEL)
    return run_dir


def test_a_run_round_trips_through_disk(tmp_path):
    run_dir = _write(tmp_path, [{"id": "E01", "tier": "R", "reply": {}}])
    assert [r["id"] for r in load_run(run_dir)] == ["E01"]


def test_the_run_records_which_corpus_and_which_model_it_scored(tmp_path):
    # §3.0: a run without its kb_version cannot be compared with another one,
    # because nobody can say whether the corpus moved underneath it.
    manifest = load_run_manifest(_write(tmp_path))
    assert manifest["eval_run_id"] == "ER-0001"
    assert manifest["kb_version"] == "abc123def456"
    assert manifest["model_id"] == MODEL


def test_the_manifest_is_not_mistaken_for_a_case(tmp_path):
    # It sits in the same directory; the loader must not score it as a 45th case.
    assert len(load_run(_write(tmp_path))) == 1


def test_the_manifest_counts_the_cases_it_wrote(tmp_path):
    run_dir = _write(tmp_path, [{"id": "E01"}, {"id": "E02"}])
    assert load_run_manifest(run_dir)["n_cases"] == 2


def test_a_run_loads_in_a_stable_order(tmp_path):
    run_dir = _write(tmp_path, [{"id": "E44"}, {"id": "E01"}, {"id": "E12"}])
    assert [r["id"] for r in load_run(run_dir)] == ["E01", "E12", "E44"]
