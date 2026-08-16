"""v4 phase 2 · task 1 — the change journal, the ledger's non-money sibling.

The ledger journals money. This journals everything else — an address change, a
mandate edit, a status flip — so "every change is auditable" is literal across
the whole store, and any past state is reconstructable by replay (D-CL-026).

App-level, not a database trigger: identical for the in-memory and Postgres
stores, and testable offline. Time is always injected.
"""

import pytest

from src.records.changelog import ChangeJournal, FieldDelta, RecordChangeEntry
from src.records.models import Contact, Party, Policy, Transaction, gbp
from src.records.store import InMemoryRecordBook

SEED_AT = "2026-01-01T00:00:00"


def _party(party_id="PH-1001", **over) -> Party:
    kw = dict(party_id=party_id, name="Theta Meridian 12", dob="1954-02-11",
              registered_address="14 Lattice Way, Demoford",
              contact=Contact(phone="07700 900819", email="ph-1001@example.org",
                              registered=True))
    kw.update(over)
    return Party(**kw)


def _policy(policy_no="LP-20419876", **over) -> Policy:
    kw = dict(policy_no=policy_no, product="lifelong_protection", status="in_force",
              start_date="2016-05-01", holder_party_id="PH-1001")
    kw.update(over)
    return Policy(**kw)


def _seeded() -> InMemoryRecordBook:
    book = InMemoryRecordBook()
    book.add_party(_party(), actor="seed", source_ref="seed", at=SEED_AT)
    book.add_policy(_policy(), actor="seed", source_ref="seed", at=SEED_AT)
    return book


# ── the entry shape ──────────────────────────────────────────────────────
def test_change_entry_carries_actor_source_ref_and_injected_time():
    entry = RecordChangeEntry(
        seq=1, entity_type="party", entity_id="PH-1001",
        changes=(FieldDelta(field="registered_address", old="14 Lattice Way",
                            new="9 Cobbleside"),),
        actor="handler_a", source_ref="CN-1000000001", at="2026-07-13T09:00:00")
    assert entry.changes[0].field == "registered_address"
    assert entry.changes[0].old == "14 Lattice Way"
    assert entry.actor == "handler_a"
    assert entry.source_ref == "CN-1000000001"


def test_change_entry_source_ref_must_be_a_case_interaction_or_seed():
    for ref in ("CW-300218754", "CN-1000000001", "seed"):
        RecordChangeEntry(seq=1, entity_type="party", entity_id="PH-1001",
                          changes=(), actor="a", source_ref=ref, at=SEED_AT)
    with pytest.raises(ValueError):
        RecordChangeEntry(seq=1, entity_type="party", entity_id="PH-1001",
                          changes=(), actor="a", source_ref="because I said so",
                          at=SEED_AT)


# ── the journal is append-only ───────────────────────────────────────────
def test_journal_sequences_entries_from_one():
    journal = ChangeJournal()
    first = journal.append(entity_type="party", entity_id="PH-1001", changes=(),
                           actor="a", source_ref="seed", at=SEED_AT)
    second = journal.append(entity_type="party", entity_id="PH-1002", changes=(),
                            actor="a", source_ref="seed", at=SEED_AT)
    assert (first.seq, second.seq) == (1, 2)


def test_journal_history_is_an_immutable_snapshot():
    journal = ChangeJournal()
    journal.append(entity_type="party", entity_id="PH-1001", changes=(), actor="a",
                   source_ref="seed", at=SEED_AT)
    snapshot = journal.entries()
    assert isinstance(snapshot, tuple)
    # Mutating the snapshot cannot reach the journal.
    with pytest.raises((AttributeError, TypeError)):
        snapshot.append(None)          # type: ignore[attr-defined]
    assert len(journal.entries()) == 1


def test_journal_exposes_no_way_to_edit_or_remove_an_entry():
    journal = ChangeJournal()
    for forbidden in ("delete", "remove", "update", "edit", "clear", "pop"):
        assert not hasattr(journal, forbidden), f"append-only: {forbidden} must not exist"


