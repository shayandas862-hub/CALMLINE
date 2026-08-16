"""The knowledge-base release gate — non-zero exit blocks the release.

Five things must hold before the corpus may be embedded or shipped:

  1. **chunk_id uniqueness** — a collision leaves a chunk uncitable, silently.
  2. **vocabulary conformance** — `doc`/`aud`/`type` come from a closed set, or
     audience filtering and product filtering quietly stop working.
  3. **provenance parseability** — every `data=` value resolves to a citation
     style, so no answer can attribute a fictional threshold as though it were
     law.
  4. **statable effective dates** — a rule legislated but not yet in force is
     only answerable if the chunk actually contains its commencement date.
  5. **count reconciliation** — the parsed total matches what
     `data/kb/README.md` declares, so editing the corpus without updating its
     own change record fails the gate rather than drifting.

The gate *reports*; it never tracebacks. A corpus that cannot be parsed is a
failure line, not a crash.
"""

from datetime import date
from pathlib import Path

from src.corpus.kb_validate import (
    AUDIENCES,
    DOCS,
    KB_DATE,
    TYPES,
    declared_chunk_count,
    duplicate_chunk_ids,
    main,
    validate,
)

KB = Path(__file__).resolve().parent.parent / "data" / "kb"

GOOD = (
    "## 4.1 Fund taxation\n"
    "*meta: doc=02-BOND | sec=4.1 | aud=all | type=tax_rule | data=real*\n"
    "Life funds pay corporation tax.\n"
)


def _kb(tmp_path: Path, *docs: str, declared: int | None = None) -> Path:
    """A throwaway KB directory: one file per doc, plus an optional README claim."""
    for index, body in enumerate(docs, start=1):
        (tmp_path / f"{index:02d}_doc.md").write_text(body, encoding="utf-8")
    if declared is not None:
        (tmp_path / "README.md").write_text(
            f"Expected on a clean package: **{declared} chunks**, `RESULT: PASS`.\n",
            encoding="utf-8",
        )
    return tmp_path


# --- 1. chunk_id uniqueness -----------------------------------------------


def test_a_collision_is_reported_with_both_claimants(tmp_path):
    # Arrange
    kb = _kb(tmp_path, (
        "# First\n"
        "*meta: doc=01-WOL | sec=frontmatter | aud=all | type=caveats | data=mixed*\n"
        "Body one.\n"
        "## Second\n"
        "*meta: doc=01-WOL | sec=frontmatter | aud=all | type=caveats | data=mixed*\n"
        "Body two.\n"
    ))

    # Act
    duplicates = duplicate_chunk_ids(kb)

    # Assert — it names both, so the fix is obvious
    assert list(duplicates) == ["01-WOL:frontmatter"]
    assert duplicates["01-WOL:frontmatter"] == ["First", "Second"]


def test_a_collision_across_two_documents_is_reported(tmp_path):
    kb = _kb(tmp_path, GOOD, GOOD)
    assert list(duplicate_chunk_ids(kb)) == ["02-BOND:4.1"]


def test_a_collision_fails_the_gate(tmp_path):
    report = validate(_kb(tmp_path, GOOD, GOOD))
    assert report.passed is False
    assert any("02-BOND:4.1" in failure for failure in report.failures)


def test_distinct_sections_do_not_collide(tmp_path):
    kb = _kb(tmp_path, (
        "# Title\n"
        "*meta: doc=05-OPS | sec=frontmatter | aud=all | type=caveats | data=mixed*\n"
        "One.\n"
        "# Subtitle\n"
        "*meta: doc=05-OPS | sec=frontmatter-title | aud=all | type=caveats | data=mixed*\n"
        "Two.\n"
    ))
    assert duplicate_chunk_ids(kb) == {}


def test_the_kb_readme_is_not_treated_as_corpus(tmp_path):
    # README.md documents the contract by example — those meta lines are not corpus.
    (tmp_path / "README.md").write_text(GOOD, encoding="utf-8")
    (tmp_path / "02_bond.md").write_text(GOOD, encoding="utf-8")
    assert duplicate_chunk_ids(tmp_path) == {}


def test_headings_without_a_meta_line_emit_no_chunk(tmp_path):
    kb = _kb(tmp_path, (
        "# PART I — PRODUCT\n"
        "\n"
        "## 1. What the product is\n"
        "*meta: doc=01-WOL | sec=1 | aud=all | type=overview | data=mixed*\n"
        "Body.\n"
        "# PART II — OPERATIONS\n"
    ))
    assert duplicate_chunk_ids(kb) == {}


# --- 2. vocabulary conformance -------------------------------------------

def test_the_vocabularies_are_the_closed_sets_the_kb_declares():
    assert len(DOCS) == 7
    assert AUDIENCES == frozenset(
        {"customer", "back_office", "ops", "regulatory", "all"})
    assert len(TYPES) == 21


def test_an_unknown_doc_fails_the_gate(tmp_path):
    kb = _kb(tmp_path, GOOD.replace("doc=02-BOND", "doc=99-NOPE"))
    report = validate(kb)
    assert report.passed is False
    assert any("99-NOPE" in f for f in report.failures)


def test_an_unknown_audience_fails_the_gate(tmp_path):
    # A typo'd audience silently removes the chunk from every filtered search.
    report = validate(_kb(tmp_path, GOOD.replace("aud=all", "aud=everyone")))
    assert report.passed is False
    assert any("everyone" in f for f in report.failures)


