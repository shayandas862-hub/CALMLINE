"""What the caller screen is made of — search results and the handler's panel.

Split from ``gate_routes.py`` at the 300-line rule. Three assemblers, no
routes: find a policy by number **or** holder name, serialise the held checks
the handler ticks against, and name everyone with standing on the policy.
All of it is staff-facing; the caller-facing rules (nothing read aloud,
failure names no element) live in ``src.identity`` and are enforced there.
"""

from __future__ import annotations

from typing import Any, Optional

from src.identity.questions import held_checks

SEARCH_LIMIT = 8
_MIN_QUERY = 2


def search_policies(book: Any, query: str) -> dict:
    """Policies whose number or holder name contains ``query``.

    Case- and whitespace-insensitive, capped at ``SEARCH_LIMIT`` matches but
    honest about the real total — a capped list that says nothing was dropped
    teaches the handler the book is smaller than it is.
    """
    needle = " ".join(query.split()).casefold()
    if len(needle) < _MIN_QUERY:
        return {"query": query, "total": 0, "matches": []}

    found = []
    for policy in book.list_policies():
        holder = book.get_party(policy.holder_party_id)
        name = holder.name if holder else ""
        if needle in policy.policy_no.casefold() or needle in name.casefold():
            found.append({"policy_no": policy.policy_no, "holder": name,
                          "product": policy.product, "status": policy.status})
    found.sort(key=lambda match: match["policy_no"])
    return {"query": query, "total": len(found),
            "matches": found[:SEARCH_LIMIT]}


def checks_view(party: Any, policy: Any) -> list[dict]:
    """The `05-OPS:3.2` panel as the page receives it — held values included,
    because the screen is the handler's (D-CL-114)."""
    return [{"kind": check.kind, "prompt": check.prompt,
             "source": check.source,
             "held": [{"label": f.label, "value": f.value, "mono": f.mono,
                       "ask_only": f.ask_only} for f in check.fields]}
            for check in held_checks(party, policy)]


def _party_name(book: Any, party_id: str) -> str:
    party = book.get_party(party_id)
    return party.name if party else party_id


def authorities_view(book: Any, policy: Any) -> dict:
    """Everyone with standing on this policy, named and labelled.

    The handler must be able to see who may speak before deciding anything —
    the holder, every recorded authority (with scope and status), the adviser
    firm's LOA, and any trust's trustees. Empty sections are reported as
    empty, not omitted: "nobody else holds authority" is a finding.
    """
    records = [{"authority_id": record.authority_id, "type": record.type,
                "name": _party_name(book, record.party_id),
                "scope": list(record.scope), "status": record.status}
               for record in book.get_authorities(policy.policy_no)]

    adviser: Optional[dict] = None
    loa = getattr(policy, "adviser_loa", None)
    if loa is not None:
        adviser = {"firm": loa.firm, "frn": loa.frn,
                   "scope": list(loa.scope), "expiry": loa.expiry}

    trust: Optional[dict] = None
    held = getattr(policy, "trust", None)
    if held is not None:
        trust = {"kind": held.kind,
                 "trustees": [_party_name(book, trustee)
                              for trustee in held.trustees]}

    return {"holder": {"name": _party_name(book, policy.holder_party_id),
                       "party_id": policy.holder_party_id},
            "records": records, "adviser": adviser, "trust": trust}
