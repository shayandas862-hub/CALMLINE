"""v4 phase 4 — grounding, checked by the loop because only the loop knows.

Split from ``tests/test_console_loop.py`` at the 300-line rule.

An earlier design put "an answer must cite a clause" on ``ConsoleReply``. A
handler hit it on the first obvious record question — *"what is the value
today?"* — because a ledger figure has no clause behind it, so the rule forced a
choice between fabricating a reference and refusing a question the agent could
answer. The invariant moved here and got stronger: an answer must rest on a tool
that actually ran, and every clause it cites must be one retrieval really
returned. Neither is something the model can attest to about itself.
"""

import json

import pytest

from src.agent.console_loop import run_console_agent
from src.agent.loop import AgentError
from src.agent.tools.registry import Tool, ToolRegistry

OPERATIVE_DATE = "2026-04-12"
MODEL = "claude-sonnet-5"

CONSOLE_ANSWER = json.dumps({
    "answer_text": "It was worth £46,210.00; a £40,000 withdrawal needs approval.",
    "citations": [{"chunk_id": "02-BOND:4.9",
                   "citation_style": "aldercrest_standard"}],
    "abstained": False,
})
CONSOLE_ABSTAIN = json.dumps({
    "answer_text": "", "abstained": True,
    "abstention_reason": "the caller is not verified for this policy",
})


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
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


def _valuation(*, policy_no: str, as_at: str) -> dict:
    return {"found": True, "policy_no": policy_no, "as_at": as_at,
            "value_pence": 4621000, "value": "£46,210.00"}


def _retrieve(*, query: str) -> dict:
    return {"found": True, "query": query, "clauses": [
        {"chunk_id": "02-BOND:4.9", "citation_style": "aldercrest_standard"}]}


def _registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(Tool("get_valuation", "value at a date", _valuation,
                      params={"policy_no": "the policy number"}))
    reg.register(Tool("retrieve_clause", "search the rules", _retrieve,
                      params={"query": "what to look up"}))
    return reg


def _run(client, **over):
    kw = dict(client=client, registry=_registry(), model=MODEL,
              operative_date=OPERATIVE_DATE, audience="front_office")
    kw.update(over)
    return run_console_agent("what was it worth, and may they withdraw?", **kw)

def test_an_answer_about_the_record_needs_no_citation():
    # The bug a handler hit live: "what is the value today?" is answered from
    # the ledger, which has no clause to cite. Refusing that would be the
    # product declining a question it can correctly answer.
    record_answer = json.dumps({
        "answer_text": "The current value is £150,240.00.", "citations": []})
    client = FakeClient([
        Resp("tool_use", [tool_use_block(name="get_valuation",
                                         args={"policy_no": "HB-40582213",
                                               "as_at": "2026-04-12"})]),
        Resp("end_turn", [text_block(record_answer)]),
    ])
    result = _run(client)
    assert result.reply.abstained is False
    assert result.reply.citations == []
    assert result.reply.tools_used == ["get_valuation"]


def test_an_answer_that_used_no_tool_at_all_is_refused():
    # Nothing ran, so the claim came from memory.
    uncited = json.dumps({"answer_text": "It is worth about £150,000.",
                          "citations": []})
    client = FakeClient([Resp("end_turn", [text_block(uncited)])])
    with pytest.raises(AgentError, match="without using any tool"):
        _run(client)


def test_a_citation_retrieval_never_returned_is_refused():
    # A plausible clause id produced from memory is the real fabrication risk,
    # and it is one only the loop can catch.
    invented = json.dumps({
        "answer_text": "Withdrawals need approval.",
        "citations": [{"chunk_id": "02-BOND:99.9"}]})
    client = FakeClient([
        Resp("tool_use", [tool_use_block(name="retrieve_clause",
                                         args={"query": "withdrawal"})]),
        Resp("end_turn", [text_block(invented)]),
    ])
    with pytest.raises(AgentError, match="fabricated"):
        _run(client)


def test_a_citation_retrieval_did_return_is_accepted():
    client = FakeClient([
        Resp("tool_use", [tool_use_block(name="retrieve_clause",
                                         args={"query": "withdrawal"})]),
        Resp("end_turn", [text_block(CONSOLE_ANSWER)]),
    ])
    assert _run(client).reply.citations[0].chunk_id == "02-BOND:4.9"


def test_an_abstention_is_not_asked_to_ground_itself():
    client = FakeClient([Resp("end_turn", [text_block(CONSOLE_ABSTAIN)])])
    assert _run(client).reply.abstained is True
