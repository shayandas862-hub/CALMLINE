"""The wordlist guard: no listed term ever lands in a committed file.

The real wordlist lives only in a gitignored local file — it is NEVER written
into the repo, including into this test. These tests use a stand-in word
("acmecorp") to prove the scanning mechanism works.
"""

from scripts.check_banned_words import find_violations, load_banned_words

STANDIN = "acmecorp"


def test_flags_a_file_containing_a_banned_word(tmp_path):
    # Arrange
    offending = tmp_path / "leak.md"
    offending.write_text(f"This mentions {STANDIN} which must never ship.", encoding="utf-8")

    # Act
    violations = find_violations([offending], [STANDIN])

    # Assert
    assert len(violations) == 1
    path, word = violations[0]
    assert path == offending
    assert word == STANDIN


def test_clean_tree_passes(tmp_path):
    # Arrange
    clean = tmp_path / "fine.md"
    clean.write_text("Nothing forbidden here — synthetic insurer only.", encoding="utf-8")

    # Act
    violations = find_violations([clean], [STANDIN])

    # Assert
    assert violations == []


def test_match_is_case_insensitive(tmp_path):
    # Arrange
    offending = tmp_path / "mixed.md"
    offending.write_text("AcMeCoRp appears here.", encoding="utf-8")

    # Act
    violations = find_violations([offending], [STANDIN])

    # Assert
    assert len(violations) == 1


def test_binary_and_missing_files_are_skipped_not_crashed(tmp_path):
    # Arrange — a binary blob and a path that does not exist
    binary = tmp_path / "blob.bin"
    binary.write_bytes(b"\x00\x01\x02" + STANDIN.encode())
    ghost = tmp_path / "does-not-exist.md"

    # Act / Assert — scanning must not raise
    violations = find_violations([binary, ghost], [STANDIN])
    assert isinstance(violations, list)


def test_load_words_from_local_file(tmp_path):
    # Arrange — the gitignored list format: one word per line, # comments allowed
    local = tmp_path / ".banned-words.local"
    local.write_text("# forbidden names\n" + STANDIN + "\n\nwidgetco\n", encoding="utf-8")

    # Act
    words = load_banned_words(root=tmp_path, env={})

    # Assert
    assert STANDIN in words
    assert "widgetco" in words
    assert all(not w.startswith("#") for w in words)


def test_load_words_from_env_when_no_local_file(tmp_path):
    # Act — no local file present; CI supplies the list via a secret env var
    words = load_banned_words(root=tmp_path, env={"BANNED_WORDS": "acmecorp, widgetco"})

    # Assert
    assert set(words) == {"acmecorp", "widgetco"}


def test_no_source_configured_returns_empty(tmp_path):
    # Act — neither file nor env; caller decides how to warn
    words = load_banned_words(root=tmp_path, env={})

    # Assert
    assert words == []
