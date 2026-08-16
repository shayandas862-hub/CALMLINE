"""v4 phase 2 · task 1 — the reshaped system-of-record core shapes.

`Party` replaces v3's `Policyholder`; `Policy` is slimmed to what every product
shares, with per-product detail moving to `src/records/products.py`. Policy
numbers carry the KB's three per-product grammars (`05-OPS:1.4`), validated at
construction. Money is integer PENCE everywhere so the arithmetic is exact.
"""

import pytest

from src.records.models import (
    CREDIT_KINDS,
    DEBIT_KINDS,
    AdviserLoa,
    Contact,
    IdVerification,
    LedgerEntry,
    LifeAssured,
    Party,
    Policy,
    Transaction,
    Trust,
    VulnerabilityFlag,
    format_gbp,
    gbp,
)


def _party(**over) -> Party:
    kw = dict(
        party_id="PH-1001",
        name="Theta Meridian 12",
        dob="1954-02-11",
        registered_address="14 Lattice Way, Demoford",
        contact=Contact(phone="07700 900819", email="ph-1001@example.org", registered=True),
    )
    kw.update(over)
    return Party(**kw)


def _policy(**over) -> Policy:
    kw = dict(
        policy_no="LP-20419876",
        product="lifelong_protection",
        status="in_force",
        start_date="2016-05-01",
        holder_party_id="PH-1001",
    )
    kw.update(over)
    return Policy(**kw)


# ── money helpers ────────────────────────────────────────────────────────
def test_gbp_converts_pounds_to_pence():
    # Arrange / Act
    pence = gbp(50_000)
    # Assert
    assert pence == 5_000_000


def test_format_gbp_renders_pence_as_pounds():
    assert format_gbp(3_000_000) == "£30,000.00"
    assert format_gbp(0) == "£0.00"
    assert format_gbp(4_250) == "£42.50"


# ── Party (was Policyholder) ─────────────────────────────────────────────
def test_party_carries_the_data_dictionary_fields():
    party = _party()
    assert party.party_id == "PH-1001"
    assert party.dob == "1954-02-11"          # real-shaped, not v3's 0000-05-05
    assert party.contact.phone == "07700 900819"
    assert party.contact.registered is True
    assert party.scottish_taxpayer is False   # drives S-code PAYE answers on RA
    assert party.vulnerability_flag is None
    assert party.id_verified_level is None


def test_party_holds_a_vulnerability_flag_as_the_minimum_needed():
    # Special-category care: a reference and a category, never free-text detail.
    party = _party(vulnerability_flag=VulnerabilityFlag(
        support_needs_ref="SN-1001", category="health"))
    assert party.vulnerability_flag.support_needs_ref == "SN-1001"
    assert party.vulnerability_flag.category == "health"


def test_party_id_verification_is_a_cached_snapshot_with_a_timestamp():
    party = _party(id_verified_level=IdVerification(level="EV", at="2026-06-14T10:00:00"))
    assert party.id_verified_level.level == "EV"
    assert party.id_verified_level.at == "2026-06-14T10:00:00"


def test_party_rejects_an_unknown_verification_level():
    with pytest.raises(ValueError):
        _party(id_verified_level=IdVerification(level="probably", at="2026-06-14T10:00:00"))


def test_party_id_follows_the_internal_grammar():
    with pytest.raises(ValueError):
        _party(party_id="1001")


# ── Policy — the three product grammars ──────────────────────────────────
@pytest.mark.parametrize("policy_no", ["LP-20419876", "HB-40582213", "RA-77103428"])
def test_policy_accepts_each_product_prefix(policy_no):
    product = {"LP": "lifelong_protection", "HB": "horizon_bond",
               "RA": "retirement_account"}[policy_no[:2]]
    assert _policy(policy_no=policy_no, product=product).policy_no == policy_no


@pytest.mark.parametrize("bad", [
    "WL-88213",        # a Harbour & Vale relic — the wrong prefix and too short
    "TL-55090",
    "LP-2041987",      # seven digits
    "LP-204198765",    # nine digits
    "lp-20419876",     # lowercase
    "LP20419876",      # no separator
])
def test_policy_rejects_anything_outside_the_kb_grammar(bad):
    with pytest.raises(ValueError):
        _policy(policy_no=bad)


def test_policy_rejects_an_unknown_product():
    with pytest.raises(ValueError):
        _policy(product="Whole of Life")   # v3's free text is no longer a product


def test_policy_number_prefix_must_agree_with_the_product():
    # The prefix IS the product marker (05-OPS:1.4) — a bond numbered LP- is a
    # data error, not a presentation choice.
    with pytest.raises(ValueError):
        _policy(policy_no="LP-20419876", product="horizon_bond")


def test_policy_rejects_an_unknown_status():
    with pytest.raises(ValueError):
        _policy(status="active")           # the dictionary vocabulary is snake_case


@pytest.mark.parametrize("status", ["in_force", "lapsed", "paid_up", "claimed", "surrendered"])
def test_policy_accepts_the_dictionary_statuses(status):
    assert _policy(status=status).status == status


def test_policy_no_longer_carries_product_specific_money_fields():
    # These moved to CoverComponent; has_cash_value became can_pay_cash_out().
    policy = _policy()
    for gone in ("sum_assured_pence", "premium_pence", "has_cash_value", "holder_id"):
        assert not hasattr(policy, gone), f"{gone} should have moved off Policy"


