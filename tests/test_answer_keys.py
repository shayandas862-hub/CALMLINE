"""v4 phase 6 · Task 3's producer — the judge grades answer-key coverage.

The scorer folds `record["answer_keys"]` into the coverage metric. Nothing
produced them until this: a metric with no producer is the exact defect this
phase's card was corrected for, twice over.

**One call per key.** The existing judge's discipline is "grade EXACTLY ONE
criterion — nothing else", and asking for five verdicts in one reply is how a
grader starts averaging them. Cheap on Haiku, and strictness is what the
coverage number is for.

The judge grades **prose against a key**. It is never shown the expected
chunks: retrieval is scored by recall@5, and letting the judge see what should
have been retrieved would let a well-worded miss score as a hit.
"""

import json

import pytest

from src.evals.answer_keys import grade_answer_keys, grade_run
from src.evals.judge import JudgeError

CASE = {"id": "E01", "tier": "R", "question": "Grace period after a missed premium?",
        "answer_keys": ["30 days", "claim paid net of premium"],
        "expected_chunks": ["01-WOL:3.10"], "failure_watched": "wrong figure"}


class _Blk:
    def __init__(self, text):
        self.type, self.text = "text", text


class _Resp:
    def __init__(self, text):
        self.content = [_Blk(text)]


class _Client:
    """Records every call, replies with the queued verdicts in order."""

    def __init__(self, verdicts):
        self.calls = []
        outer = self

        class _Messages:
            def create(self, **kw):
                outer.calls.append(kw)
                passed, reason = verdicts[len(outer.calls) - 1]
                return _Resp(json.dumps({"passed": passed, "reason": reason}))

        self.messages = _Messages()


def _record(**over):
    record = {"id": "E01", "tier": "R", "retrieved": [], "answer_keys": [],
              "reply": {"answer_text": "Thirty days, paid net of the premium.",
                        "abstained": False, "abstention_reason": "",
                        "guardrail_events": [], "citations": []}}
    record.update(over)
    return record


# ── grading one case ───────────────────────────────────────────────────

def test_each_answer_key_is_graded_in_its_own_call():
    client = _Client([(True, "states 30 days"), (True, "says net of premium")])
    grades = grade_answer_keys(CASE, _record(), client=client, model="claude-haiku-4-5")
    assert len(client.calls) == 2
    assert [g["key"] for g in grades] == CASE["answer_keys"]
    assert all(g["covered"] for g in grades)


def test_a_key_the_answer_misses_is_marked_uncovered_with_a_reason():
    client = _Client([(True, "states 30 days"), (False, "never mentions the premium")])
    grades = grade_answer_keys(CASE, _record(), client=client, model="claude-haiku-4-5")
    assert grades[1]["covered"] is False
    assert "premium" in grades[1]["reason"]


def test_the_answer_prose_is_what_the_judge_is_shown():
    client = _Client([(True, "y"), (True, "y")])
    grade_answer_keys(CASE, _record(), client=client, model="claude-haiku-4-5")
    prompt = client.calls[0]["messages"][0]["content"]
    assert "Thirty days, paid net of the premium." in prompt
    assert "30 days" in prompt  # the key being graded


def test_the_judge_is_never_shown_the_expected_chunks():
    # Retrieval is scored by recall@5. A judge that can see what SHOULD have
    # been retrieved can mark a well-worded miss as a hit.
    client = _Client([(True, "y"), (True, "y")])
    grade_answer_keys(CASE, _record(), client=client, model="claude-haiku-4-5")
    prompt = client.calls[0]["messages"][0]["content"]
    assert "01-WOL:3.10" not in prompt


def test_malformed_judge_output_raises_rather_than_passing():
    class _Bad:
        messages = type("M", (), {"create": lambda self, **kw: _Resp("not json")})()

    with pytest.raises(JudgeError):
        grade_answer_keys(CASE, _record(), client=_Bad(), model="claude-haiku-4-5")


def test_a_transport_failure_raises_rather_than_passing():
    class _Down:
        messages = type("M", (), {
            "create": lambda self, **kw: (_ for _ in ()).throw(RuntimeError("503"))})()

    with pytest.raises(JudgeError):
        grade_answer_keys(CASE, _record(), client=_Down(), model="claude-haiku-4-5")


# ── the model the judge runs on ────────────────────────────────────────

def test_haiku_is_not_sent_adaptive_thinking():
    # Haiku 4.5 predates adaptive thinking. The judge used to hardcode
    # `thinking={"type": "adaptive"}` for every model, which would have failed
    # outright the first time it ran on the phase's own judge model.
    client = _Client([(True, "y"), (True, "y")])
    grade_answer_keys(CASE, _record(), client=client, model="claude-haiku-4-5")
    assert "thinking" not in client.calls[0]


def test_the_judge_model_is_named_on_every_call():
    client = _Client([(True, "y"), (True, "y")])
    grade_answer_keys(CASE, _record(), client=client, model="claude-haiku-4-5")
    assert client.calls[0]["model"] == "claude-haiku-4-5"


def test_the_environment_names_the_judge_when_the_caller_does_not(monkeypatch):
    monkeypatch.setenv("JUDGE_MODEL", "claude-haiku-4-5")
    client = _Client([(True, "y"), (True, "y")])
    grade_answer_keys(CASE, _record(), client=client)
    assert client.calls[0]["model"] == "claude-haiku-4-5"


# ── grading a whole run ────────────────────────────────────────────────

def test_grade_run_fills_the_grades_the_scorer_folds():
    client = _Client([(True, "y"), (False, "n")])
    records = grade_run([CASE], [_record()], client=client, model="claude-haiku-4-5")
    assert [g["covered"] for g in records[0]["answer_keys"]] == [True, False]


def test_an_errored_case_is_not_sent_to_the_judge():
    # There is no answer to grade, and spending a call to be told so is waste.
    client = _Client([])
    records = grade_run([CASE], [{"id": "E01", "error": "boom"}],
                        client=client, model="claude-haiku-4-5")
    assert client.calls == []
    assert records[0]["answer_keys"] == []


def test_a_case_with_no_record_is_left_alone():
    client = _Client([])
    assert grade_run([CASE], [], client=client, model="claude-haiku-4-5") == []


def test_grading_does_not_mutate_the_record_it_was_given():
    original = _record()
    client = _Client([(True, "y"), (True, "y")])
    grade_run([CASE], [original], client=client, model="claude-haiku-4-5")
    assert original["answer_keys"] == []
