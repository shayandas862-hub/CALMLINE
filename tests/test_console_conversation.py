"""v4 phase 5 · Task 8 — the agent remembers through the endpoint.

`tests/test_conversation.py` tests the store; this drives `/api/agent` and asks
whether a second question actually sees the first. The distinction matters —
phase 4's handoff records two defects that were tests proving a unit worked
while the product did not.
"""

import copy
import json

from fastapi.testclient import TestClient

from src.agent.conversation import ConversationStore
from src.web.console.app import create_console_app

POLICY_A = "LP-20419876"
POLICY_B = "HB-40582213"
CONFIRMED = ["policy_no", "name_dob", "address_or_bank"]

REPLY = json.dumps({"answer_text": "It was worth £46,210.00.",
                    "citations": [], "abstained": False, "tools_used": []})


class _Blk:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Resp:
    def __init__(self, stop_reason, content):
        self.stop_reason, self.content = stop_reason, content


class _Messages:
    def __init__(self, responses):
        self._responses, self.calls = list(responses), []

    def create(self, **kw):
        # Snapshot `messages`. The loop mutates the same list across steps, so
        # storing the reference makes every recorded call show the final state
        # — which would have made these assertions pass for the wrong reason.
        self.calls.append({**kw, "messages": copy.deepcopy(kw["messages"])})
        return self._responses.pop(0)


class _Client:
    def __init__(self, responses):
        self.messages = _Messages(responses)


def _text(body):
    return _Resp("end_turn", [_Blk(type="text", text=body)])


def _tool(name="retrieve_clause", args=None, id="tu_1"):
    """A tool step. The grounding check refuses an answer that used none."""
    return _Resp("tool_use", [_Blk(type="tool_use", name=name,
                                   input=args or {"query": "x"}, id=id)])


def _answer():
    """One full exchange: a tool call, then the reply."""
    return [_tool(), _text(REPLY)]


def _live(responses, conversations=None):
    client = _Client(responses)
    app = create_console_app(secret="test-secret", api_key="sk-ant-test",
                             model="claude-sonnet-5",
                             client_factory=lambda key: client,
                             conversations=conversations or ConversationStore())
    return app, client


def _verified(app, policy_no=POLICY_A):
    c = TestClient(app)
    c.post("/api/login", json={"role": "front_office"})
    cn = c.post("/api/interaction/open",
                json={"policy_no": policy_no}).json()["cn_ref"]
    c.post("/api/verify", json={"cn_ref": cn, "policy_no": policy_no})
    r = c.post("/api/verify", json={"cn_ref": cn, "policy_no": policy_no,
                                    "confirmed": CONFIRMED})
    assert r.json()["outcome"] == "passed"
    return c, cn


def _ask(c, cn, message, policy_no=POLICY_A):
    return c.post("/api/agent", json={"policy_no": policy_no, "cn_ref": cn,
                                      "message": message}).json()


def _sent_messages(client, call_index):
    return client.messages.calls[call_index]["messages"]


# ── a second question sees the first ───────────────────────────────────

def test_a_follow_up_carries_the_earlier_exchange():
    app, client = _live([*_answer(), *_answer()])
    c, cn = _verified(app)
    _ask(c, cn, "what is their balance?")
    _ask(c, cn, "and how do they claim?")

    # calls: 0,1 = first question (tool then reply); 2 = second question opens
    second = _sent_messages(client, 2)
    assert [m["role"] for m in second[:2]] == ["user", "assistant"]
    assert "what is their balance?" in second[0]["content"]
    assert "and how do they claim?" in second[-1]["content"]


def test_the_first_question_starts_cold():
    app, client = _live(_answer())
    c, cn = _verified(app)
    _ask(c, cn, "what is their balance?")
    assert len(_sent_messages(client, 0)) == 1


# ── the policy-switch trap, through the endpoint ───────────────────────

def test_switching_policy_does_not_carry_the_first_policys_context():
    # THE trap (P-CL-001 §2). Verification is scoped to (CN-, policy_no), so
    # policy B needs its own — but nothing crosses the endpoint when the model
    # simply remembers A's record, so the gate cannot catch it. The conversation
    # is keyed on the pair precisely so there is nothing to catch.
    app, client = _live([*_answer(), *_answer()])
    c, cn = _verified(app)
    _ask(c, cn, "what is their balance?", policy_no=POLICY_A)

    # Verify B inside the SAME interaction, so the gate is satisfied and the
    # question genuinely reaches the agent. This is the dangerous case: the
    # request is legitimate, and only the conversation's scoping stops A's
    # record travelling into it.
    c.post("/api/verify", json={"cn_ref": cn, "policy_no": POLICY_B})
    r = c.post("/api/verify", json={"cn_ref": cn, "policy_no": POLICY_B,
                                    "confirmed": CONFIRMED})
    assert r.json()["outcome"] == "passed"
    _ask(c, cn, "and what is this one worth?", policy_no=POLICY_B)

    # The B request opens at call index 2; nothing before it may carry A.
    for message in _sent_messages(client, 2):
        assert POLICY_A not in str(message.get("content", "")), (
            "policy A's context reached a question about policy B")


# ── the boundary holds ─────────────────────────────────────────────────

def test_a_different_interaction_starts_cold():
    conversations = ConversationStore()
    app, client = _live([*_answer(), *_answer()], conversations)
    c, cn = _verified(app)
    _ask(c, cn, "what is their balance?")

    c2, cn2 = _verified(app)
    _ask(c2, cn2, "different caller entirely")
    assert len(_sent_messages(client, 2)) == 1


def test_closing_the_interaction_ends_the_conversation():
    # The done criterion: a question after the interaction closes sees nothing.
    conversations = ConversationStore()
    app, client = _live([*_answer(), *_answer()], conversations)
    c, cn = _verified(app)
    _ask(c, cn, "what is their balance?")
    assert conversations.turns(cn, POLICY_A)

    conversations.expire_for_interaction(cn)
    _ask(c, cn, "do you remember?")
    assert len(_sent_messages(client, 2)) == 1


def test_the_keyword_path_remembers_too():
    # Both paths, one behaviour — otherwise the offline demo answers a follow-up
    # the live console could not, or the reverse.
    conversations = ConversationStore()
    app = create_console_app(secret="test-secret", conversations=conversations)
    c, cn = _verified(app)
    _ask(c, cn, "what is their balance?")
    assert len(conversations.turns(cn, POLICY_A)) == 1