def test_journal_filters_by_entity():
    journal = ChangeJournal()
    journal.append(entity_type="party", entity_id="PH-1001", changes=(), actor="a",
                   source_ref="seed", at=SEED_AT)
    journal.append(entity_type="policy", entity_id="LP-20419876", changes=(), actor="a",
                   source_ref="seed", at=SEED_AT)
    found = journal.for_entity("party", "PH-1001")
    assert len(found) == 1 and found[0].entity_id == "PH-1001"


# ── every mutating store operation journals ──────────────────────────────
def test_adding_a_party_is_journalled():
    book = InMemoryRecordBook()
    book.add_party(_party(), actor="seed", source_ref="seed", at=SEED_AT)
    entries = book.changes.for_entity("party", "PH-1001")
    assert len(entries) == 1
    assert entries[0].actor == "seed"


def test_adding_a_policy_is_journalled():
    book = _seeded()
    entries = book.changes.for_entity("policy", "LP-20419876")
    assert len(entries) == 1


def test_an_address_update_appends_an_entry_carrying_actor_and_source_ref():
    # The phase's done criterion, stated directly.
    book = _seeded()
    book.update_party("PH-1001", actor="handler_a", source_ref="CN-1000000001",
                      at="2026-07-13T09:00:00",
                      registered_address="9 Cobbleside, Demoford")

    entries = book.changes.for_entity("party", "PH-1001")
    assert len(entries) == 2                      # the add, then the update
    latest = entries[-1]
    assert latest.actor == "handler_a"
    assert latest.source_ref == "CN-1000000001"
    assert latest.at == "2026-07-13T09:00:00"
    delta = next(d for d in latest.changes if d.field == "registered_address")
    assert delta.old == "14 Lattice Way, Demoford"
    assert delta.new == "9 Cobbleside, Demoford"


def test_an_update_actually_changes_the_stored_party():
    book = _seeded()
    book.update_party("PH-1001", actor="handler_a", source_ref="CN-1000000001",
                      at="2026-07-13T09:00:00", registered_address="9 Cobbleside")
    assert book.get_party("PH-1001").registered_address == "9 Cobbleside"


def test_an_update_that_changes_nothing_journals_nothing():
    # A no-op write must not manufacture an audit trail.
    book = _seeded()
    before = len(book.changes.entries())
    book.update_party("PH-1001", actor="handler_a", source_ref="CN-1000000001",
                      at="2026-07-13T09:00:00",
                      registered_address="14 Lattice Way, Demoford")
    assert len(book.changes.entries()) == before


def test_updating_an_unknown_field_is_refused():
    book = _seeded()
    with pytest.raises(Exception):
        book.update_party("PH-1001", actor="a", source_ref="seed", at=SEED_AT,
                          favourite_colour="green")


def test_applying_a_transaction_is_journalled_against_the_policy():
    book = _seeded()
    book.apply_transaction("LP-20419876", Transaction(
        txn_id="TXN-1", policy_no="LP-20419876", kind="opening",
        amount_pence=gbp(46_210), reason="opening fund value", actor="seed",
        at="2016-05-01T00:00:00"))
    entries = book.changes.for_entity("policy", "LP-20419876")
    assert len(entries) == 2                      # the add, then the money movement
    assert entries[-1].at == "2016-05-01T00:00:00"      # the transaction's own time


def test_a_refused_transaction_journals_nothing():
    # An overdraw is refused by the ledger; the journal must not record an
    # attempt as though it happened.
    book = _seeded()
    before = len(book.changes.entries())
    with pytest.raises(Exception):
        book.apply_transaction("LP-20419876", Transaction(
            txn_id="TXN-2", policy_no="LP-20419876", kind="withdrawal",
            amount_pence=gbp(1), reason="overdraw", actor="seed",
            at="2016-05-02T00:00:00"))
    assert len(book.changes.entries()) == before


def test_a_policy_status_flip_is_journalled():
    book = _seeded()
    book.update_policy("LP-20419876", actor="reviewer_b", source_ref="CW-300218754",
                       at="2026-07-13T10:00:00", status="surrendered")
    latest = book.changes.for_entity("policy", "LP-20419876")[-1]
    delta = next(d for d in latest.changes if d.field == "status")
    assert (delta.old, delta.new) == ("in_force", "surrendered")
    assert book.get_policy("LP-20419876").status == "surrendered"
