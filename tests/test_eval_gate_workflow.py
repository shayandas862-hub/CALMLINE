"""The eval-gate workflow runs the gate on PRs with zero live calls / secrets."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "eval-gate.yml"


def test_workflow_exists():
    assert WORKFLOW.exists()


def test_triggers_on_pull_request():
    assert "pull_request:" in WORKFLOW.read_text(encoding="utf-8")


def test_runs_the_gate():
    assert "scripts/eval_gate.py" in WORKFLOW.read_text(encoding="utf-8")


def test_uses_no_secrets_and_no_live_calls():
    text = WORKFLOW.read_text(encoding="utf-8")
    # the gate scores cached outputs — it must not interpolate any GitHub secret
    # (`${{ secrets.X }}`) nor name a model key. Prose mentioning "secrets" is fine.
    assert "${{ secrets." not in text
    assert "ANTHROPIC_API_KEY" not in text
    assert "OPENAI_API_KEY" not in text
    assert "COHERE_API_KEY" not in text


def test_the_workflow_verifies_the_golden_set_has_not_been_tuned():
    # A gate that scores a set somebody edited is a gate that can be walked
    # around: fail the case, reword the case, pass the gate.
    assert "freeze_goldens.py" in WORKFLOW.read_text(encoding="utf-8")


def test_the_workflow_regenerates_the_set_to_prove_it_matches_the_kb():
    # The committed set is derived. If the KB moved and nobody re-ran the
    # generator, the exam and the syllabus have quietly diverged.
    assert "build_golden_from_kb.py --check" in WORKFLOW.read_text(encoding="utf-8")


def test_the_gate_reports_itself_inactive_until_a_baseline_lands():
    # Honest, rather than passing silently as though it had checked something.
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "baseline.json" in text and "inactive" in text
