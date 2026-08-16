"""v4 phase 6 · Task 2 — the golden set is REGENERATED from the KB.

`golden_evals.jsonl` was never delivered, but all 44 cases are fully specified
in `06-RAGOPS §3.1–3.6`. So the set is derived from the corpus rather than
typed out beside it: the script is what makes the committed file reproducible,
and what stops the exam paper and the syllabus drifting apart.

These tests run against the **real KB document**, not a fixture. A generator
tested only on a fixture proves it can parse a table someone wrote for it.
"""

import json

import pytest

from scripts.build_golden_from_kb import build_cases, render_jsonl
from src.evals.golden import load_golden_set, tier_counts, validate_case

# `06-RAGOPS §3.0` — the tier totals the KB's own tables carry.
EXPECTED_TIERS = {"R": 9, "M": 9, "X": 6, "T": 4, "G": 8, "O": 8}


@pytest.fixture(scope="module")
def cases():
    return build_cases()


# ── the set is complete ────────────────────────────────────────────────

def test_all_forty_four_cases_are_generated(cases):
    assert len(cases) == 44


def test_the_tier_counts_match_the_kb_tables(cases):
    assert tier_counts(cases) == EXPECTED_TIERS


def test_every_case_id_is_unique_and_shaped_like_the_kb(cases):
    ids = [c["id"] for c in cases]
    assert len(set(ids)) == 44
    assert all(i.startswith("E") and i[1:].isdigit() for i in ids)


def test_every_case_from_e01_to_e44_is_present(cases):
    assert {c["id"] for c in cases} == {f"E{n:02d}" for n in range(1, 45)}


# ── every generated case is a valid golden case ────────────────────────

def test_every_generated_case_passes_validation_against_the_live_kb(cases):
    # The generator and the validator meet here: if a table names a chunk the
    # parser does not produce, this is where it surfaces — at build time,
    # rather than as a silently-wrong score months later.
    for case in cases:
        validate_case(case)


# ── the rows are read faithfully ───────────────────────────────────────

def _by_id(cases, case_id):
    return next(c for c in cases if c["id"] == case_id)


def test_a_tier_r_row_is_read_column_for_column(cases):
    e01 = _by_id(cases, "E01")
    assert e01["tier"] == "R"
    assert e01["question"] == "Grace period after a missed premium?"
    assert e01["answer_keys"] == ["30 days", "claim paid net of premium"]
    assert e01["expected_chunks"] == ["01-WOL:3.10"]
    assert e01["failure_watched"] == "wrong figure"


def test_a_row_with_several_expected_chunks_splits_them(cases):
    assert _by_id(cases, "E03")["expected_chunks"] == ["03-PEN:4.3", "03-PEN:9.1"]


def test_a_guardrail_row_maps_prompt_and_required_behaviour(cases):
    # Tier G's table uses different column HEADINGS (Prompt / Required
    # behaviour) for the same positions. Read positionally, not by name.
    e23 = _by_id(cases, "E23")
    assert e23["tier"] == "G"
    assert "sanctions check" in e23["question"]
    assert e23["answer_keys"][0].startswith("refuse")
    assert e23["expected_chunks"] == ["05-OPS:13.3"]


def test_the_tier_g_cases_are_the_binary_ones(cases):
    from src.evals.golden import is_binary
    assert sum(1 for c in cases if is_binary(c["tier"])) == 8


# ── temporal cases ─────────────────────────────────────────────────────

def test_the_one_case_whose_table_states_when_it_was_asked_carries_that_date(cases):
    # E24's question says "(asked 13 Jul 2026)". That is the only asked-at date
    # the KB states, and it is the only one generated — see D-CL-078.
    assert _by_id(cases, "E24")["operative_date"] == "2026-07-13"


def test_no_other_case_invents_an_operative_date(cases):
    dated = [c["id"] for c in cases if c.get("operative_date")]
    assert dated == ["E24"]


def test_the_asked_at_marker_is_stripped_from_the_question(cases):
    # The date is structure now; leaving it in the prose too would ask the
    # agent to reconcile two sources of the same fact.
    assert "asked 13 Jul 2026" not in _by_id(cases, "E24")["question"]


# ── the committed artefact ─────────────────────────────────────────────

def test_the_rendered_file_round_trips_through_the_loader(tmp_path, cases):
    path = tmp_path / "golden_evals.jsonl"
    path.write_text(render_jsonl(cases), encoding="utf-8")
    assert len(load_golden_set(path)) == 44


def test_the_rendering_is_deterministic(cases):
    assert render_jsonl(cases) == render_jsonl(build_cases())


def test_one_case_per_line_and_no_trailing_blank(cases):
    body = render_jsonl(cases)
    lines = body.splitlines()
    assert len(lines) == 44
    assert body.endswith("\n") and not body.endswith("\n\n")
    assert all(json.loads(line)["id"] for line in lines)


def test_the_committed_set_matches_what_the_script_generates():
    # The artefact is committed AND reproducible. If the KB changes and nobody
    # re-runs the script, this is what says so.
    from scripts.build_golden_from_kb import GOLDEN_PATH
    assert GOLDEN_PATH.exists(), "run scripts/build_golden_from_kb.py"
    assert GOLDEN_PATH.read_text(encoding="utf-8") == render_jsonl(build_cases())
