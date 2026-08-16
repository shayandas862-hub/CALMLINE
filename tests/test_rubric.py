"""The rubric is an artifact with a contract: every point is tagged and cited.

Guards against a rubric point drifting in without a programmatic/qualitative
tag or without a public FCA source — which would make it unscoreable or
unverifiable.
"""

import re
from pathlib import Path

RUBRIC = Path(__file__).resolve().parent.parent / "rubric" / "rubric.md"


def rubric_points() -> list[str]:
    """Each rubric point is a bold line like '**R6 — … `[P]`**'."""
    text = RUBRIC.read_text(encoding="utf-8")
    return re.findall(r"\*\*R\d+ —[^\n]*\*\*", text)


def test_rubric_exists_and_has_enough_points():
    assert RUBRIC.exists()
    assert len(rubric_points()) >= 12, "rubric must have at least 12 checkable points"


def test_every_point_is_tagged_programmatic_or_qualitative():
    for point in rubric_points():
        assert "`[P]`" in point or "`[Q]`" in point, f"untagged rubric point: {point}"


def test_headline_metric_is_safety_accuracy():
    text = RUBRIC.read_text(encoding="utf-8").lower()
    assert "safety accuracy" in text


def test_cites_public_fca_sources():
    text = RUBRIC.read_text(encoding="utf-8")
    assert "FG21/1" in text, "must cite the vulnerable-customers guidance"
    assert "PRIN 2A" in text, "must cite Consumer Duty"
    assert "fca.org.uk" in text, "must link the public source"


def test_covers_both_case_types():
    text = RUBRIC.read_text(encoding="utf-8").lower()
    # call-side and action-side coverage both present
    assert "refus" in text and "recommendation" in text and "checklist" in text
