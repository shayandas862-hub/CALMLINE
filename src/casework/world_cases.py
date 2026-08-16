"""The dataset's live queue rows as real `Case` objects.

The console's back-office queue can only rank what it holds, so the world's
open work has to arrive as the same shape the raise path produces — under the
references the dataset minted, because "the same cases are in the database
after a reload" is only true if nothing renumbers them on the way through.

Nothing here invents: every field is the row's own, and a row this module
does not understand raises rather than guessing — the reader upstream has
already verified the file against the manifest, so a surprise here is a
programming fault, not bad data to be coped with.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from src.casework.models import Case, EvidenceItem


def cases_from_queue(rows: Iterable[Mapping]) -> "list[Case]":
    """Every queue row as a `Case`, evidence and all, nothing re-minted."""
    return [_case(row) for row in rows]


def _case(row: Mapping) -> Case:
    return Case(
        case_id=row["cw_ref"],
        cw_ref=row["cw_ref"],
        policy_no=row["policy_no"],
        request=row["request"],
        cn_ref=row["cn_ref"],
        type=row["type"],
        priority=row["priority"],
        status=row["status"],
        sla_due=row["sla_due"],
        created_at=f"{row['opened_on']}T00:00:00",
        evidence=[EvidenceItem(
            evidence_id=item["evidence_id"],
            cw_ref=row["cw_ref"],
            policy_no=row["policy_no"],
            requirement=item["requirement"],
            requirement_source=item["requirement_source"],
            received_via=item["received_via"],
            received_at=f"{item['received_on']}T00:00:00",
            satisfies=item["satisfies"],
        ) for item in row["evidence"]],
    )
