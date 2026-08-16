"""v3 phase 3 · Tasks 4–5 — approval closes the maker-checker loop.

The agent PROPOSES (phase 2); only a human APPROVAL commits the proposal to the
ledger (phase 1). A do-not-proceed case cannot be approved, and no approval ever
happens without a human calling it.

**v4 phase 3** adds the two controls `07-RUNBOOK:4.3` keeps apart — *"four-eyes
tests correctness, dual authorisation tests authority"*. Four-eyes: the maker
cannot be the checker (E39). Dual authorisation: above £250,000 a second,
distinct approver is required (`05-OPS:14`). Both are only meaningful because
the session now names an actor (D-CL-045).
"""

import pytest

from src.agent.tools.case_tools import raise_case, run_compliance_check
from src.agent.tools.money_tools import record_transaction
from src.casework.approval import ApprovalError, approve_case
from src.casework.queue import CaseQueue
from src.records.models import Contact, Party, Policy, Transaction, gbp
from src.records.seed import build_seed_book
from src.records.store import InMemoryRecordBook

BIG_AT = "2020-01-01T00:00:00"


def _big_book() -> InMemoryRecordBook:
    """A bond sitting on £600,000, so a £300,000 movement is fundable.

    The seeded book's largest policy is £212,400, and an overdraw is refused by
    the ledger long before any band check runs — so the dual-authorisation
    threshold needs a book built for it.
    """
    book = InMemoryRecordBook()
    book.add_party(Party(party_id="PH-9001", name="Argon Basalt 27",
                         dob="1962-09-30", registered_address="8 Cornice Row",
                         contact=Contact(phone="07700 900456",
                                         email="ph-9001@example.org")),
                   actor="seed", source_ref="seed", at=BIG_AT)
    book.add_policy(Policy(policy_no="HB-99000001", product="horizon_bond",
                           status="in_force", start_date="2020-01-01",
                           holder_party_id="PH-9001"),
                    actor="seed", source_ref="seed", at=BIG_AT)
    book.apply_transaction("HB-99000001", Transaction(
        txn_id="TXN-OPEN", policy_no="HB-99000001", kind="opening",
        amount_pence=gbp(600_000), reason="opening value", actor="seed",
        at=BIG_AT))
    return book


def _big_case(queue: CaseQueue, amount_pence: int, *, maker="handler_a"):
    """A prepared, proceed-recommended case for the big bond."""
    case = raise_case(queue.open, policy_no="HB-99000001",
                      request="partial surrender", priority="high")
    proposed = record_transaction(policy_no="HB-99000001", kind="withdrawal",
                                  amount_pence=amount_pence, reason="customer request",
                                  actor=maker, at="2026-07-02T14:00:00")
    check = run_compliance_check([
        {"requirement": "Policy in force", "clause_ref": "02-BOND:4.2",
         "verdict": "pass"}])
    queue.attach_precheck(case.case_id, checklist=check["checklist"],
                          recommendation=check["recommendation"], proposed=proposed)
    return case


def _prepared_case(recommendation="proceed", with_proposal=True):
    book = build_seed_book()  # LP-20419876 sits at £46,210
    q = CaseQueue()
    case = raise_case(q.open, policy_no="LP-20419876", request="withdrawal £5,000", priority="high")
    proposed = None
    if with_proposal:
        proposed = record_transaction(policy_no="LP-20419876", kind="withdrawal",
                                      amount_pence=gbp(5_000), reason="customer request",
                                      actor="agent", at="2026-07-02T14:00:00")
    check = run_compliance_check([
        {"requirement": "Policy in force", "clause_ref": "WL-1.2", "verdict":
         "pass" if recommendation == "proceed" else "fail"},
    ])
    q.attach_precheck(case.case_id, checklist=check["checklist"],
                      recommendation=check["recommendation"], proposed=proposed)
    return q, book, case


def test_approving_a_proceed_case_commits_the_movement_to_the_ledger():
    q, book, case = _prepared_case()
    approved = approve_case(q, book, case.case_id, reviewer="Reviewer B",
                            at="2026-07-02T15:00:00", txn_id="TXN-9")
    assert book.current_value("LP-20419876") == gbp(41_210)  # £46,210 − £5,000, committed
    assert approved.status == "completed"
    assert approved.human_decision == "approved"
    assert any(e["event"] == "committed_to_ledger" for e in approved.audit)


def test_a_do_not_proceed_case_cannot_be_approved_and_nothing_moves():
    q, book, case = _prepared_case(recommendation="do_not_proceed")
    with pytest.raises(ApprovalError):
        approve_case(q, book, case.case_id, reviewer="Reviewer B",
                     at="2026-07-02T15:00:00", txn_id="TXN-9")
    assert book.current_value("LP-20419876") == gbp(46_210)  # untouched


def test_a_case_cannot_be_approved_twice():
    q, book, case = _prepared_case()
    approve_case(q, book, case.case_id, reviewer="R", at="2026-07-02T15:00:00", txn_id="TXN-9")
    with pytest.raises(ApprovalError):
        approve_case(q, book, case.case_id, reviewer="R", at="2026-07-02T15:05:00", txn_id="TXN-10")


def test_approving_a_case_with_no_proposal_completes_without_a_ledger_write():
    q, book, case = _prepared_case(with_proposal=False)
    approved = approve_case(q, book, case.case_id, reviewer="R",
                            at="2026-07-02T15:00:00", txn_id="TXN-9")
    assert approved.status == "completed"
    assert book.current_value("LP-20419876") == gbp(46_210)  # nothing to move