# ── Policy — lives assured, trust, adviser authority ─────────────────────
def test_policy_defaults_to_a_single_life():
    assert _policy().lives_assured_basis == "single"


def test_policy_records_a_joint_last_survivor_basis():
    policy = _policy(
        policy_no="HB-40582213", product="horizon_bond",
        lives_assured=(LifeAssured(name="Argon Basalt 27", party_id="PH-1002"),
                       LifeAssured(name="Xenon Basalt 63", party_id=None)),
        lives_assured_basis="joint_last_survivor")
    assert len(policy.lives_assured) == 2
    assert policy.lives_assured[1].party_id is None


def test_policy_rejects_an_unknown_lives_basis():
    with pytest.raises(ValueError):
        _policy(lives_assured_basis="joint_first_death")


def test_policy_carries_a_trust_with_its_execution_details():
    policy = _policy(trust=Trust(kind="discretionary", executed="2016-05-01",
                                 trustees=("Theta Meridian 12", "Delta Meridian 41"),
                                 registrable=True, urn=None))
    assert policy.trust.kind == "discretionary"
    assert len(policy.trust.trustees) == 2
    assert policy.trust.urn is None


def test_adviser_loa_scope_is_a_closed_vocabulary():
    loa = AdviserLoa(firm="Fairholm Financial Ltd", frn="512345",
                     scope=("servicing", "information"), expiry="2027-03-31")
    assert "withdrawals" not in loa.scope     # an information LOA cannot instruct money
    with pytest.raises(ValueError):
        AdviserLoa(firm="x", frn="1", scope=("anything_it_likes",), expiry="2027-03-31")


def test_policy_bank_last4_is_four_digits_for_display_only():
    assert _policy(bank_last4="4471").bank_last4 == "4471"
    with pytest.raises(ValueError):
        _policy(bank_last4="71")


# ── Transaction — the kind vocabulary grows per product ──────────────────
def test_transaction_amount_is_a_positive_magnitude():
    txn = Transaction(txn_id="TXN-1", policy_no="HB-40582213", kind="regular_withdrawal",
                      amount_pence=gbp(6_000), reason="annual 5% withdrawal",
                      actor="Reviewer B", at="2026-07-02T10:00:00")
    assert txn.amount_pence == 600_000        # magnitude, not signed
    assert txn.signed_pence == -600_000       # the kind decides the direction


def test_transaction_rejects_negative_amount():
    with pytest.raises(ValueError):
        Transaction(txn_id="TXN-2", policy_no="LP-20419876", kind="withdrawal",
                    amount_pence=-1, reason="bad", actor="x", at="2026-07-02T10:00:00")


def test_transaction_rejects_unknown_kind():
    with pytest.raises(ValueError):
        Transaction(txn_id="TXN-3", policy_no="LP-20419876", kind="teleport",
                    amount_pence=1, reason="?", actor="x", at="2026-07-02T10:00:00")


@pytest.mark.parametrize("kind", ["contribution", "transfer_in"])
def test_new_product_credit_kinds_are_known(kind):
    assert kind in CREDIT_KINDS


@pytest.mark.parametrize("kind", ["regular_withdrawal", "segment_surrender", "ufpls_payment"])
def test_new_product_debit_kinds_are_known(kind):
    assert kind in DEBIT_KINDS


def test_known_kinds_split_into_credits_and_debits():
    assert "opening" in CREDIT_KINDS and "premium" in CREDIT_KINDS
    assert "withdrawal" in DEBIT_KINDS and "payout" in DEBIT_KINDS
    assert CREDIT_KINDS.isdisjoint(DEBIT_KINDS)


# ── what happens to a policy between the phone calls (v4.5 phase 1) ──────
@pytest.mark.parametrize("kind", ["investment_return", "bonus"])
def test_world_credit_kinds_are_known(kind):
    assert kind in CREDIT_KINDS


@pytest.mark.parametrize("kind", ["investment_loss", "charge"])
def test_world_debit_kinds_are_known(kind):
    assert kind in DEBIT_KINDS


def test_what_the_fund_did_is_two_named_kinds_not_one_signed_amount():
    # A fund can fall as well as rise, and the fall is a movement in its own
    # right — named, not a generic `debit_adjustment`. `amount_pence` stays a
    # magnitude and the kind carries the direction, as every other movement
    # does, so the money guard and the ledger fold are untouched.
    gain = Transaction(txn_id="TXN-G", policy_no="HB-40582213",
                       kind="investment_return", amount_pence=gbp(20_000),
                       reason="fund growth", actor="seed", at="2020-04-01T00:00:00")
    loss = Transaction(txn_id="TXN-L", policy_no="HB-40582213",
                       kind="investment_loss", amount_pence=gbp(5_000),
                       reason="fund fall", actor="seed", at="2021-04-01T00:00:00")
    assert gain.signed_pence == gbp(20_000) and not gain.is_debit
    assert loss.signed_pence == -gbp(5_000) and loss.is_debit


# ── LedgerEntry ──────────────────────────────────────────────────────────
def test_ledger_entry_records_transaction_and_resulting_balance():
    txn = Transaction(txn_id="TXN-1", policy_no="HB-40582213", kind="regular_withdrawal",
                      amount_pence=gbp(6_000), reason="annual 5% withdrawal",
                      actor="Reviewer B", at="2026-07-02T10:00:00")
    entry = LedgerEntry(seq=2, transaction=txn, balance_after_pence=gbp(30_000))
    assert entry.seq == 2
    assert entry.transaction is txn
    assert entry.balance_after_pence == 3_000_000
