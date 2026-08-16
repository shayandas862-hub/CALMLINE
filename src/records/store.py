"""The RecordStore interface and its in-memory implementation.

``RecordStore`` is the seam: the in-memory ``InMemoryRecordBook`` here is used
for all offline development and tests, and ``PostgresRecordStore`` plugs into
the same interface — with no change to the ledger logic.

**Every mutating operation journals.** Adding a party, adding a policy, editing
a field, committing money — each appends a ``RecordChangeEntry`` carrying the
actor, the case or interaction it came from, and an injected timestamp. A write
that changes nothing journals nothing; a write the ledger refuses journals
nothing either, because it did not happen.
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields, replace
from typing import Any, Optional, Protocol, runtime_checkable

from src.records.changelog import ChangeJournal, FieldDelta, diff
from src.records.interactions import InteractionStore
from src.records.ledger import PolicyLedger
from src.records.models import LedgerEntry, Party, Policy, Transaction


class RecordError(RuntimeError):
    """Raised for operations on a party or policy the store does not know."""


@runtime_checkable
class RecordStore(Protocol):
    """The system-of-record interface every implementation honours."""

    def get_party(self, party_id: str) -> Optional[Party]: ...
    def get_policy(self, policy_no: str) -> Optional[Policy]: ...
    def list_policies(self) -> list[Policy]: ...
    def apply_transaction(self, policy_no: str, txn: Transaction) -> LedgerEntry: ...
    def history(self, policy_no: str) -> tuple[LedgerEntry, ...]: ...
    def current_value(self, policy_no: str) -> int: ...


def _field_names(record: Any) -> "tuple[str, ...]":
    return tuple(f.name for f in dataclass_fields(record))


class InMemoryRecordBook:
    """An in-memory book of business. Each policy owns a ``PolicyLedger``."""

    def __init__(self) -> None:
        self._parties: dict[str, Party] = {}
        self._policies: dict[str, Policy] = {}
        self._ledgers: dict[str, PolicyLedger] = {}
        self._changes = ChangeJournal()
        # Per-product detail, keyed by policy. Singular for the one-per-policy
        # shapes, lists for the many-per-policy ones.
        self._covers: dict[str, Any] = {}
        self._bond_terms: dict[str, Any] = {}
        self._pension_terms: dict[str, Any] = {}
        self._pension_tax: dict[str, Any] = {}
        self._mandates: dict[str, Any] = {}
        self._funds: dict[str, list[Any]] = {}
        self._authorities: dict[str, list[Any]] = {}
        self._interactions = InteractionStore()
        self._cases: dict[str, list[Any]] = {}

    @property
    def interactions(self) -> InteractionStore:
        """The `CN-` contact log."""
        return self._interactions

    def add_interaction(self, interaction: Any, *, actor: str, source_ref: str,
                        at: str) -> Any:
        """Record a contact against a policy."""
        self._require_policy(interaction.policy_no)
        self._interactions.add(interaction)
        self._changes.append(entity_type="interaction", entity_id=interaction.cn_ref,
                             changes=(FieldDelta(field="opened_at", old=None,
                                                 new=interaction.opened_at),),
                             actor=actor, source_ref=source_ref, at=at)
        return interaction

    def add_case(self, case: Any, *, actor: str, source_ref: str, at: str) -> Any:
        """Record a case against a policy."""
        self._require_policy(case.policy_no)
        self._cases.setdefault(case.policy_no, []).append(case)
        self._changes.append(entity_type="case", entity_id=case.cw_ref or case.case_id,
                             changes=(FieldDelta(field="status", old=None,
                                                 new=case.status),),
                             actor=actor, source_ref=source_ref, at=at)
        return case

    def cases_for_policy(self, policy_no: str) -> "tuple[Any, ...]":
        return tuple(self._cases.get(policy_no, ()))

    @property
    def changes(self) -> ChangeJournal:
        """The append-only journal of every non-money change (and the money
        ones too — the ledger holds the amounts, this holds the fact)."""
        return self._changes

    # ── writes to the book itself (not money) ────────────────────────────
    def add_party(self, party: Party, *, actor: str, source_ref: str, at: str) -> None:
        """Add a party and journal its creation."""
        self._parties[party.party_id] = party
        self._changes.append(
            entity_type="party", entity_id=party.party_id,
            changes=tuple(FieldDelta(field=name, old=None, new=getattr(party, name))
                          for name in _field_names(party)),
            actor=actor, source_ref=source_ref, at=at)

    def add_policy(self, policy: Policy, *, actor: str, source_ref: str, at: str) -> None:
        """Add a policy, open its ledger, and journal the creation."""
        self._policies[policy.policy_no] = policy
        self._ledgers.setdefault(policy.policy_no, PolicyLedger(policy.policy_no))
        self._changes.append(
            entity_type="policy", entity_id=policy.policy_no,
            changes=tuple(FieldDelta(field=name, old=None, new=getattr(policy, name))
                          for name in _field_names(policy)),
            actor=actor, source_ref=source_ref, at=at)

    def update_party(self, party_id: str, *, actor: str, source_ref: str, at: str,
                     **updates: Any) -> Party:
        """Edit a party's fields, journalling exactly what moved."""
        party = self._parties.get(party_id)
        if party is None:
            raise RecordError(f"unknown party {party_id!r}")
        return self._apply_update("party", party_id, party, self._parties,
                                  updates, actor=actor, source_ref=source_ref, at=at)

    def update_policy(self, policy_no: str, *, actor: str, source_ref: str, at: str,
                      **updates: Any) -> Policy:
        """Edit a policy's fields, journalling exactly what moved."""
        policy = self._policies.get(policy_no)
        if policy is None:
            raise RecordError(f"unknown policy {policy_no!r}")
        return self._apply_update("policy", policy_no, policy, self._policies,
                                  updates, actor=actor, source_ref=source_ref, at=at)

    # ── per-product detail ───────────────────────────────────────────────
    def add_cover(self, cover: Any, *, actor: str, source_ref: str, at: str) -> None:
        """Attach LP cover to its policy."""
        self._attach("cover", self._covers, cover.policy_no, cover,
                     actor=actor, source_ref=source_ref, at=at)

    def add_bond_terms(self, terms: Any, *, actor: str, source_ref: str, at: str) -> None:
        """Attach HB policy-level terms (segments, 5% allowance)."""
        self._attach("bond_terms", self._bond_terms, terms.policy_no, terms,
                     actor=actor, source_ref=source_ref, at=at)

    def add_pension_terms(self, terms: Any, *, actor: str, source_ref: str, at: str) -> None:
        """Attach RA policy-level terms (contributions, wish, transfers-in)."""
        self._attach("pension_terms", self._pension_terms, terms.policy_no, terms,
                     actor=actor, source_ref=source_ref, at=at)

    def add_pension_tax(self, tax: Any, *, actor: str, source_ref: str, at: str) -> None:
        """Attach RA pension-tax state (MPAA, protections, LSA)."""
        self._attach("pension_tax", self._pension_tax, tax.policy_no, tax,
                     actor=actor, source_ref=source_ref, at=at)

    def add_mandate(self, mandate: Any, *, actor: str, source_ref: str, at: str) -> None:
        """Attach the bank mandate — the control state behind ``bank_last4``."""
        self._attach("mandate", self._mandates, mandate.policy_no, mandate,
                     actor=actor, source_ref=source_ref, at=at)

    def add_fund(self, fund: Any, policy_no: str, *, actor: str, source_ref: str,
                 at: str) -> None:
        """Append one fund line to a policy's holdings."""
        self._require_policy(policy_no)
        self._funds.setdefault(policy_no, []).append(fund)
        self._changes.append(entity_type="fund", entity_id=policy_no,
                             changes=(FieldDelta(field="fund", old=None,
                                                 new=fund.fund_id),),
                             actor=actor, source_ref=source_ref, at=at)

    def add_authority(self, authority: Any, *, actor: str, source_ref: str,
                      at: str) -> None:
        """Append a third-party authority record to a policy (AD-CL-033)."""
        self._require_policy(authority.policy_no)
        self._authorities.setdefault(authority.policy_no, []).append(authority)
        self._changes.append(entity_type="authority", entity_id=authority.policy_no,
                             changes=(FieldDelta(field="authority", old=None,
                                                 new=authority.authority_id),),
                             actor=actor, source_ref=source_ref, at=at)

    def get_cover(self, policy_no: str) -> Optional[Any]:
        return self._covers.get(policy_no)

    def get_bond_terms(self, policy_no: str) -> Optional[Any]:
        return self._bond_terms.get(policy_no)

    def get_pension_terms(self, policy_no: str) -> Optional[Any]:
        return self._pension_terms.get(policy_no)

    def get_pension_tax(self, policy_no: str) -> Optional[Any]:
        return self._pension_tax.get(policy_no)

    def get_mandate(self, policy_no: str) -> Optional[Any]:
        return self._mandates.get(policy_no)

    def get_funds(self, policy_no: str) -> "tuple[Any, ...]":
        return tuple(self._funds.get(policy_no, ()))

    def get_authorities(self, policy_no: str) -> "tuple[Any, ...]":
        return tuple(self._authorities.get(policy_no, ()))

    # ── reads ────────────────────────────────────────────────────────────
    def get_party(self, party_id: str) -> Optional[Party]:
        return self._parties.get(party_id)

    def list_parties(self) -> list[Party]:
        return list(self._parties.values())

    def get_policy(self, policy_no: str) -> Optional[Policy]:
        return self._policies.get(policy_no)

    def list_policies(self) -> list[Policy]:
        return list(self._policies.values())

    def policies_for_party(self, party_id: str) -> list[Policy]:
        return [p for p in self._policies.values() if p.holder_party_id == party_id]

    def history(self, policy_no: str) -> tuple[LedgerEntry, ...]:
        return self._ledger(policy_no).history()

    def current_value(self, policy_no: str) -> int:
        return self._ledger(policy_no).balance()

    # ── the one money-touching write ─────────────────────────────────────
    def apply_transaction(self, policy_no: str, txn: Transaction, *,
                          source_ref: str = "seed") -> LedgerEntry:
        """Append a transaction to the policy's ledger (overdraw-checked there).

        The journal entry is written only after the ledger accepts the movement,
        so a refused transaction leaves no trace of having happened.
        """
        entry = self._ledger(policy_no).apply(txn)
        self._changes.append(
            entity_type="policy", entity_id=policy_no,
            changes=(FieldDelta(field="ledger", old=None,
                                new=f"{txn.kind} {txn.signed_pence}p → "
                                    f"{entry.balance_after_pence}p"),),
            actor=txn.actor, source_ref=source_ref, at=txn.at)
        return entry

    # ── internal ─────────────────────────────────────────────────────────
    def _attach(self, entity_type: str, registry: dict[str, Any], policy_no: str,
                value: Any, *, actor: str, source_ref: str, at: str) -> None:
        """Store one piece of per-product detail against a known policy."""
        self._require_policy(policy_no)
        registry[policy_no] = value
        self._changes.append(
            entity_type=entity_type, entity_id=policy_no,
            changes=tuple(FieldDelta(field=name, old=None, new=getattr(value, name))
                          for name in _field_names(value)),
            actor=actor, source_ref=source_ref, at=at)

    def _require_policy(self, policy_no: str) -> None:
        if policy_no not in self._policies:
            raise RecordError(f"unknown policy {policy_no!r}")

    def _apply_update(self, entity_type: str, entity_id: str, current: Any,
                      registry: dict[str, Any], updates: dict[str, Any], *,
                      actor: str, source_ref: str, at: str) -> Any:
        known = _field_names(current)
        unknown = set(updates) - set(known)
        if unknown:
            raise RecordError(
                f"unknown {entity_type} field(s) {sorted(unknown)} on {entity_id}")
        updated = replace(current, **updates)
        deltas = diff(current, updated, known)
        if not deltas:
            return current            # a no-op write manufactures no audit trail
        registry[entity_id] = updated
        self._changes.append(entity_type=entity_type, entity_id=entity_id,
                             changes=deltas, actor=actor, source_ref=source_ref, at=at)
        return updated

    def _ledger(self, policy_no: str) -> PolicyLedger:
        if policy_no not in self._policies:
            raise RecordError(f"unknown policy {policy_no!r}")
        return self._ledgers[policy_no]
