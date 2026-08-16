"""v4 phase 5 · Task 4 — every answer leaves a trace, whichever path answered.

Split from ``tests/test_console_agent.py``, which was already at the 300-line
rule. That file asks "did the endpoint answer correctly"; this one asks "is what
happened recorded".

The point of the phase in one line: **a keyword answer and a live answer produce
the same record shape**, distinguishable only by ``mode`` and ``model_id``. The
alternative — nullable fields plus a "was this a real answer?" guard inside every
metric — is how a dashboard starts lying, because the offline demo would produce
numbers the live path never would.

Latency comes from an **injected clock**. Rule 8 has no exception for
measurement: a test that cannot control the clock cannot assert a duration, and
a duration nobody asserts is a number nobody has checked.
"""

import json

from fastapi.testclient import TestClient

from src.traces.store import InMemoryTraceStore
from src.web.console.app import create_console_app

POLICY_NO = "LP-20419876"
CONFIRMED = ["policy_no", "name_dob", "address_or_bank"]

REPLY_JSON = json.dumps({
    "answer_text": "It was worth £151,240.00.",
    "citations": [{"chunk_id": "02-BOND:4.9"}],
    "abstained": False,
    "tools_used": [],
})


class _Blk:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Resp:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


class _Messages:
    def __init__(self, responses):
        self._responses = list(responses)

    def create(self, **kwargs):
        return self._responses.pop(0)


class _Client:
    def __init__(self, responses):
        self.messages = _Messages(responses)


def _text(body):
    return _Resp("end_turn", [_Blk(type="text", text=body)])


def _tool_use(name, args, id="tu_1"):
    return _Resp("tool_use", [_Blk(type="tool_use", name=name, input=args, id=id)])


class _Ticks:
    """A clock that advances a fixed amount each time it is read."""

    def __init__(self, step=0.25):
        self._t, self._step = 0.0, step

    def __call__(self):
        self._t += self._step
        return self._t


def _app(traces, **over):
    return create_console_app(secret="test-secret", traces=traces, **over)


def _live_app(traces, responses):
    return _app(traces, api_key="sk-ant-test", model="claude-sonnet-5",
                client_factory=lambda key: _Client(responses))


def _verified(app):
    c = TestClient(app)
    assert c.post("/api/login", json={"role": "front_office"}).status_code == 200
    cn_ref = c.post("/api/interaction/open",
                    json={"policy_no": POLICY_NO}).json()["cn_ref"]
    c.post("/api/verify", json={"cn_ref": cn_ref, "policy_no": POLICY_NO})
    r = c.post("/api/verify", json={"cn_ref": cn_ref, "policy_no": POLICY_NO,
                                    "confirmed": CONFIRMED})
    assert r.json()["outcome"] == "passed"
    return c, cn_ref


def _ask(client, cn_ref, message="what is their balance?"):
    return client.post("/api/agent", json={"policy_no": POLICY_NO,
                                           "cn_ref": cn_ref,
                                           "message": message}).json()


# ── the live path persists ─────────────────────────────────────────────

def test_a_live_answer_is_persisted_as_one_trace():
    traces = InMemoryTraceStore()
    app = _live_app(traces, [_tool_use("retrieve_clause", {"query": "withdrawal"}),
                             _text(REPLY_JSON)])
    c, cn_ref = _verified(app)
    _ask(c, cn_ref)
    assert len(traces.all()) == 1


def test_the_trace_names_the_model_that_answered():
    traces = InMemoryTraceStore()
    app = _live_app(traces, [_tool_use("retrieve_clause", {"query": "w"}),
                             _text(REPLY_JSON)])
    c, cn_ref = _verified(app)
    _ask(c, cn_ref)
    rec = traces.all()[0]
    assert rec.mode == "live"
    assert rec.model_id == "claude-sonnet-5"


def test_the_trace_belongs_to_the_interaction_it_was_asked_on():
    traces = InMemoryTraceStore()
    app = _live_app(traces, [_tool_use("retrieve_clause", {"query": "w"}),
                             _text(REPLY_JSON)])
    c, cn_ref = _verified(app)
    _ask(c, cn_ref)
    assert traces.query(cn_ref=cn_ref)[0].cn_ref == cn_ref


def test_the_trace_carries_the_citation_with_the_version_retrieval_read():
    # End to end: task 0 backfilled it, task 1 bridged it, task 4 stored it.
    traces = InMemoryTraceStore()
    app = _live_app(traces, [_tool_use("retrieve_clause", {"query": "withdrawal"}),
                             _text(REPLY_JSON)])
    c, cn_ref = _verified(app)
    _ask(c, cn_ref)
    cited = traces.all()[0].cited
    assert [(x.chunk_id, x.version) for x in cited] == [("02-BOND:4.9", 1)]


def test_the_role_that_asked_is_recorded():
    traces = InMemoryTraceStore()
    app = _live_app(traces, [_tool_use("retrieve_clause", {"query": "w"}),
                             _text(REPLY_JSON)])
    c, cn_ref = _verified(app)
    _ask(c, cn_ref)
    assert traces.all()[0].user_role == "front_office"


