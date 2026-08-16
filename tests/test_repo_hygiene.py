"""Guards the Phase 1 start-gates: licence present, secrets never committed.

These are structural checks, not logic tests — they fail the build if the
repository's governance files go missing or if `.env.example` ever grows a
real-looking secret value.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_license_is_mit_with_correct_copyright():
    # Arrange
    license_path = ROOT / "LICENSE"

    # Act
    text = license_path.read_text(encoding="utf-8")

    # Assert
    assert license_path.exists(), "LICENSE file must exist at the repo root"
    assert "MIT License" in text
    assert "Copyright (c) 2026 Shayan Das" in text


def test_gitignore_excludes_secrets_and_caches():
    # Arrange
    gitignore_path = ROOT / ".gitignore"

    # Act
    lines = {
        line.strip()
        for line in gitignore_path.read_text(encoding="utf-8").splitlines()
    }

    # Assert — the three things that must never be tracked
    assert ".env" in lines, ".gitignore must exclude the real .env"
    assert ".venv/" in lines, ".gitignore must exclude the virtualenv"
    assert "__pycache__/" in lines, ".gitignore must exclude bytecode caches"


def test_env_example_lists_required_names_without_real_values():
    # Arrange
    example_path = ROOT / ".env.example"
    required_names = {
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "COHERE_API_KEY",
        "DATABASE_URL",
        "ANTHROPIC_MODEL",
        "JUDGE_MODEL",
    }

    # Act
    raw = example_path.read_text(encoding="utf-8")
    assignments = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, _, value = stripped.partition("=")
        assignments[name.strip()] = value.strip()

    # Assert — every required variable is documented
    assert required_names.issubset(assignments.keys()), (
        f"missing from .env.example: {required_names - set(assignments)}"
    )

    # Assert — no real secret ever ships. Secret-bearing variables must be empty
    # or an obvious <placeholder>, never a plausible live value. Non-secret config
    # (e.g. model IDs) may carry a real default.
    secret_names = {
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "COHERE_API_KEY",
        "DATABASE_URL",
    }
    for name in secret_names:
        value = assignments[name]
        assert value == "" or (value.startswith("<") and value.endswith(">")), (
            f"{name} in .env.example has a non-placeholder value: {value!r}"
        )
