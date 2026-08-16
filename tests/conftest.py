"""Two suite-wide things: the identity-gate audit, and the world fixtures.

**The gate audit (v4 phase 3).** The phase's headline done criterion is stronger
than any single test can state: **zero disclosures without a passed verification
record in the whole suite run**. A per-test assertion only covers the traffic
that test happened to generate; a console app built somewhere else, by a test
written later, would never be looked at.

So every ``GateEventLog`` the console builds is registered here, and at the end
of the session every one of them is asked the same question. If any test in the
suite — including one that has nothing to do with the gate — ever causes a
disclosure with no passed record behind it, the run fails and names the event.

Note this counts **disclosures**, not ``bypass_attempt`` events. Refusals are
supposed to happen and several tests provoke them deliberately; what must never
happen is data actually going out.

**The world fixtures (v4.5 phase 3).** The book of two hundred is built once per
session and shared, because building it per test file is the same deterministic
work repeated. ``tiny_world`` is the opposite: two hand-made policies carrying
one of everything the dataset format has to survive, so the refusal tests can
say what they mean without two hundred policies in the way.
"""

from datetime import date

import pytest

import src.web.console.app as console_app
from src.identity.events import GateEventLog
from src.records.authorisations import BankMandate, MandateChange
from src.records.models import LedgerEntry, Transaction
from world import WORLD_BIRTH_DATE
from world.lifetimes.events import LifeEvent
from world.operations.shapes import (
    PlannedCase,
    PlannedContact,
    PlannedEvidence,
    PolicyOperations,
)

WORLD_SEED = 11
PEOPLE_AS_OF = date(2026, 7, 25)

_LOGS: list[GateEventLog] = []


class _RegisteredGateEventLog(GateEventLog):
    """A gate log that remembers itself, so the session can audit them all."""

    def __init__(self) -> None:
        super().__init__()
        _LOGS.append(self)


@pytest.fixture(autouse=True, scope="session")
def _audit_every_gate_log():
    """Swap in the registering log, then audit every one at session end."""
    original = console_app.GateEventLog
    console_app.GateEventLog = _RegisteredGateEventLog
    try:
        yield
    finally:
        console_app.GateEventLog = original

    # Without this the audit below passes by having looked at nothing.
    assert _LOGS, "no gate log was registered — the suite-wide audit was vacuous"

    offenders = [(index, event)
                 for index, log in enumerate(_LOGS)
                 for event in log.disclosures_without_pass()]
    assert not offenders, (
        "a disclosure happened with no passed verification behind it: "
        + "; ".join(f"app#{i} seq={e.seq} {e.policy_no} cn={e.cn_ref} "
                    f"actor={e.actor}" for i, e in offenders))


# ── the world ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def world_book():
    """The real two hundred, built once. Deterministic, so sharing is safe."""
    from world.lifetimes.build import build_book

    return build_book(seed=WORLD_SEED, born=WORLD_BIRTH_DATE)


def _entry(policy_no: str, seq: int, kind: str, pence: int, at: str,
           balance: int) -> LedgerEntry:
    return LedgerEntry(
        seq=seq,
        transaction=Transaction(txn_id=f"TXN-{policy_no}-{seq}",
                                policy_no=policy_no, kind=kind,
                                amount_pence=pence, reason="a stated reason",
                                actor="world", at=at),
        balance_after_pence=balance)


@pytest.fixture
def tiny_world():
    """Two policies carrying one of everything the format has to survive.

    Deliberately includes the shapes the real book uses rarely — a mandate on
    hold, a change history, evidence recorded against a requirement — because
    those are exactly the fields a round-trip test would otherwise never touch.
    """
    from world.dataset import World
    from world.lifetimes.build import BuiltPolicy

    policy = BuiltPolicy(
        policy_no="LP-20000137", product="lifelong_protection", status="in_force",
        start=date(1998, 3, 1), holder_party_id="PH-0001",
        entries=(_entry("LP-20000137", 1, "opening", 500_00,
                        "1998-03-01T00:00:00", 500_00),
                 _entry("LP-20000137", 2, "charge", 100_00,
                        "1999-03-01T00:00:00", 400_00)),
        events=(LifeEvent(on=date(2004, 3, 1), kind="premium_review",
                          detail="reviewed at the sixth anniversary"),),
        band="under_25k", headline_value_pence=400_00)
    other = BuiltPolicy(
        policy_no="HB-20000274", product="horizon_bond", status="surrendered",
        start=date(2015, 6, 1), holder_party_id="PH-0002",
        entries=(_entry("HB-20000274", 1, "opening", 10_000_00,
                        "2015-06-01T00:00:00", 10_000_00),),
        events=(), band="25k_to_100k", headline_value_pence=10_000_00)

    mandates = {
        "LP-20000137": BankMandate(
            policy_no="LP-20000137", account_last4="4417", verified=True,
            change_history=(MandateChange(at="2026-05-02T00:00:00", actor="world",
                                          note="account changed"),)),
        "HB-20000274": BankMandate(policy_no="HB-20000274", account_last4="9902",
                                   verified=False, hold_until="2026-08-01"),
    }
    operations = {
        "LP-20000137": PolicyOperations(
            policy_no="LP-20000137",
            contacts=(PlannedContact(cn_ref="CN-2000013701",
                                     policy_no="LP-20000137",
                                     on=date(2024, 4, 2), channel="telephone",
                                     intent="valuation request",
                                     outcome="answered"),),
            cases=(PlannedCase(
                cw_ref="CW-300000001", policy_no="LP-20000137",
                cn_ref="CN-2000013701", opened_on=date(2024, 4, 2),
                closed_on=date(2024, 4, 9), request="partial surrender",
                type="surrender", status="completed",
                human_decision="approved",
                evidence=(PlannedEvidence(
                    evidence_id="EV-0001", requirement="identity",
                    requirement_source="05-OPS:3.2", received_on=date(2024, 4, 4),
                    satisfies="identity"),),
                authorised_movement_on=date(2024, 4, 9)),)),
        "HB-20000274": PolicyOperations(policy_no="HB-20000274", contacts=(),
                                        cases=()),
    }
    return World(policies=(policy, other), bank_mandates=mandates,
                 operations=operations, people=[{"party_id": "PH-0001"}],
                 memorable_holders=("PH-0001",), seed=WORLD_SEED,
                 born=WORLD_BIRTH_DATE, people_as_of=PEOPLE_AS_OF, stories=())