# ── latency, from an injected clock ────────────────────────────────────

def test_latency_is_measured_from_the_injected_clock():
    traces = InMemoryTraceStore()
    app = _app(traces, api_key="sk-ant-test", model="claude-sonnet-5",
               client_factory=lambda key: _Client(
                   [_tool_use("retrieve_clause", {"query": "w"}),
                    _text(REPLY_JSON)]),
               clock=_Ticks(step=0.25))
    c, cn_ref = _verified(app)
    _ask(c, cn_ref)
    # Two reads, 0.25s apart, in milliseconds — a real number, not a stub.
    assert traces.all()[0].latency_ms.generate == 250


# ── the keyword path produces the SAME shape ───────────────────────────

def test_a_keyword_answer_is_persisted_too():
    traces = InMemoryTraceStore()
    c, cn_ref = _verified(_app(traces))
    _ask(c, cn_ref)
    assert len(traces.all()) == 1


def test_the_keyword_trace_names_no_model():
    traces = InMemoryTraceStore()
    c, cn_ref = _verified(_app(traces))
    _ask(c, cn_ref)
    rec = traces.all()[0]
    assert rec.mode == "keyword"
    assert rec.model_id is None


def test_both_paths_produce_the_same_record_type():
    # The decision behind task 4: one shape, so the five metrics stay
    # pure folds and the offline demo cannot produce numbers the live path
    # never would.
    kw_store = InMemoryTraceStore()
    c, cn_ref = _verified(_app(kw_store))
    _ask(c, cn_ref)

    live_store = InMemoryTraceStore()
    app = _live_app(live_store, [_tool_use("retrieve_clause", {"query": "w"}),
                                 _text(REPLY_JSON)])
    c2, cn2 = _verified(app)
    _ask(c2, cn2)

    keyword, live = kw_store.all()[0], live_store.all()[0]
    assert type(keyword) is type(live)
    differing = {f for f in type(live).model_fields
                 if getattr(keyword, f) != getattr(live, f)}
    assert differing <= {"trace_id", "cn_ref", "ts", "mode", "model_id",
                         "answer_text", "cited", "retrieved", "latency_ms",
                         "abstained", "guardrail_events", "handoff"}


def test_the_keyword_path_answers_in_words_not_a_tool_dump():
    # It had no answer_text at all before this (D-CL-058), so there was
    # nothing to persist and nothing for the ops screen to show.
    traces = InMemoryTraceStore()
    c, cn_ref = _verified(_app(traces))
    _ask(c, cn_ref)
    assert traces.all()[0].answer_text.strip() != ""


def test_the_keyword_reply_reaches_the_client_as_well_as_the_store():
    traces = InMemoryTraceStore()
    c, cn_ref = _verified(_app(traces))
    out = _ask(c, cn_ref)
    assert out["reply"]["answer_text"].strip() != ""
    assert out["mode"] == "keyword"


# ── a question that names no policy still records ──────────────────────

def test_a_rules_question_with_no_policy_is_traced_without_an_interaction():
    # 07-RUNBOOK:4.1 keeps this path open and ungated. A trace that could not be
    # written here would leave the honest path unrecorded.
    traces = InMemoryTraceStore()
    c, _ = _verified(_app(traces))
    c.post("/api/agent", json={"message": "how does a claim work?"})
    assert len(traces.all()) == 1
    assert traces.all()[0].cn_ref is None


# ── retrieved[] is what evals read (phase 6 task 0) ────────────────────
#
# The route already had both facts and passed neither on: the loop builds the
# provenance map for the citation backfill, and the searcher returns its clauses
# in rank order. So every trace stored before this said `version: None` and
# `rank: None` for every chunk retrieval returned, and `recall@5` — which asks
# "was the expected chunk in the top five" — had no ranking to read.


def _retrieved_from_one_live_answer():
    traces = InMemoryTraceStore()
    app = _live_app(traces, [_tool_use("retrieve_clause", {"query": "withdrawal"}),
                             _text(REPLY_JSON)])
    c, cn_ref = _verified(app)
    _ask(c, cn_ref)
    return traces.all()[0].retrieved


def test_the_trace_says_which_version_each_retrieved_chunk_was_read_at():
    retrieved = _retrieved_from_one_live_answer()
    assert retrieved, "the live answer retrieved nothing — the fixture is wrong"
    assert all(r.version is not None for r in retrieved)


def test_the_trace_says_where_retrieval_placed_each_chunk():
    # Ranks are 1-based and consecutive from the top, in the searcher's own
    # order — that is the only thing recall@5 can be computed from.
    retrieved = _retrieved_from_one_live_answer()
    assert [r.rank for r in retrieved] == list(range(1, len(retrieved) + 1))


def test_the_trace_carries_the_score_retrieval_gave_each_chunk():
    retrieved = _retrieved_from_one_live_answer()
    assert all(isinstance(r.score, float) for r in retrieved)
