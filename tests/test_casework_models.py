"""v4 phase 2 · task 4 — the Case on the KB's own grammar.

`CASE-0001` was a repo-native id. The KB defines `CW-` + 9 (`05-OPS:1.4`), and
the case now carries what the back office actually works from: what kind of
request it is, what authority level it needs, and the evidence attached to it.

Time is always computed against an injected ``now`` — the code never calls the
clock — so the SLA maths is deterministic in tests.
"""

import pytest

from src.casework.models import (
    CASE_TYPES,
    Case,
    EvidenceItem,
    priority_rank,
    sla_seconds_left,
)


def _case(**over) -> Case:
    kw = dict(case_id="CW-300218754", cw_ref="CW-300218754",
              policy_no="LP-20419876", request="Death claim")
    kw.update(over)
    return Case(**kw)


# ── defaults carried forward ─────────────────────────────────────────────
def test_case_has_sensible_defaults():
    case = _case()
    assert case.status == "pending_review"
    assert case.priority == "medium"
    assert case.checklist == []
    assert case.audit == []
    assert case.evidence == []
    assert case.proposed is None
    assert case.human_decision is None
    assert case.type == "servicing"
    assert case.authority_level_required is None


def test_priority_rank_orders_high_before_low():
    high = priority_rank(_case(priority="high"))
    medium = priority_rank(_case(priority="medium"))
    low = priority_rank(_case(priority="low"))
    assert high < medium < low


def test_sla_seconds_left_counts_down_against_now():
    case = _case(sla_due="2026-07-02T12:00:00")
    assert sla_seconds_left(case, "2026-07-02T10:00:00") == 7200   # two hours left
    assert sla_seconds_left(case, "2026-07-02T13:00:00") == -3600  # an hour overdue


def test_sla_seconds_left_is_none_without_a_due_time():
    assert sla_seconds_left(_case(), "2026-07-02T10:00:00") is None


# ── the CW- grammar ──────────────────────────────────────────────────────
def test_cw_ref_follows_the_kb_grammar():
    assert _case(cw_ref="CW-300218754").cw_ref == "CW-300218754"


@pytest.mark.parametrize("bad", [
    "CASE-0001",        # the Harbour & Vale relic
    "CW-30021875",      # eight digits
    "CW-3002187540",    # ten digits
    "cw-300218754",     # lowercase
    "CW300218754",      # no separator
])
def test_cw_ref_rejects_anything_else(bad):
    with pytest.raises(ValueError):
        _case(cw_ref=bad)


def test_a_case_may_exist_before_it_has_a_cw_ref():
    # The queue mints the reference; a case built without one is not an error.
    assert Case(case_id="tmp", policy_no="LP-20419876", request="x").cw_ref is None


# ── type and authority ───────────────────────────────────────────────────
@pytest.mark.parametrize("kind", sorted(CASE_TYPES))
def test_case_type_accepts_the_documented_vocabulary(kind):
    assert _case(type=kind).type == kind


def test_case_type_rejects_an_invented_kind():
    with pytest.raises(ValueError):
        _case(type="whatever_the_handler_typed")


def test_authority_level_required_is_carried_for_the_reviewer():
    # Compiled from the matrix (AD-CL-028); the full matrix lands in phase 3.
    assert _case(authority_level_required="band_2").authority_level_required == "band_2"


# ── evidence — "the things they have sent in" ────────────────────────────
def _evidence(**over) -> EvidenceItem:
    kw = dict(evidence_id="EV-0001", cw_ref="CW-300218754", policy_no="LP-20419876",
              requirement="Certified copy of the grant of probate",
              requirement_source="05-OPS:5.4", description="Grant, certified 2026-06-01",
              received_via="post", received_at="2026-06-14T09:00:00",
              taken_by="handler_a", satisfies="yes")
    kw.update(over)
    return EvidenceItem(**kw)


def test_evidence_item_records_what_was_supplied_and_which_rule_demanded_it():
    item = _evidence()
    assert item.requirement_source == "05-OPS:5.4"   # the KB rule, by chunk id
    assert item.received_via == "post"
    assert item.taken_by == "handler_a"
    assert item.satisfies == "yes"


@pytest.mark.parametrize("verdict", ["yes", "no", "unverifiable"])
def test_evidence_satisfies_is_a_closed_vocabulary(verdict):
    assert _evidence(satisfies=verdict).satisfies == verdict


def test_evidence_rejects_an_unknown_verdict_or_channel():
    with pytest.raises(ValueError):
        _evidence(satisfies="probably")
    with pytest.raises(ValueError):
        _evidence(received_via="carrier pigeon")


def test_evidence_hangs_off_a_case():
    case = _case(evidence=[_evidence()])
    assert case.evidence[0].evidence_id == "EV-0001"


def test_evidence_is_not_a_ledger_row():
    # Recording what someone sent in moves no money; the shape carries no amount.
    assert not any("pence" in field for field in vars(_evidence()))
