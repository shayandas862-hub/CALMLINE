"""The CI workflow must run the unit tests and the banned-words guard.

Text-based checks (no YAML dependency) that fail if the workflow loses its
essential steps — the two things that must run on every push.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"


def test_workflow_exists():
    assert WORKFLOW.exists(), ".github/workflows/tests.yml must exist"


def test_workflow_triggers_on_push_and_pr():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "push:" in text
    assert "pull_request:" in text


def test_workflow_runs_unit_tests_excluding_integration():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "pytest" in text
    assert "not integration" in text, "CI must not run live-Supabase integration tests"


def test_workflow_runs_banned_words_check():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "check_banned_words.py" in text
    assert "BANNED_WORDS" in text, "CI must pass the banned-words secret to the check"
