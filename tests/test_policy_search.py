"""D-CL-114 — the caller screen: find the policy, then see what the record holds.

Two surfaces, both staff-facing. **Search**: one box taking a policy number or
a policyholder name; a fragment of either finds the policy. **Present**: the
verification panel now carries the held details the handler ticks against, and
the policy's authority holders — a handler who cannot see the record cannot
judge a match, and one who cannot see the authorities cannot know who may
speak. The caller-facing rules survive unchanged and are tested with the gate.
"""

from fastapi.testclient import TestClient

from src.records.authorisations import AuthorityRecord
from src.records.models import AdviserLoa, Contact, Party, Policy, Trust
from src.records.store import InMemoryRecordBook
from src.web.console.app import create_console_app

AT = "2026-07-13T09:00:00"
SEED_POLICY = "LP-20419876"          # the seeded book's own demo record


def _client(book=None):
    return TestClient(create_console_app(secret="test-secret", book=book))


def _login(client, role="front_office"):
    assert client.post("/api/login", json={"role": role}).status_code == 200


def _search(client, q):
    return client.get("/api/policies/search", params={"q": q})


def _stock(party_id, name, policy_no, **policy_over):
    party = Party(party_id=party_id, name=name, dob="1961-04-02",
                  registered_address="3 Gable Court, Sampleton",
                  contact=Contact(phone="07700 900900",
                                  email=f"{party_id.lower()}@example.org",
                                  registered=True))
    policy = Policy(policy_no=policy_no, product="horizon_bond",
                    status="in_force", start_date="2019-03-01",
                    holder_party_id=party_id, **policy_over)
    return party, policy


def _book(entries):
    book = InMemoryRecordBook()
    for party, policy in entries:
        book.add_party(party, actor="test", source_ref="seed", at=AT)
        book.add_policy(policy, actor="test", source_ref="seed", at=AT)
    return book


# ── search: number or name, either finds the policy ──────────────────────
def test_a_full_policy_number_finds_its_policy_and_names_the_holder():
    c = _client()
    _login(c)
    body = _search(c, SEED_POLICY).json()
    assert body["total"] == 1
    assert body["matches"][0]["policy_no"] == SEED_POLICY
    assert body["matches"][0]["holder"] == "Theta Meridian 12"


def test_a_number_fragment_is_enough():
    c = _client()
    _login(c)
    matches = _search(c, "20419").json()["matches"]
    assert SEED_POLICY in [m["policy_no"] for m in matches]


def test_a_name_finds_the_policy_case_insensitively():
    c = _client()
    _login(c)
    for q in ("Theta Meridian", "theta meridian 12", "THETA"):
        matches = _search(c, q).json()["matches"]
        assert SEED_POLICY in [m["policy_no"] for m in matches], q


def test_a_single_character_searches_nothing():
    # One key-press matches half the book; answering it would be noise.
    c = _client()
    _login(c)
    assert _search(c, "t").json() == {"query": "t", "total": 0, "matches": []}


def test_no_match_is_an_empty_list_not_an_error():
    c = _client()
    _login(c)
    body = _search(c, "ZZ-00000000").json()
    assert body["total"] == 0 and body["matches"] == []


def test_the_list_is_capped_but_the_total_is_honest():
    entries = [_stock(f"PH-91{i:02d}", f"Quartz Delta {i}", f"HB-9100{i:04d}")
               for i in range(11)]
    c = _client(book=_book(entries))
    _login(c)
    body = _search(c, "Quartz Delta").json()
    assert body["total"] == 11
    assert len(body["matches"]) == 8


def test_search_needs_a_session_but_serves_every_desk():
    assert _search(_client(), "Theta").status_code == 401
    for role in ("front_office", "back_office", "ops"):
        c = _client()
        _login(c, role)
        assert _search(c, "Theta").status_code == 200, role


# ── present: the pre-filled panel ────────────────────────────────────────
def _present(client, policy_no=SEED_POLICY):
    cn = client.post("/api/interaction/open",
                     json={"policy_no": policy_no}).json()["cn_ref"]
    return client.post("/api/verify",
                       json={"cn_ref": cn, "policy_no": policy_no}).json()


def test_presenting_shows_the_handler_what_the_record_holds():
    c = _client()
    _login(c)
    body = _present(c)
    assert [chk["kind"] for chk in body["checks"]] == [
        "policy_no", "name_dob", "address_or_bank"]
    shown = " ".join(f["value"] for chk in body["checks"]
                     for f in chk["held"])
    for held in (SEED_POLICY, "Theta Meridian 12", "1954-02-11",
                 "14 Lattice Way", "4471"):
        assert held in shown


def test_presenting_names_the_policy_holder_and_every_authority_holder():
    party, policy = _stock("PH-9201", "Umber Sable 4", "HB-92000001",
                           bank_last4="7011",
                           trust=Trust(kind="discretionary",
                                       executed="2020-06-01",
                                       trustees=("PH-9202",)),
                           adviser_loa=AdviserLoa(firm="Harbourline Advice LLP",
                                                  frn="912345",
                                                  scope=("servicing",
                                                         "information"),
                                                  expiry="2027-01"))
    attorney = Party(party_id="PH-9202", name="Sable Umber 9",
                     dob="1958-11-23",
                     registered_address="9 Weir Lane, Sampleton",
                     contact=Contact(phone="07700 900901",
                                     email="ph-9202@example.org",
                                     registered=True))
    book = _book([(party, policy)])
    book.add_party(attorney, actor="test", source_ref="seed", at=AT)
    book.add_authority(AuthorityRecord(authority_id="AUTH-0001",
                                       policy_no=policy.policy_no,
                                       party_id="PH-9202", type="LPA",
                                       scope=("servicing", "information"),
                                       evidence_ref="OPG-77", status="active"),
                       actor="test", source_ref="seed", at=AT)
    c = _client(book=book)
    _login(c)
    body = _present(c, policy.policy_no)

    authorities = body["authorities"]
    assert authorities["holder"]["name"] == "Umber Sable 4"
    lpa = authorities["records"][0]
    assert (lpa["type"], lpa["name"], lpa["status"]) == (
        "LPA", "Sable Umber 9", "active")
    assert "servicing" in lpa["scope"]
    assert authorities["adviser"]["firm"] == "Harbourline Advice LLP"
    assert authorities["trust"]["trustees"] == ["Sable Umber 9"]


def test_a_policy_with_nobody_else_reports_empty_authorities_not_nothing():
    # A bare record — no authority, no LOA, no trust. (The seeded demo policy
    # is the wrong subject here: it carries an adviser LOA on purpose.)
    c = _client(book=_book([_stock("PH-9301", "Basalt Vermilion 2",
                                   "HB-93000001")]))
    _login(c)
    authorities = _present(c, "HB-93000001")["authorities"]
    assert authorities["records"] == []
    assert authorities["adviser"] is None
    assert authorities["trust"] is None


# ── the retired contract ─────────────────────────────────────────────────
def test_posting_typed_answers_is_refused_and_names_the_new_contract():
    c = _client()
    _login(c)
    cn = c.post("/api/interaction/open",
                json={"policy_no": SEED_POLICY}).json()["cn_ref"]
    r = c.post("/api/verify", json={
        "cn_ref": cn, "policy_no": SEED_POLICY,
        "answers": {"policy_no": SEED_POLICY}})
    assert r.status_code == 400
    assert "confirmed" in r.json()["detail"]
