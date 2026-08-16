"""v4 phase 6 · Task 1 — the six-tier golden case.

`06-RAGOPS §3.0` defines the tiers: **R** retrieval/single-hop · **M** multi-hop
· **X** cross-document · **T** temporal · **G** guardrail/refusal · **O**
operational. Tier G is **binary** — a guardrail case passes or it does not, and
there is no partial credit for nearly refusing.

The rule that makes this set worth having: **every `expected_chunks` ref is
validated against the Phase 1 parser at load time.** A golden set naming chunks
the KB no longer contains is an exam marked against an answer sheet for a
different paper — it would keep scoring, and every score would be wrong. Evals
cannot rot.

Validation is strict and fail-loud, carried over from the v3 shape: a malformed
case raises rather than being skipped, because a dropped case quietly inflates
every rate computed over the set.
"""

import json

import pytest

from src.evals.golden import (GoldenValidationError, is_binary, kb_chunk_ids,
                              load_golden_set, validate_case)

KNOWN = {"01-WOL:3.10", "02-BOND:4.2", "03-PEN:4.3", "07-RUNBOOK:8.6"}


def _case(**over):
    case = {
        "id": "E01",
        "tier": "R",
        "question": "Grace period after a missed premium?",
        "answer_keys": ["30 days", "claim paid net of premium"],
        "expected_chunks": ["01-WOL:3.10"],
        "failure_watched": "wrong figure",
    }
    case.update(over)
    return case


def _write(tmp_path, cases, name="golden_evals.jsonl"):
    path = tmp_path / name
    path.write_text("\n".join(json.dumps(c) for c in cases) + "\n", encoding="utf-8")
    return path


# ── the shape ──────────────────────────────────────────────────────────

def test_a_well_formed_case_validates():
    validate_case(_case(), known_chunks=KNOWN)


def test_every_tier_in_the_kb_vocabulary_is_accepted():
    for tier in ("R", "M", "X", "T", "G", "O"):
        validate_case(_case(tier=tier), known_chunks=KNOWN)


def test_a_tier_outside_the_vocabulary_is_refused():
    with pytest.raises(GoldenValidationError):
        validate_case(_case(tier="S"), known_chunks=KNOWN)


def test_a_case_needs_a_question():
    with pytest.raises(GoldenValidationError):
        validate_case(_case(question=""), known_chunks=KNOWN)


def test_a_case_needs_at_least_one_answer_key():
    # Answer-key coverage is one of the three scores; a case with no keys would
    # score 100% for saying nothing.
    with pytest.raises(GoldenValidationError):
        validate_case(_case(answer_keys=[]), known_chunks=KNOWN)


def test_a_case_needs_at_least_one_expected_chunk():
    # recall@5 has nothing to measure against otherwise.
    with pytest.raises(GoldenValidationError):
        validate_case(_case(expected_chunks=[]), known_chunks=KNOWN)


def test_a_case_names_the_failure_it_watches_for():
    with pytest.raises(GoldenValidationError):
        validate_case(_case(failure_watched=""), known_chunks=KNOWN)


# ── evals cannot rot ───────────────────────────────────────────────────

def test_an_expected_chunk_the_kb_does_not_contain_is_refused():
    with pytest.raises(GoldenValidationError) as exc:
        validate_case(_case(expected_chunks=["02-BOND:9.9"]), known_chunks=KNOWN)
    assert "02-BOND:9.9" in str(exc.value)


def test_the_real_kb_is_what_the_refs_are_checked_against():
    # The default is the live parser, not a fixture — an injectable set keeps
    # the unit tests fast, but the default has to be the thing that can rot.
    ids = kb_chunk_ids()
    assert "01-WOL:3.10" in ids and "07-RUNBOOK:8.6" in ids
    validate_case(_case())


# ── Tier G is binary ───────────────────────────────────────────────────

def test_tier_g_is_binary_and_the_others_are_not():
    assert is_binary("G") is True
    for tier in ("R", "M", "X", "T", "O"):
        assert is_binary(tier) is False


# ── temporal cases carry their operative date ──────────────────────────

def test_a_temporal_case_may_carry_an_operative_date():
    case = _case(id="E24", tier="T", operative_date="2026-07-13")
    validate_case(case, known_chunks=KNOWN)
    assert case["operative_date"] == "2026-07-13"


def test_an_operative_date_that_is_not_a_date_is_refused():
    with pytest.raises(GoldenValidationError):
        validate_case(_case(operative_date="next April"), known_chunks=KNOWN)


# ── loading the set ────────────────────────────────────────────────────

def test_the_set_loads_from_one_jsonl_file(tmp_path):
    path = _write(tmp_path, [_case(), _case(id="E02", tier="M",
                                            expected_chunks=["02-BOND:4.2"])])
    cases = load_golden_set(path, known_chunks=KNOWN)
    assert [c["id"] for c in cases] == ["E01", "E02"]


def test_a_duplicate_id_is_refused(tmp_path):
    path = _write(tmp_path, [_case(), _case()])
    with pytest.raises(GoldenValidationError):
        load_golden_set(path, known_chunks=KNOWN)


def test_a_malformed_line_raises_rather_than_being_skipped(tmp_path):
    # A dropped case quietly inflates every rate computed over the set.
    path = tmp_path / "golden_evals.jsonl"
    path.write_text(json.dumps(_case()) + "\n{not json}\n", encoding="utf-8")
    with pytest.raises(GoldenValidationError):
        load_golden_set(path, known_chunks=KNOWN)


def test_blank_lines_are_not_cases(tmp_path):
    path = tmp_path / "golden_evals.jsonl"
    path.write_text(json.dumps(_case()) + "\n\n", encoding="utf-8")
    assert len(load_golden_set(path, known_chunks=KNOWN)) == 1


def test_a_case_that_fails_validation_names_itself(tmp_path):
    # The id in the message is what makes a 44-case failure actionable.
    path = _write(tmp_path, [_case(id="E07", tier="Z")])
    with pytest.raises(GoldenValidationError) as exc:
        load_golden_set(path, known_chunks=KNOWN)
    assert "E07" in str(exc.value)


def test_tier_counts_are_reported_for_the_loaded_set(tmp_path):
    # The KB's own tier totals are 9/9/6/4/8/8; the freeze and the per-tier
    # report both need this without re-deriving it.
    path = _write(tmp_path, [_case(), _case(id="E21", tier="G"),
                             _case(id="E22", tier="G")])
    from src.evals.golden import tier_counts
    assert tier_counts(load_golden_set(path, known_chunks=KNOWN)) == {"R": 1, "G": 2}
