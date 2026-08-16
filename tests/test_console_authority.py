"""v4 phase 3 · task 6 — the third-party authority path through the console.

Split from `test_console_gate.py` at the 300-line rule; one job per file.

`05-OPS:5.1` verifies the **firm** and its **FRN** on the FCA Register, not a
named individual — and that is exactly what the corpus records: the anchors
carry an `adviser_LOA` naming a firm, an FRN, a scope and an expiry, with no
person attached. So an LOA claim resolves against the policy's own adviser
record rather than against an invented party (D-CL-050).
"""

from tests.test_console_gate import (
    POLICY_NO,
    _client,
    _front_office,
    _open_interaction,
)


def test_an_adviser_in_scope_is_allowed():
    # LP-20419876 carries Fairholm Financial Ltd, FRN 512345,
    # scope = servicing + information, expiring 2027-03.
    c = _client()
    _front_office(c)
    cn_ref = _open_interaction(c, claimed_relationship="LOA")
    body = c.post("/api/authority/check", json={
        "cn_ref": cn_ref, "policy_no": POLICY_NO, "claimed": "LOA",
        "firm": "Fairholm Financial Ltd", "frn": "512345",
        "action": "information"}).json()
    assert body["allowed"] is True
    assert "05-OPS:5.1" in body["sources"]


def test_an_adviser_out_of_scope_is_refused():
    # Withdrawals are not in this LOA's scope (05-OPS:5.0).
    c = _client()
    _front_office(c)
    cn_ref = _open_interaction(c, claimed_relationship="LOA")
    body = c.post("/api/authority/check", json={
        "cn_ref": cn_ref, "policy_no": POLICY_NO, "claimed": "LOA",
        "firm": "Fairholm Financial Ltd", "frn": "512345",
        "action": "withdrawals"}).json()
    assert body["allowed"] is False
    assert "05-OPS:5.0" in body["sources"]
    assert body["remedy"]


def test_an_adviser_is_refused_a_bank_change_whatever_the_scope():
    # 05-OPS:5.1 — structural. The bond's LOA even carries `withdrawals`.
    c = _client()
    _front_office(c)
    cn_ref = _open_interaction(c, policy_no="HB-40582213",
                              claimed_relationship="LOA")
    body = c.post("/api/authority/check", json={
        "cn_ref": cn_ref, "policy_no": "HB-40582213", "claimed": "LOA",
        "firm": "Brightwater IFA LLP", "frn": "618902",
        "action": "bank_change"}).json()
    assert body["allowed"] is False
    assert "05-OPS:5.1" in body["sources"]
    assert body["customer_direct_route"] is True


def test_a_wrong_frn_does_not_resolve_to_the_adviser():
    # The FRN is the check `05-OPS:5.1` actually names.
    c = _client()
    _front_office(c)
    cn_ref = _open_interaction(c, claimed_relationship="LOA")
    body = c.post("/api/authority/check", json={
        "cn_ref": cn_ref, "policy_no": POLICY_NO, "claimed": "LOA",
        "firm": "Fairholm Financial Ltd", "frn": "999999",
        "action": "information"}).json()
    assert body["allowed"] is False
    assert "05-OPS:5.7" in body["sources"]


def test_a_policy_with_no_adviser_refuses_an_loa_claim():
    # RA-77103428 has no adviser LOA at all.
    c = _client()
    _front_office(c)
    cn_ref = _open_interaction(c, policy_no="RA-77103428",
                              claimed_relationship="LOA")
    body = c.post("/api/authority/check", json={
        "cn_ref": cn_ref, "policy_no": "RA-77103428", "claimed": "LOA",
        "firm": "Anyone At All", "frn": "000000", "action": "information"}).json()
    assert body["allowed"] is False


def test_an_authority_check_needs_a_session():
    assert _client().post("/api/authority/check", json={
        "policy_no": POLICY_NO, "claimed": "LOA", "firm": "x", "frn": "1",
        "action": "information"}).status_code == 401