def test_an_unknown_type_fails_the_gate(tmp_path):
    report = validate(_kb(tmp_path, GOOD.replace("type=tax_rule", "type=musings")))
    assert report.passed is False
    assert any("musings" in f for f in report.failures)


# --- 3. provenance parseability ------------------------------------------

def test_an_unparseable_provenance_is_a_failure_line_not_a_traceback(tmp_path):
    report = validate(_kb(tmp_path, GOOD.replace("data=real", "data=invented")))
    assert report.passed is False
    assert any("invented" in f for f in report.failures)


def test_a_meta_line_missing_a_field_is_a_failure_line(tmp_path):
    broken = GOOD.replace(" | data=real", "")
    report = validate(_kb(tmp_path, broken))
    assert report.passed is False
    assert report.failures, "a corpus that will not parse must fail loudly"


# --- 4. statable effective dates -----------------------------------------

def test_a_not_yet_in_force_chunk_without_a_date_fails_the_gate(tmp_path):
    kb = _kb(tmp_path, (
        "### 4.6 Legislated future change\n"
        "*meta: doc=02-BOND | sec=4.6 | aud=all | type=tax_rule "
        "| data=real (not yet in force)*\n"
        "Savings rates rise at some point. No date stated anywhere.\n"
    ))
    report = validate(kb)
    assert report.passed is False
    assert any("02-BOND:4.6" in f for f in report.failures)


def test_a_not_yet_in_force_chunk_stating_its_date_passes(tmp_path):
    kb = _kb(tmp_path, (
        "### 4.6 Legislated future change\n"
        "*meta: doc=02-BOND | sec=4.6 | aud=all | type=tax_rule "
        "| data=real (not yet in force)*\n"
        "Finance Act 2026 raises savings rates from 6 April 2027 to 22%.\n"
    ), declared=1)
    assert validate(kb).passed is True


def test_a_date_in_the_heading_alone_is_enough(tmp_path):
    kb = _kb(tmp_path, (
        "### 4.6 Savings rates from 6 April 2027\n"
        "*meta: doc=02-BOND | sec=4.6 | aud=all | type=tax_rule "
        "| data=real (not yet in force)*\n"
        "Rates rise to 22/42/47%.\n"
    ), declared=1)
    assert validate(kb).passed is True


def test_an_in_force_chunk_needs_no_date(tmp_path):
    assert validate(_kb(tmp_path, GOOD, declared=1)).passed is True


def test_only_a_date_after_the_knowledge_base_date_counts(tmp_path):
    # The real savings-rate chunk cites its Royal Assent (18 March 2026) and the
    # Budget that announced it (26 November 2025). Neither tells a handler when
    # the rule bites, so "any date present" is not good enough.
    kb = _kb(tmp_path, (
        "### 4.6 Legislated future change\n"
        "*meta: doc=02-BOND | sec=4.6 | aud=all | type=tax_rule "
        "| data=real (not yet in force)*\n"
        "Finance Act 2026 (Royal Assent 18 March 2026; Autumn Budget "
        "26 November 2025) raises savings-income rates to 22/42/47%.\n"
    ), declared=1)

    report = validate(kb)

    assert report.passed is False
    assert any("02-BOND:4.6" in f for f in report.failures)


def test_the_commencement_date_may_omit_the_day(tmp_path):
    kb = _kb(tmp_path, (
        "### 14.3 The IHT change\n"
        "*meta: doc=03-PEN | sec=14.3 | aud=all | type=tax_rule "
        "| data=real (not yet in force)*\n"
        "From April 2027 unused pension funds fall within the estate for IHT.\n"
    ), declared=1)
    assert validate(kb).passed is True


def test_the_reference_date_is_the_corpus_date_not_the_wall_clock(tmp_path):
    # Injected, per the determinism rule: the same corpus must give the same
    # verdict whenever the gate runs.
    body = (
        "### 4.6 Future change\n"
        "*meta: doc=02-BOND | sec=4.6 | aud=all | type=tax_rule "
        "| data=real (not yet in force)*\n"
        "Rates change from 6 April 2027.\n"
    )
    kb = _kb(tmp_path, body, declared=1)

    # As at the real KB date, 2027 is still ahead → statable.
    assert validate(kb).passed is True
    # Wind the reference date past it and the same chunk no longer states a
    # future date — it is no longer a "not yet in force" rule at all.
    assert validate(kb, kb_date=date(2028, 1, 1)).passed is False


# --- 5. count reconciliation ---------------------------------------------


def test_a_declared_count_that_disagrees_with_reality_fails_the_gate(tmp_path):
    # This is the change-control gate: edit the corpus, update its own record.
    report = validate(_kb(tmp_path, GOOD, declared=423))
    assert report.passed is False
    assert any("423" in f and "1" in f for f in report.failures)


def test_a_matching_declared_count_passes(tmp_path):
    report = validate(_kb(tmp_path, GOOD, declared=1))
    assert report.passed is True
    assert report.chunk_count == 1


def test_a_readme_making_no_claim_is_not_itself_a_failure(tmp_path):
    # Absent a claim there is nothing to reconcile against; the other checks stand.
    report = validate(_kb(tmp_path, GOOD))
    assert report.declared_count is None
    assert report.passed is True
