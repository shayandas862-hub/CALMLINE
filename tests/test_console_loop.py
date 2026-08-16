"""v4 phase 4 · Task 4 — the console's loop, Anthropic MOCKED.

Split from ``tests/test_loop.py`` when it passed the 300-line rule, mirroring
the split of ``console_loop.py`` from ``loop.py``. The eval harness's loop is
tested next door; this file drives ``run_console_agent``, which dispatches
whatever the registry holds and returns a ``ConsoleReply``.

No live API calls. The fakes stand in for the SDK response objects, and the
tests drive the model's decisions.
"""

import json

import pytest

from src.agent.console_loop import run_console_agent
from src.agent.loop import AgentError
from src.agent.tools.registry import Tool, ToolRegistry
from src.agent.tools.verification import VerificationRequired


# ── fakes for the Anthropic SDK surface ────────────────────────────────
class Blk:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def tool_use_block(name="retrieve_clause", args=None, id="tu_1"):
    return Blk(type="tool_use", name=name, input=args or {"query": "x"}, id=id)


def text_block(text):
    return Blk(type="text", text=text)


class Resp:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


class FakeMessages:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        nxt = self._responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)

OPERATIVE_DATE = "2026-04-12"
MODEL = "claude-sonnet-5"

CONSOLE_ANSWER = json.dumps({
    "answer_text": "It was worth £46,210.00; a £40,000 withdrawal needs approval.",
    "citations": [{"chunk_id": "02-BOND:4.9",
                   "citation_style": "aldercrest_standard"}],
    "abstained": False,
    "tools_used": ["a tool it never called"],
})
CONSOLE_ABSTAIN = json.dumps({
    "answer_text": "", "abstained": True,
    "abstention_reason": "the caller is not verified for this policy",
})


def _valuation(*, policy_no: str, as_at: str) -> dict:
    return {"found": True, "policy_no": policy_no, "as_at": as_at,
            "value_pence": 4621000, "value": "£46,210.00"}


def _retrieve(*, query: str) -> dict:
    return {"found": True, "query": query, "clauses": [
        {"chunk_id": "02-BOND:4.9", "citation_style": "aldercrest_standard"}]}


def _refuses(*, policy_no: str, verification_id: str) -> dict:
    raise VerificationRequired("no live verification for this policy")


def _registry(*, refusing=False) -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(Tool("get_valuation", "value at a date",
                      _refuses if refusing else _valuation,
                      params={"policy_no": "the policy number"}))
    reg.register(Tool("retrieve_clause", "search the rules", _retrieve,
                      params={"query": "what to look up"}))
    return reg


def _run(client, *, registry=None, **over):
    kw = dict(client=client, registry=registry or _registry(), model=MODEL,
              operative_date=OPERATIVE_DATE, audience="front_office")
    kw.update(over)
    return run_console_agent("what was it worth, and may they withdraw?", **kw)


def test_the_console_loop_offers_every_registered_tool():
    client = FakeClient([Resp("end_turn", [text_block(CONSOLE_ABSTAIN)])])
    _run(client)
    names = [t["name"] for t in client.messages.calls[0]["tools"]]
    assert names == ["get_valuation", "retrieve_clause"]


def test_the_target_query_drives_two_tool_calls_and_one_cited_answer():
    # The phase's headline done criterion: valuation with as_at, then
    # retrieval, composed into a single cited answer.
    client = FakeClient([
        Resp("tool_use", [tool_use_block(name="get_valuation",
                                         args={"policy_no": "HB-40582213",
                                               "as_at": "2026-01-12"})]),
        Resp("tool_use", [tool_use_block(name="retrieve_clause",
                                         args={"query": "withdrawal"}, id="tu_2")]),
        Resp("end_turn", [text_block(CONSOLE_ANSWER)]),
    ])
    result = _run(client)
    assert result.reply.abstained is False
    assert result.reply.citations[0].chunk_id == "02-BOND:4.9"
    assert result.reply.tools_used == ["get_valuation", "retrieve_clause"]
    calls = [s for s in result.trace.as_list() if s["kind"] == "tool_call"]
    assert len(calls) == 2
    assert calls[0]["args"]["as_at"] == "2026-01-12"


def test_a_refused_record_tool_becomes_an_abstention_not_an_answer():
    # Done criterion: the loop surfaces a refusal, never a fabricated answer.
    client = FakeClient([
        Resp("tool_use", [tool_use_block(name="get_valuation",
                                         args={"policy_no": "HB-40582213",
                                               "verification_id": ""})]),
        Resp("end_turn", [text_block(CONSOLE_ABSTAIN)]),
    ])
    result = _run(client, registry=_registry(refusing=True))
    assert result.reply.abstained is True
    assert "not verified" in result.reply.abstention_reason
    assert any("refused" in e for e in result.reply.guardrail_events)


def test_a_refusal_is_fed_back_to_the_model_as_an_error():
    # Not swallowed into a gap — a gap is what a model fills from memory.
    client = FakeClient([
        Resp("tool_use", [tool_use_block(name="get_valuation",
                                         args={"policy_no": "X",
                                               "verification_id": ""})]),
        Resp("end_turn", [text_block(CONSOLE_ABSTAIN)]),
    ])
    _run(client, registry=_registry(refusing=True))
    fed_back = client.messages.calls[1]["messages"][-1]["content"][0]
    assert fed_back["is_error"] is True
    assert "REFUSED" in fed_back["content"]


