"""v4 phase 4 · Task 6 — `/api/agent` wired to the real agent.

Phase 3 already gated this endpoint (D-CL-052) — the review found it disclosing a
balance to an unverified caller, because the agent's tools read the same book the
gated endpoints read. Those four behaviours are pinned next door in
`test_console_gate.py` and must survive this reshape; what is new here is the
live path behind the gate, and saying honestly which path answered.

The live path is driven by a **stubbed client** injected through
``client_factory``. Rule 10 says zero live API calls in the suite, and a live
path exercised only in production is a live path nobody has tested.
"""

import json

from fastapi.testclient import TestClient

from src.web.console.app import create_console_app

POLICY_NO = "LP-20419876"
CONFIRMED = ["policy_no", "name_dob", "address_or_bank"]

REPLY_JSON = json.dumps({
    "answer_text": "It was worth £46,210.00 on 12 April.",
    "citations": [{"chunk_id": "02-BOND:4.9",
                   "citation_style": "aldercrest_standard"}],
    "abstained": False,
})
ABSTAIN_JSON = json.dumps({
    "answer_text": "", "abstained": True,
    "abstention_reason": "the rules do not cover this",
})


# ── a stubbed Anthropic client ───────────────────────────────────────────
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
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class _Client:
    def __init__(self, responses):
        self.messages = _Messages(responses)


def _text(text):
    return _Resp("end_turn", [_Blk(type="text", text=text)])


RECORD_REPLY_JSON = json.dumps({
    # A ledger answer cites nothing — there is no clause behind a balance.
    "answer_text": "It was worth £46,210.00 on 12 April.", "citations": []})


def _retrieval(query="withdrawal"):
    """A retrieval step, so a cited answer has something real to cite."""
    return _tool_use("retrieve_clause", {"query": query})


def _tool_use(name, args, id="tu_1"):
    return _Resp("tool_use", [_Blk(type="tool_use", name=name, input=args, id=id)])


# ── app builders ─────────────────────────────────────────────────────────
def _app(**over):
    return create_console_app(secret="test-secret", **over)


def _live_app(responses):
    client = _Client(responses)
    app = _app(api_key="sk-ant-test", model="claude-sonnet-5",
               client_factory=lambda key: client)
    return app, client


def _verified(app):
    """A logged-in front-office session that has passed the gate."""
    c = TestClient(app)
    assert c.post("/api/login", json={"role": "front_office"}).status_code == 200
    cn_ref = c.post("/api/interaction/open",
                    json={"policy_no": POLICY_NO}).json()["cn_ref"]
    c.post("/api/verify", json={"cn_ref": cn_ref, "policy_no": POLICY_NO})
    r = c.post("/api/verify", json={"cn_ref": cn_ref, "policy_no": POLICY_NO,
                                    "confirmed": CONFIRMED})
    assert r.json()["outcome"] == "passed"
    return c, cn_ref


# ── the offline path says so ─────────────────────────────────────────────

def test_with_no_key_the_console_answers_offline_and_says_so():
    c, cn_ref = _verified(_app())
    out = c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                                     "message": "what is their balance?"}).json()
    assert out["mode"] == "keyword"
    assert "no anthropic api key" in out["reason"].lower()
    assert out["model"] is None


def test_the_offline_path_names_no_model_it_did_not_run():
    c, cn_ref = _verified(_app())
    out = c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                                     "message": "how do they claim?"}).json()
    assert out["model"] is None


def test_a_disclosure_still_reports_the_verification_that_unlocked_it():
    c, cn_ref = _verified(_app())
    out = c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                                     "message": "what is their balance?"}).json()
    assert out["verification_id"].startswith("VR-")
    assert out["cn_ref"] == cn_ref


def test_the_operative_date_defaults_to_the_consoles_injected_now():
    # Never the wall clock (rule 8).
    c, cn_ref = _verified(_app(now="2026-04-12T09:00:00"))
    out = c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                                     "message": "balance?"}).json()
    assert out["operative_date"] == "2026-04-12"


def test_an_operative_date_in_the_request_is_used_and_echoed():
    c, cn_ref = _verified(_app())
    out = c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                                     "message": "balance?",
                                     "operative_date": "2026-01-12"}).json()
    assert out["operative_date"] == "2026-01-12"


# ── the live path, behind the same gate ──────────────────────────────────

def test_a_key_selects_the_live_agent_and_it_is_reported():
    app, _ = _live_app([_retrieval(), _text(REPLY_JSON)])
    c, cn_ref = _verified(app)
    out = c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                                     "message": "what was it worth?"}).json()
    assert out["mode"] == "live"
    assert out["model"] == "claude-sonnet-5"
    assert out["reply"]["answer_text"].startswith("It was worth")


def test_the_live_reply_cites_the_style_the_corpus_states_not_the_models():
    # REPLY_JSON has the model claiming `aldercrest_standard` for 02-BOND:4.9.
    # The corpus says `cite_source` — the clause is real law, and labelling it an
    # Aldercrest operating standard is precisely the misattribution the
    # provenance rule exists to prevent.
    #
    # Until phase 5 this test asserted the model's value and passed, because the
    # model's string round-tripped. It proved the plumbing, not the citation.
    app, _ = _live_app([_retrieval(), _text(REPLY_JSON)])
    c, cn_ref = _verified(app)
    out = c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                                     "message": "what was it worth?"}).json()
    citation = out["reply"]["citations"][0]
    assert citation["chunk_id"] == "02-BOND:4.9"
    assert citation["citation_style"] == "cite_source"
    assert citation["version"] == 1