# ── the band ceiling (05-OPS:14 / the product II.13 ladders) ─────────────
def test_a_back_office_reviewer_may_approve_inside_its_band():
    q, book, case = _prepared_case()          # £5,000, bottom band
    approved = approve_case(q, book, case.case_id, reviewer="reviewer_kim",
                            at="2026-07-02T15:00:00", txn_id="TXN-9",
                            role="back_office")
    assert approved.status == "completed"


def test_a_back_office_reviewer_may_not_approve_above_its_band():
    # £60,000 is the team-manager band for a bond withdrawal (02-BOND:II.13).
    q, book = CaseQueue(), _big_book()
    case = _big_case(q, gbp(60_000))
    with pytest.raises(ApprovalError):
        approve_case(q, book, case.case_id, reviewer="reviewer_kim",
                     at="2026-07-02T15:00:00", txn_id="TXN-9", role="back_office")
    assert book.current_value("HB-99000001") == gbp(600_000)   # nothing moved


def test_a_front_office_session_can_never_approve():
    q, book, case = _prepared_case()
    with pytest.raises(ApprovalError):
        approve_case(q, book, case.case_id, reviewer="handler_a",
                     at="2026-07-02T15:00:00", txn_id="TXN-9", role="front_office")


def test_an_ops_session_can_never_approve():
    q, book, case = _prepared_case()
    with pytest.raises(ApprovalError):
        approve_case(q, book, case.case_id, reviewer="overseer",
                     at="2026-07-02T15:00:00", txn_id="TXN-9", role="ops")


def test_the_refusal_names_the_band_that_would_be_needed():
    q, book = CaseQueue(), _big_book()
    case = _big_case(q, gbp(60_000))
    with pytest.raises(ApprovalError, match="team_manager"):
        approve_case(q, book, case.case_id, reviewer="reviewer_kim",
                     at="2026-07-02T15:00:00", txn_id="TXN-9", role="back_office")


# ── four-eyes: the maker cannot be the checker (E39) ─────────────────────
def test_the_proposer_cannot_approve_their_own_case():
    q, book = CaseQueue(), _big_book()
    case = _big_case(q, gbp(5_000), maker="reviewer_kim")
    with pytest.raises(ApprovalError, match="maker"):
        approve_case(q, book, case.case_id, reviewer="reviewer_kim",
                     at="2026-07-02T15:00:00", txn_id="TXN-9", role="back_office")
    assert book.current_value("HB-99000001") == gbp(600_000)   # nothing moved


def test_a_different_checker_may_approve_the_same_case():
    q, book = CaseQueue(), _big_book()
    case = _big_case(q, gbp(5_000), maker="handler_a")
    approved = approve_case(q, book, case.case_id, reviewer="reviewer_kim",
                            at="2026-07-02T15:00:00", txn_id="TXN-9",
                            role="back_office")
    assert approved.status == "completed"


def test_the_case_records_maker_and_checker():
    # 07-RUNBOOK:4.3 — "sign-off is recorded with maker_id and checker_id".
    q, book = CaseQueue(), _big_book()
    case = _big_case(q, gbp(5_000), maker="handler_a")
    approved = approve_case(q, book, case.case_id, reviewer="reviewer_kim",
                            at="2026-07-02T15:00:00", txn_id="TXN-9",
                            role="back_office")
    assert approved.maker_id == "handler_a"
    assert approved.checker_id == "reviewer_kim"


# ── dual authorisation above £250,000 (05-OPS:14) ────────────────────────
def test_a_big_commit_does_not_move_on_the_first_approval():
    q, book = CaseQueue(), _big_book()
    case = _big_case(q, gbp(300_000))
    first = approve_case(q, book, case.case_id, reviewer="reviewer_kim",
                         at="2026-07-02T15:00:00", txn_id="TXN-9",
                         role="senior_manager")
    assert first.requires_second_approver is True
    assert first.status == "pending_review"          # still open
    assert book.current_value("HB-99000001") == gbp(600_000)   # nothing moved


def test_the_same_approver_cannot_be_the_second_approver():
    q, book = CaseQueue(), _big_book()
    case = _big_case(q, gbp(300_000))
    approve_case(q, book, case.case_id, reviewer="reviewer_kim",
                 at="2026-07-02T15:00:00", txn_id="TXN-9", role="senior_manager")
    with pytest.raises(ApprovalError, match="distinct"):
        approve_case(q, book, case.case_id, reviewer="reviewer_kim",
                     at="2026-07-02T15:05:00", txn_id="TXN-10",
                     role="senior_manager")
    assert book.current_value("HB-99000001") == gbp(600_000)   # still nothing


def test_a_second_distinct_approver_commits_the_big_movement():
    q, book = CaseQueue(), _big_book()
    case = _big_case(q, gbp(300_000))
    approve_case(q, book, case.case_id, reviewer="reviewer_kim",
                 at="2026-07-02T15:00:00", txn_id="TXN-9", role="senior_manager")
    done = approve_case(q, book, case.case_id, reviewer="reviewer_sam",
                        at="2026-07-02T15:05:00", txn_id="TXN-10",
                        role="senior_manager")
    assert done.status == "completed"
    assert done.second_approver_id == "reviewer_sam"
    assert book.current_value("HB-99000001") == gbp(300_000)   # £600k − £300k


def test_a_commit_at_the_threshold_needs_only_one_approver():
    # "above £250,000" — £250,000 itself is not above it.
    q, book = CaseQueue(), _big_book()
    case = _big_case(q, gbp(250_000))
    done = approve_case(q, book, case.case_id, reviewer="reviewer_kim",
                        at="2026-07-02T15:00:00", txn_id="TXN-9",
                        role="senior_manager")
    assert done.status == "completed"
    assert book.current_value("HB-99000001") == gbp(350_000)
