"""v4 phase 4 · Task 2 — the identity gate, held inside the tool layer.

Split from ``tests/test_agent_tools_v4.py`` at the 300-line rule. That file
covers what the tools *do*; this one covers what they refuse to do.

The endpoints already refuse an unverified read (D-CL-052). This is the layer
beneath: a record tool reached by any other route refuses on its own account.
The guard is applied when the tool is **bound**, not inside the record
functions — ``src/casework/assembly.py`` calls those directly and is not part of
this phase, so their signatures must not move.
"""

from functools import partial

import pytest

from src.agent.tools.record_tools import (
    get_transaction_history,
    get_valuation,
    lookup_policy_record,
)
from src.agent.tools.registry import Tool
from src.agent.tools.schemas import tool_definition
from src.agent.tools.verification import VerificationRequired, verified
from src.identity.gate import VerificationGate
from src.records.seed import build_seed_book

CN = "CN-1000000001"
OTHER_CN = "CN-1000000002"
POLICY_NO = "LP-20419876"
BOND_NO = "HB-40582213"
AT = "2026-04-12T09:00:00"


def _passed(gate, book, *, cn_ref=CN, policy_no=POLICY_NO, at=AT):
    """Drive the real gate to a passed record, from the book's own data."""
    policy = book.get_policy(policy_no)
    party = book.get_party(policy.holder_party_id)
    return gate.confirm(
        cn_ref=cn_ref, policy_no=policy_no, party=party, policy=policy,
        ticked=("policy_no", "name_dob", "address_or_bank"),
        actor="handler_a", at=at)


# ── the gate, held a second time in the tool layer ───────────────────────

def _guarded_lookup(gate, book, *, cn_ref=CN):
    return verified(partial(lookup_policy_record, book), gate=gate, cn_ref=cn_ref)


def test_a_record_tool_refuses_without_a_verification_id():
    # Arrange
    book, gate = build_seed_book(), VerificationGate()
    tool = _guarded_lookup(gate, book)

    # Act / Assert
    with pytest.raises(VerificationRequired):
        tool(policy_no=POLICY_NO, verification_id="")


def test_a_record_tool_returns_the_record_for_a_live_verification():
    # Arrange
    book, gate = build_seed_book(), VerificationGate()
    record = _passed(gate, book)
    tool = _guarded_lookup(gate, book)

    # Act
    out = tool(policy_no=POLICY_NO, verification_id=record.verification_id)

    # Assert
    assert out["found"] is True
    assert out["current_value"] == "£46,210.00"


def test_a_verification_from_another_interaction_does_not_unlock_this_one():
    # verification_id is sequential (VR-000000001), so checking the id alone
    # would let one caller's live verification unlock another caller's request
    # for the same policy. Both the interaction and the policy must agree.
    # Arrange
    book, gate = build_seed_book(), VerificationGate()
    theirs = _passed(gate, book, cn_ref=OTHER_CN)
    tool = _guarded_lookup(gate, book, cn_ref=CN)

    # Act / Assert
    with pytest.raises(VerificationRequired):
        tool(policy_no=POLICY_NO, verification_id=theirs.verification_id)


def test_a_verification_for_another_policy_does_not_unlock_this_one():
    # Arrange
    book, gate = build_seed_book(), VerificationGate()
    bond = _passed(gate, book, policy_no=BOND_NO)
    tool = _guarded_lookup(gate, book)

    # Act / Assert
    with pytest.raises(VerificationRequired):
        tool(policy_no=POLICY_NO, verification_id=bond.verification_id)


def test_an_expired_verification_no_longer_unlocks():
    # AD-CL-029: the verification is spent when the interaction closes.
    # Arrange
    book, gate = build_seed_book(), VerificationGate()
    record = _passed(gate, book)
    gate.expire_for_interaction(CN, at="2026-04-12T10:00:00")
    tool = _guarded_lookup(gate, book)

    # Act / Assert
    with pytest.raises(VerificationRequired):
        tool(policy_no=POLICY_NO, verification_id=record.verification_id)


def test_an_invented_verification_id_is_refused():
    # Arrange
    book, gate = build_seed_book(), VerificationGate()
    _passed(gate, book)
    tool = _guarded_lookup(gate, book)

    # Act / Assert
    with pytest.raises(VerificationRequired):
        tool(policy_no=POLICY_NO, verification_id="VR-999999999")


def test_the_refusal_does_not_say_whether_the_policy_exists():
    # 07-RUNBOOK:4.1 — confirming existence is itself a disclosure.
    # Arrange
    book, gate = build_seed_book(), VerificationGate()
    tool = _guarded_lookup(gate, book)

    # Act
    with pytest.raises(VerificationRequired) as real:
        tool(policy_no=POLICY_NO, verification_id="")
    with pytest.raises(VerificationRequired) as invented:
        tool(policy_no="LP-00000000", verification_id="")

    # Assert — the same answer either way
    assert str(real.value).replace(POLICY_NO, "X") == \
        str(invented.value).replace("LP-00000000", "X")


# ── the guard and the derived schema agree ───────────────────────────────

def test_the_guard_puts_verification_id_into_the_derived_schema():
    # The model has to know to supply it, and task 1 derives that from the
    # signature — so the guard must present one, not hide behind **kwargs.
    # Arrange
    book, gate = build_seed_book(), VerificationGate()
    tool = Tool("lookup_policy_record", "look up a policy",
                _guarded_lookup(gate, book))

    # Act
    schema = tool_definition(tool)["input_schema"]

    # Assert
    assert set(schema["properties"]) == {"policy_no", "verification_id"}
    assert set(schema["required"]) == {"policy_no", "verification_id"}


def test_the_guard_still_hides_the_bound_store():
    # Arrange
    book, gate = build_seed_book(), VerificationGate()
    tool = Tool("lookup_policy_record", "d", _guarded_lookup(gate, book))

    # Act / Assert
    assert "store" not in tool_definition(tool)["input_schema"]["properties"]


def test_guarding_leaves_the_raw_function_alone():
    # src/casework/assembly.py calls this directly and is not in this phase.
    # Arrange
    book, gate = build_seed_book(), VerificationGate()
    verified(partial(lookup_policy_record, book), gate=gate, cn_ref=CN)

    # Act
    out = lookup_policy_record(book, POLICY_NO)

    # Assert
    assert out["found"] is True


def test_the_valuation_tool_is_guarded_too_and_keeps_its_as_at():
    # Arrange
    book, gate = build_seed_book(), VerificationGate()
    record = _passed(gate, book)
    tool = verified(partial(get_valuation, book), gate=gate, cn_ref=CN)

    # Act
    out = tool(policy_no=POLICY_NO, as_at="2026-04-12",
               verification_id=record.verification_id)

    # Assert
    assert out["value"] == "£46,210.00"


def test_the_history_tool_is_guarded_too():
    # Arrange
    book, gate = build_seed_book(), VerificationGate()
    record = _passed(gate, book)
    tool = verified(partial(get_transaction_history, book, as_at="2026-04-12"), gate=gate, cn_ref=CN)

    # Act
    out = tool(policy_no=POLICY_NO, verification_id=record.verification_id)

    # Assert
    assert out["found"] is True
