"""The release gate's verdict on the committed corpus, and its CLI contract.

`test_kb_validate.py` proves each check accepts and rejects the right thing on
fixtures. This file answers the question the gate exists to answer:

    python -m src.corpus.kb_validate data/kb

**Is `data/kb/` releasable right now?** It must print `PASS` with the real chunk
count and exit 0, and it must exit non-zero on any injected defect — that exit
code is what blocks a release, so it is worth a test of its own.
"""

from datetime import date
from pathlib import Path

from src.corpus.kb_parser import parse_kb
from src.corpus.kb_validate import (
    KB_DATE,
    declared_chunk_count,
    duplicate_chunk_ids,
    main,
    validate,
)

KB = Path(__file__).resolve().parent.parent / "data" / "kb"


# --- the committed corpus -------------------------------------------------

def test_chunk_ids_are_unique_across_the_knowledge_base():
    duplicates = duplicate_chunk_ids(KB)
    assert duplicates == {}, (
        f"chunk_id collisions leave a chunk uncitable and un-upsertable: {duplicates}"
    )


def test_the_committed_knowledge_base_passes_the_gate():
    report = validate(KB)
    assert report.passed is True, f"failures: {report.failures}"
    assert report.chunk_count == 441
    assert report.embedded_count == 438


def test_the_readme_declares_the_count_the_parser_actually_yields():
    # The reconciliation the spec asked for: the corpus's own record was wrong
    # (it claimed 423) and is now enforced rather than decorative.
    assert declared_chunk_count(KB) == 441
    assert declared_chunk_count(KB) == len(parse_kb(KB))


def test_the_knowledge_base_date_is_the_one_the_corpus_states():
    # "Knowledge-base date: 13 July 2026" — README.md and every doc's frontmatter.
    assert KB_DATE == date(2026, 7, 13)


# --- the CLI contract -----------------------------------------------------

def test_the_cli_prints_pass_and_the_real_count(capsys):
    exit_code = main([str(KB)])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "PASS" in out
    assert "441" in out


def test_the_cli_reports_how_many_chunks_are_withheld(capsys):
    main([str(KB)])
    out = capsys.readouterr().out
    assert "438 embeddable" in out
    assert "3 withheld" in out


def test_the_cli_exits_non_zero_on_an_injected_defect(tmp_path, capsys):
    # Arrange — one typo'd audience is enough to block a release
    (tmp_path / "02_bond.md").write_text(
        "## 4.1 Fund taxation\n"
        "*meta: doc=02-BOND | sec=4.1 | aud=everyone | type=tax_rule | data=real*\n"
        "Life funds pay corporation tax.\n",
        encoding="utf-8",
    )

    # Act
    exit_code = main([str(tmp_path)])
    out = capsys.readouterr().out

    # Assert
    assert exit_code != 0
    assert "FAIL" in out
    assert "everyone" in out


def test_the_cli_rejects_a_missing_argument(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().out
