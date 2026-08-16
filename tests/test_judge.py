"""Phase 7 Task 2 — the LLM-judge grades the qualitative rubric points.

Every test drives a STUBBED client — zero live calls, zero spend. The judge
turns a (rubric point, case, agent output) into a structured pass/fail + reason,
and raises JudgeError on a malformed or failed call rather than EVER silently
passing (a silent pass would inflate the score — the one thing a judge must not do).
"""

import pytest

from src.evals.agreement import agreement
from src.evals.judge import (
    QUALITATIVE_POINTS,
    JudgeError,
    JudgeVerdict,
    applicable_points,
    get_point,
    judge_point,
    judge_run,
)


# ── stub Anthropic client (mirrors the shape src/agent/loop.py consumes) ──────
class _Block:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _Resp:
    def __init__(self, text):
        self.stop_reason = "end_turn"
        self.content = [_Block(text)]


class _Messages:
    def __init__(self, text, calls, raises):
        self._text, self._calls, self._raises = text, calls, raises

    def create(self, **kwargs):
        self._calls.append(kwargs)
        if self._raises:
            raise self._raises
        return _Resp(self._text)


class FakeClient:
    def __init__(self, text="", *, raises=None):
        self.calls = []
        self.messages = _Messages(text, self.calls, raises)


CASE = {
    "id": "c-bereaved",
    "case_type": "call",
    "transcript": [{"who": "caller", "text": "my husband just died — is the payout taxed?"}],
}
ANSWER_OUTPUT = {
    "decision": "answer",
    "answer_text": "I'm very sorry for your loss. The policy pays a lump-sum death benefit on a valid claim.",
    "citation_clause_ref": "TL-3.1",
    "vulnerability_flags": [{"name": "bereavement", "driver": "life_events"}],
}


def test_registry_has_exactly_the_four_qualitative_points():
    assert {p.point_id for p in QUALITATIVE_POINTS} == {"R5", "R8", "R11", "R12"}


def test_get_point_returns_the_criterion():
    p = get_point("R12")
    assert p.point_id == "R12"
    assert p.criterion  # non-empty rubric text the judge applies


def test_judge_returns_a_structured_pass():
    client = FakeClient('{"passed": true, "reason": "calm, plain, acknowledges the loss"}')
    v = judge_point(get_point("R12"), CASE, ANSWER_OUTPUT, client=client)
    assert isinstance(v, JudgeVerdict)
    assert v.point_id == "R12" and v.passed is True
    assert "calm" in v.reason


def test_judge_returns_a_structured_fail():
    client = FakeClient('{"passed": false, "reason": "jargon dump, no acknowledgement"}')
    v = judge_point(get_point("R12"), CASE, ANSWER_OUTPUT, client=client)
    assert v.passed is False and v.reason


def test_malformed_json_raises_judgeerror_never_silent_pass():
    client = FakeClient("the answer seems fine to me")  # not JSON
    with pytest.raises(JudgeError):
        judge_point(get_point("R8"), CASE, ANSWER_OUTPUT, client=client)


def test_missing_field_raises_judgeerror():
    client = FakeClient('{"passed": true}')  # no reason
    with pytest.raises(JudgeError):
        judge_point(get_point("R11"), CASE, ANSWER_OUTPUT, client=client)


def test_api_failure_raises_judgeerror():
    client = FakeClient(raises=RuntimeError("503 overloaded"))
    with pytest.raises(JudgeError):
        judge_point(get_point("R5"), CASE, ANSWER_OUTPUT, client=client)


def test_prompt_carries_the_criterion_and_the_answer_text():
    client = FakeClient('{"passed": true, "reason": "ok"}')
    judge_point(get_point("R11"), CASE, ANSWER_OUTPUT, client=client)
    sent = client.calls[0]
    blob = str(sent.get("system", "")) + str(sent.get("messages", ""))
    assert "recommendation" in blob.lower()  # R11 criterion is about personal recommendations
    assert ANSWER_OUTPUT["answer_text"] in blob  # the judge actually sees the answer


def test_model_is_env_configurable(monkeypatch):
    monkeypatch.setenv("JUDGE_MODEL", "claude-opus-4-8-custom")
    client = FakeClient('{"passed": true, "reason": "ok"}')
    judge_point(get_point("R12"), CASE, ANSWER_OUTPUT, client=client)
    assert client.calls[0]["model"] == "claude-opus-4-8-custom"


def test_no_sampling_params_sent_opus48_contract():
    client = FakeClient('{"passed": true, "reason": "ok"}')
    judge_point(get_point("R12"), CASE, ANSWER_OUTPUT, client=client)
    sent = client.calls[0]
    for banned in ("temperature", "top_p", "top_k", "budget_tokens"):
        assert banned not in sent


# ── applicability + run orchestration ────────────────────────────────────────
def test_applicable_points_for_a_flagged_answer_are_all_four():
    ids = [p.point_id for p in applicable_points(ANSWER_OUTPUT)]
    assert ids == ["R5", "R8", "R11", "R12"]


def test_r5_dropped_when_no_flag():
    plain_answer = dict(ANSWER_OUTPUT, vulnerability_flags=[])
    ids = [p.point_id for p in applicable_points(plain_answer)]
    assert ids == ["R8", "R11", "R12"]  # nothing to "reflect" without a flag


def test_no_qualitative_points_for_a_refusal():
    refuse = {"decision": "refuse", "escalation_route": "adviser"}
    assert applicable_points(refuse) == []  # a refusal has no answer prose to grade


def test_judge_run_grades_only_answer_cases_and_feeds_agreement():
    cases = [CASE, {"id": "c-refuse", "case_type": "call", "transcript": []}]
    run = [
        {"id": "c-bereaved", "case_type": "call", "output": ANSWER_OUTPUT},
        {"id": "c-refuse", "case_type": "call",
         "output": {"decision": "refuse", "escalation_route": "adviser"}},
    ]
    client = FakeClient('{"passed": true, "reason": "ok"}')
    grades = judge_run(cases, run, client=client)

    # only the answer case is graded, all four of its points
    assert {(g["case_id"], g["point_id"]) for g in grades} == {
        ("c-bereaved", "R5"), ("c-bereaved", "R8"),
        ("c-bereaved", "R11"), ("c-bereaved", "R12"),
    }
    # the grade records drop straight into the agreement harness
    hand = [dict(g) for g in grades]
    assert agreement(grades, hand).agreement == 1.0


def test_judge_run_forwards_clause_text_for_faithfulness():
    cases = [CASE]
    run = [{"id": "c-bereaved", "case_type": "call", "output": ANSWER_OUTPUT}]
    client = FakeClient('{"passed": true, "reason": "ok"}')
    judge_run(cases, run, client=client, clause_text_by_ref={"TL-3.1": "Pays a lump sum on death."})
    # the R8 call must carry the cited clause text so faithfulness is judgeable
    blobs = [str(c.get("messages", "")) for c in client.calls]
    assert any("Pays a lump sum on death." in b for b in blobs)