def test_tools_used_reports_what_was_dispatched_not_what_the_model_claimed():
    # CONSOLE_ANSWER claims a tool it never called.
    client = FakeClient([
        Resp("tool_use", [tool_use_block(name="retrieve_clause",
                                         args={"query": "withdrawal"})]),
        Resp("end_turn", [text_block(CONSOLE_ANSWER)]),
    ])
    result = _run(client)
    assert result.reply.tools_used == ["retrieve_clause"]


def test_a_tool_used_twice_is_reported_once():
    client = FakeClient([
        Resp("tool_use", [tool_use_block(name="retrieve_clause",
                                         args={"query": "a"})]),
        Resp("tool_use", [tool_use_block(name="retrieve_clause",
                                         args={"query": "b"}, id="tu_2")]),
        Resp("end_turn", [text_block(CONSOLE_ANSWER)]),
    ])
    assert _run(client).reply.tools_used == ["retrieve_clause"]


def test_the_operative_date_and_audience_reach_the_system_prompt():
    client = FakeClient([Resp("end_turn", [text_block(CONSOLE_ABSTAIN)])])
    _run(client)
    system = client.messages.calls[0]["system"]
    assert OPERATIVE_DATE in system
    assert "front_office" in system


def test_the_model_id_is_the_one_the_caller_passed():
    # Nothing in this module decides the model — it comes from configuration.
    client = FakeClient([Resp("end_turn", [text_block(CONSOLE_ABSTAIN)])])
    _run(client, model="claude-opus-5")
    assert client.messages.calls[0]["model"] == "claude-opus-5"


def test_the_trace_is_returned_and_records_the_refs_retrieval_gave_back():
    client = FakeClient([
        Resp("tool_use", [tool_use_block(name="retrieve_clause",
                                         args={"query": "withdrawal"})]),
        Resp("end_turn", [text_block(CONSOLE_ANSWER)]),
    ])
    result = _run(client)
    kinds = [s["kind"] for s in result.trace.as_list()]
    assert kinds == ["tool_call", "tool_result", "verdict"]
    assert result.trace.as_list()[1]["refs"] == ["02-BOND:4.9"]


def test_a_malformed_console_reply_raises_rather_than_fabricating():
    client = FakeClient([Resp("end_turn", [text_block("{not json")])])
    with pytest.raises(AgentError):
        _run(client)


def test_an_uncited_answer_is_rejected_rather_than_returned():
    uncited = json.dumps({"answer_text": "Trust me.", "citations": []})
    client = FakeClient([Resp("end_turn", [text_block(uncited)])])
    with pytest.raises(AgentError):
        _run(client)


def test_the_console_loop_keeps_the_step_limit():
    client = FakeClient([Resp("tool_use", [tool_use_block(name="retrieve_clause",
                                                          args={"query": "x"})])
                         for _ in range(10)])
    with pytest.raises(AgentError, match="step limit"):
        _run(client, max_steps=3)


def test_the_console_loop_sends_no_sampling_params_and_no_budget_tokens():
    # All four are rejected on claude-sonnet-5.
    client = FakeClient([Resp("end_turn", [text_block(CONSOLE_ABSTAIN)])])
    _run(client)
    sent = client.messages.calls[0]
    assert sent["thinking"] == {"type": "adaptive"}
    for banned in ("temperature", "top_p", "top_k", "budget_tokens"):
        assert banned not in sent


def test_an_api_failure_is_a_typed_agent_error():
    client = FakeClient([RuntimeError("529 overloaded")])
    with pytest.raises(AgentError):
        _run(client)


# ── the request shape follows the model, not the other way round ─────────

def test_a_46_generation_model_gets_adaptive_thinking_and_effort():
    client = FakeClient([Resp("end_turn", [text_block(CONSOLE_ABSTAIN)])])
    _run(client, model="claude-sonnet-5")
    sent = client.messages.calls[0]
    assert sent["thinking"] == {"type": "adaptive"}
    assert sent["output_config"]["effort"] == "high"


def test_an_earlier_model_is_sent_neither():
    # Verified against the API: Haiku 4.5 answers the adaptive request with
    # "400 adaptive thinking is not supported on this model".
    client = FakeClient([Resp("end_turn", [text_block(CONSOLE_ABSTAIN)])])
    _run(client, model="claude-haiku-4-5")
    sent = client.messages.calls[0]
    assert "thinking" not in sent
    assert "effort" not in sent["output_config"]


def test_every_model_still_gets_the_structured_output_format():
    for model in ("claude-sonnet-5", "claude-haiku-4-5", "some-future-model"):
        client = FakeClient([Resp("end_turn", [text_block(CONSOLE_ABSTAIN)])])
        _run(client, model=model)
        fmt = client.messages.calls[0]["output_config"]["format"]
        assert fmt["type"] == "json_schema", model


def test_an_unknown_model_gets_the_conservative_shape():
    # Better to under-ask and work than to send a parameter that 400s.
    client = FakeClient([Resp("end_turn", [text_block(CONSOLE_ABSTAIN)])])
    _run(client, model="claude-something-unreleased")
    assert "thinking" not in client.messages.calls[0]