def test_the_live_path_is_still_428_without_a_verification():
    # The phase-3 gate runs before any of this.
    app, client = _live_app([_text(REPLY_JSON)])
    c = TestClient(app)
    c.post("/api/login", json={"role": "front_office"})
    r = c.post("/api/agent", json={"policy_no": POLICY_NO, "message": "balance?"})
    assert r.status_code == 428
    assert client.messages.calls == [], "the model must not be called on a refusal"


def test_the_live_path_gets_the_verification_scoped_tools():
    app, client = _live_app([_text(REPLY_JSON)])
    c, cn_ref = _verified(app)
    c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                               "message": "what was it worth?"})
    tools = {t["name"]: t for t in client.messages.calls[0]["tools"]}
    assert set(tools) == {"lookup_policy_record", "get_transaction_history",
                          "get_valuation", "retrieve_clause"}
    assert "verification_id" in tools["get_valuation"]["input_schema"]["properties"]
    assert "verification_id" not in tools["retrieve_clause"]["input_schema"]["properties"]


def test_the_operative_date_reaches_the_live_system_prompt():
    app, client = _live_app([_text(REPLY_JSON)])
    c, cn_ref = _verified(app)
    c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                               "message": "worth?", "operative_date": "2026-01-12"})
    assert "2026-01-12" in client.messages.calls[0]["system"]


def test_a_live_tool_call_runs_against_the_real_book():
    app, client = _live_app([
        _tool_use("get_valuation", {"policy_no": POLICY_NO, "as_at": "2026-04-12",
                                    "verification_id": "VR-000000001"}),
        _text(RECORD_REPLY_JSON),
    ])
    c, cn_ref = _verified(app)
    out = c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                                     "message": "what was it worth?"}).json()
    assert out["reply"]["tools_used"] == ["get_valuation"]
    fed_back = client.messages.calls[1]["messages"][-1]["content"][0]
    assert "46,210" in fed_back["content"]


def test_a_live_tool_call_with_a_bad_verification_id_is_refused():
    # Defence in depth: the endpoint let this request through, the tool does not.
    app, client = _live_app([
        _tool_use("get_valuation", {"policy_no": POLICY_NO, "as_at": "2026-04-12",
                                    "verification_id": "VR-999999999"}),
        _text(ABSTAIN_JSON),
    ])
    c, cn_ref = _verified(app)
    out = c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                                     "message": "what was it worth?"}).json()
    assert out["reply"]["abstained"] is True
    assert any("refused" in e for e in out["reply"]["guardrail_events"])
    fed_back = client.messages.calls[1]["messages"][-1]["content"][0]
    assert fed_back["is_error"] is True


def test_an_abstention_is_a_200_not_an_error():
    # Refusing correctly is the product working, so it is a success state.
    app, _ = _live_app([_text(ABSTAIN_JSON)])
    c, cn_ref = _verified(app)
    r = c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                                   "message": "what is the meaning of life?"})
    assert r.status_code == 200
    assert r.json()["reply"]["abstained"] is True


def test_the_trace_is_returned_for_the_live_path():
    # Returned, not persisted — persistence is phase 5.
    app, _ = _live_app([
        _tool_use("retrieve_clause", {"query": "withdrawal"}),
        _text(REPLY_JSON),
    ])
    c, cn_ref = _verified(app)
    out = c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                                     "message": "may they withdraw?"}).json()
    assert [s["kind"] for s in out["trace"]] == [
        "tool_call", "tool_result", "verdict"]


def test_a_rules_question_needs_no_verification_on_the_live_path_either():
    # 07-RUNBOOK:4.1 — general product information is permitted before verification.
    app, _ = _live_app([_text(REPLY_JSON)])
    c = TestClient(app)
    c.post("/api/login", json={"role": "front_office"})
    r = c.post("/api/agent", json={"message": "how does a bond withdrawal work?"})
    assert r.status_code == 200
    assert r.json()["mode"] == "live"


# ── found by the live smoke ──────────────────────────────────────────────

def test_an_agent_that_cannot_finish_abstains_rather_than_500ing():
    # The step limit fired through the console and surfaced as "Something went
    # wrong." A bad answer is not a broken server, and 500 is the opposite of
    # the stance that a refusal is the product working.
    app, _ = _live_app([_tool_use("retrieve_clause", {"query": "x"},
                                  id=f"tu_{i}") for i in range(12)])
    c, cn_ref = _verified(app)
    r = c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                                   "message": "go round in circles"})
    assert r.status_code == 200
    body = r.json()
    assert body["reply"]["abstained"] is True
    assert any("agent_error" in e for e in body["reply"]["guardrail_events"])


def test_no_ops_material_reaches_a_front_office_answer():
    # The done criterion, asserted against the CONSOLE's own wiring rather than
    # a retriever a test built with the right audience. app.py was binding no
    # audience at all, so ops chunks were in the index the agent searched.
    c, cn_ref = _verified(_app())
    out = c.post("/api/agent", json={
        "policy_no": POLICY_NO, "cn_ref": cn_ref,
        "message": "quality assurance sampling and ops escalation"}).json()
    clauses = (out.get("result") or {}).get("clauses") or []
    assert clauses, "expected the keyword path to retrieve something"
    assert all(c["aud"] in ("front_office", "all") for c in clauses)
