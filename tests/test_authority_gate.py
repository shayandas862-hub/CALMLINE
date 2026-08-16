"""v4 phase 3 · task 3 — the third-party authority path (AD-CL-033).

`05-OPS:5.0` is the overarching rule and the shape of this module: authority
must be **verified**, *and* the request must fall **within the verified scope**.
Fail either and the specific instruction is refused, with an explanation of what
would make it acceptable and the customer-direct route offered. No partial
disclosure "to be helpful".

Two limits are **structural** — they hold whatever a scope tuple happens to
say, because they come from what the instrument *is*:

* an LOA does not authorise receiving claim/surrender proceeds or changing the
  customer's bank details (`05-OPS:5.1`);
* trusteeship is personal, so an attorney is not a trustee — replacement runs
  by deed under s.36 Trustee Act 1925 (`05-OPS:5.8`, `01-WOL:II.6.13`; this is
  eval case E22, whose recorded failure mode is "accepts attorney as trustee").

A scope tuple is data and can be typed wrong. These two cannot be, which is the
point of encoding them here rather than trusting the record.
"""

import pytest

from src.identity.authority import (
    AUTHORITY_ACTIONS,
    AUTHORITY_SOURCES,
    AuthorityDecision,
    authorise,
    resolve_authority,
)
from src.records.authorisations import AuthorityRecord

POLICY_NO = "HB-40582213"
PARTY_ID = "PH-2001"


def _authority(**over) -> AuthorityRecord:
    kw = dict(authority_id="AUTH-0001", policy_no=POLICY_NO, party_id=PARTY_ID,
              type="LOA", scope=("information", "servicing"),
              evidence_ref="LOA-2026-04-11", verified_date="2026-04-11",
              status="active")
    kw.update(over)
    return AuthorityRecord(**kw)


# ── the vocabulary and its sources ───────────────────────────────────────
def test_every_authority_type_names_the_chunk_that_governs_it():
    # AD-CL-028 — a rule held in code carries its source.
    assert AUTHORITY_SOURCES["LOA"] == "05-OPS:5.1"
    assert AUTHORITY_SOURCES["LPA"] == "05-OPS:5.2"
    assert AUTHORITY_SOURCES["EPA"] == "05-OPS:5.3"
    assert AUTHORITY_SOURCES["deputy"] == "05-OPS:5.4"
    assert AUTHORITY_SOURCES["PR"] == "05-OPS:5.5"
    assert AUTHORITY_SOURCES["mandate"] == "05-OPS:5.6"
    assert AUTHORITY_SOURCES["one_off"] == "05-OPS:5.6"
    assert AUTHORITY_SOURCES["trustee"] == "05-OPS:5.8"


def test_the_action_vocabulary_covers_what_a_third_party_can_ask_for():
    assert AUTHORITY_ACTIONS == frozenset({
        "information", "servicing", "switches", "withdrawals",
        "bank_change", "claim_proceeds", "trustee_change"})


def test_an_unknown_action_is_refused_rather_than_defaulted():
    with pytest.raises(ValueError):
        authorise(_authority(), action="borrow_the_car")


# ── resolving a claimed relationship to a record ─────────────────────────
def test_a_claimed_relationship_resolves_to_the_matching_record():
    records = (_authority(), _authority(authority_id="AUTH-0002", type="LPA",
                                        party_id="PH-2002"))
    found = resolve_authority(records, party_id="PH-2002", claimed="LPA")
    assert found is not None and found.authority_id == "AUTH-0002"


def test_a_claim_with_no_matching_record_resolves_to_nothing():
    assert resolve_authority((_authority(),), party_id="PH-9999",
                             claimed="LPA") is None


def test_claiming_a_different_instrument_than_the_one_held_resolves_to_nothing():
    # "I hold power of attorney" against a record that is only an adviser LOA.
    assert resolve_authority((_authority(),), party_id=PARTY_ID,
                             claimed="LPA") is None


# ── verified, and in scope (05-OPS:5.0) ──────────────────────────────────
def test_an_active_authority_acting_in_scope_is_allowed():
    decision = authorise(_authority(), action="information")
    assert isinstance(decision, AuthorityDecision)
    assert decision.allowed is True
    assert "05-OPS:5.0" in decision.sources


