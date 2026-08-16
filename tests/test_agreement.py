"""Phase 7 Task 3 (the math) — judge-vs-hand-label agreement.

Pure computation, fixture-tested — no client, no live calls. The published number
is only credible if it counts ONLY the points both the judge and the human graded,
and surfaces every disagreement rather than burying it.
"""

from src.evals.agreement import agreement


def _g(case_id, point_id, passed):
    return {"case_id": case_id, "point_id": point_id, "passed": passed}


def test_perfect_agreement_is_one():
    judge = [_g("c1", "R12", True), _g("c1", "R11", False)]
    hand = [_g("c1", "R12", True), _g("c1", "R11", False)]
    r = agreement(judge, hand)
    assert r.total == 2 and r.agreed == 2
    assert r.agreement == 1.0
    assert r.disagreements == []


def test_partial_agreement_lists_disagreements():
    judge = [_g("c1", "R12", True), _g("c1", "R8", True), _g("c2", "R12", False)]
    hand = [_g("c1", "R12", True), _g("c1", "R8", False), _g("c2", "R12", False)]
    r = agreement(judge, hand)
    assert r.total == 3 and r.agreed == 2
    assert r.agreement == 2 / 3
    assert len(r.disagreements) == 1
    d = r.disagreements[0]
    assert d["case_id"] == "c1" and d["point_id"] == "R8"
    assert d["judge"] is True and d["hand"] is False


def test_per_point_breakdown():
    judge = [_g("c1", "R12", True), _g("c2", "R12", False), _g("c1", "R8", True)]
    hand = [_g("c1", "R12", True), _g("c2", "R12", True), _g("c1", "R8", True)]
    r = agreement(judge, hand)
    assert r.per_point["R12"] == 0.5  # one of two R12 pairs agreed
    assert r.per_point["R8"] == 1.0


def test_only_pairs_graded_by_both_are_counted():
    # the human never graded (c2, R12); it must not inflate or deflate the score
    judge = [_g("c1", "R12", True), _g("c2", "R12", False)]
    hand = [_g("c1", "R12", True)]
    r = agreement(judge, hand)
    assert r.total == 1 and r.agreed == 1 and r.agreement == 1.0


def test_empty_is_zero_not_a_crash():
    r = agreement([], [])
    assert r.total == 0 and r.agreed == 0
    assert r.agreement == 0.0
    assert r.per_point == {} and r.disagreements == []
