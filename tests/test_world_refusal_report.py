"""The refusal report — what the world could not legally build, and why.

A refused movement stops its policy, and this is where it lands. The report is
the phase's evidence that nothing was quietly adjusted: a build that ends with
an empty report built every policy by the rules, and a build that does not says
exactly which policy, which day, which movement and which rule.

Kept separate from the engine's own tests because it is a separate module with
a separate job — the engine decides, this records.
"""

from __future__ import annotations

from datetime import date

from world.lifetimes.report import Refusal, RefusalReport

POLICY_NO = "HB-40000001"


def _refusal(policy_no=POLICY_NO, on=date(2020, 1, 1), kind="withdrawal",
             amount_pence=500, reason="would overdraw"):
    return Refusal(policy_no=policy_no, on=on, kind=kind,
                   amount_pence=amount_pence, reason=reason)


def test_a_new_report_is_empty():
    # Arrange / Act
    report = RefusalReport()

    # Assert
    assert report.is_empty()
    assert report.refusals == ()
    assert len(report) == 0


def test_a_refusal_names_the_policy_the_date_the_movement_and_the_reason():
    # Arrange
    report = RefusalReport()

    # Act
    report.record(_refusal())

    # Assert — all five, because a report you cannot act on is not a report
    (refusal,) = report.refusals
    assert refusal.policy_no == POLICY_NO
    assert refusal.on == date(2020, 1, 1)
    assert refusal.kind == "withdrawal"
    assert refusal.amount_pence == 500
    assert refusal.reason == "would overdraw"
    assert not report.is_empty()


def test_refusals_are_kept_in_the_order_they_happened():
    # Arrange
    report = RefusalReport()

    # Act
    for day in (1, 2, 3):
        report.record(_refusal(on=date(2020, 1, day)))

    # Assert
    assert [r.on.day for r in report.refusals] == [1, 2, 3]


def test_for_policy_selects_only_that_policys_refusals():
    # Arrange
    report = RefusalReport()
    for policy_no in (POLICY_NO, "LP-20000002", POLICY_NO):
        report.record(_refusal(policy_no=policy_no))

    # Act / Assert
    assert len(report.for_policy(POLICY_NO)) == 2
    assert len(report.for_policy("LP-20000002")) == 1
    assert report.for_policy("RA-70000003") == ()


def test_the_recorded_refusals_cannot_be_edited_through_the_handle():
    """The report is evidence. A caller holding the tuple cannot rewrite it."""
    # Arrange
    report = RefusalReport()
    report.record(_refusal())

    # Act / Assert — a tuple has no append, and the dataclass is frozen
    assert isinstance(report.refusals, tuple)


def test_a_report_renders_every_refusal_as_a_readable_line():
    """The build prints this. A reason nobody can read is not a reason."""
    # Arrange
    report = RefusalReport()
    report.record(_refusal(reason="would overdraw HB-40000001"))

    # Act
    rendered = report.render()

    # Assert
    assert POLICY_NO in rendered
    assert "2020-01-01" in rendered
    assert "withdrawal" in rendered
    assert "would overdraw" in rendered


def test_an_empty_report_renders_as_saying_so_rather_than_as_nothing():
    assert RefusalReport().render().strip() != ""