def test_no_authority_at_all_is_refused():
    decision = authorise(None, action="information")
    assert decision.allowed is False
    assert "05-OPS:5.7" in decision.sources


@pytest.mark.parametrize("status", ["unverified", "expired", "revoked"])
def test_an_authority_that_is_not_active_is_refused(status):
    decision = authorise(_authority(status=status), action="information")
    assert decision.allowed is False
    assert "05-OPS:5.7" in decision.sources


def test_an_action_outside_the_recorded_scope_is_refused():
    decision = authorise(_authority(scope=("information",)), action="switches")
    assert decision.allowed is False
    assert "05-OPS:5.0" in decision.sources


# ── the structural limits (they beat the scope tuple) ────────────────────
def test_an_loa_cannot_change_bank_details_even_if_the_scope_says_so():
    # 05-OPS:5.1 — the instrument does not confer it, so the record cannot
    # grant it by being typed generously.
    decision = authorise(_authority(scope=("information", "bank_change")),
                         action="bank_change")
    assert decision.allowed is False
    assert "05-OPS:5.1" in decision.sources


def test_an_loa_cannot_receive_proceeds_even_if_the_scope_says_so():
    decision = authorise(_authority(scope=("claim_proceeds",)),
                         action="claim_proceeds")
    assert decision.allowed is False
    assert "05-OPS:5.1" in decision.sources


def test_an_lpa_permits_an_instruction_the_loa_refuses_on_the_same_policy():
    # The phase's done criterion, stated directly (05-OPS:5.1 vs 5.2).
    loa = _authority(type="LOA", scope=("information", "bank_change"))
    lpa = _authority(authority_id="AUTH-0002", type="LPA",
                     scope=("information", "bank_change"))
    assert authorise(loa, action="bank_change").allowed is False
    assert authorise(lpa, action="bank_change").allowed is True


def test_an_attorney_is_not_a_trustee():
    # E22 — recorded failure mode: "accepts attorney as trustee".
    decision = authorise(_authority(type="LPA", scope=("trustee_change",)),
                         action="trustee_change")
    assert decision.allowed is False
    assert "05-OPS:5.8" in decision.sources
    assert "01-WOL:II.6.13" in decision.sources


@pytest.mark.parametrize("kind", ["LOA", "EPA", "deputy", "PR", "mandate", "one_off"])
def test_no_instrument_but_trusteeship_confers_a_trustee_change(kind):
    decision = authorise(_authority(type=kind, scope=("trustee_change",)),
                         action="trustee_change")
    assert decision.allowed is False


def test_an_actual_trustee_may_make_a_trustee_change():
    decision = authorise(_authority(type="trustee", scope=("trustee_change",)),
                         action="trustee_change")
    assert decision.allowed is True


# ── how a refusal reads (05-OPS:5.0 / 5.7) ───────────────────────────────
def test_a_refusal_explains_what_would_make_the_instruction_acceptable():
    decision = authorise(_authority(scope=("information",)), action="withdrawals")
    assert decision.remedy


def test_a_refusal_offers_the_customer_direct_route():
    decision = authorise(None, action="information")
    assert decision.customer_direct_route is True


def test_a_refusal_discloses_nothing_about_the_policy():
    # "No partial disclosure to be helpful" — a refusal must not become a
    # side channel for the data it is refusing.
    decision = authorise(_authority(scope=("information",)), action="withdrawals")
    rendered = " ".join(str(v) for v in (decision.reason, decision.remedy))
    assert POLICY_NO not in rendered


def test_a_refusal_names_the_authority_it_refused_so_it_can_be_logged():
    decision = authorise(_authority(), action="withdrawals")
    assert decision.authority_id == "AUTH-0001"


def test_every_decision_carries_at_least_one_source():
    for action in sorted(AUTHORITY_ACTIONS):
        decision = authorise(_authority(scope=tuple(AUTHORITY_ACTIONS)), action=action)
        assert decision.sources, f"{action} decided with no cited source"
