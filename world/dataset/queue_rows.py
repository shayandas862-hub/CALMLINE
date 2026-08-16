"""What a live queue row is, and what the reader refuses.

`queue.jsonl` holds **open work only**. History lives in `policies.jsonl`
under `operations.cases`, always completed; a queue row claiming to be
completed is history filed in the wrong drawer, and the reader refuses it
rather than tidying it across.

The vocabulary is the schema's own (`cases.status`, 0001_init.sql:313) minus
the terminal state — there is still no terminal refusal in the schema, that
gap is phase 6's known finding, and the queue must not invent one.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from world.dataset.manifest import DatasetError

LIVE_STATUSES = ("pending_review", "blocked", "held_for_review")

QUEUE_KEYS = ("cw_ref", "policy_no", "cn_ref", "opened_on", "request", "type",
              "status", "priority", "sla_due", "evidence")

EVIDENCE_KEYS = ("evidence_id", "requirement", "requirement_source",
                 "received_on", "received_via", "satisfies")


def validate_queue_row(row: Mapping[str, Any], *, policies: Iterable[str],
                       taken: set, where: str) -> None:
    """One row, checked whole — the same discipline as every other file."""
    for key in QUEUE_KEYS:
        if key not in row:
            raise DatasetError(f"{where}: missing field {key!r}")

    if row["policy_no"] not in policies:
        raise DatasetError(
            f"{where}: {row['cw_ref']} is opened on {row['policy_no']}, "
            f"which is not in the book")
    if row["status"] not in LIVE_STATUSES:
        raise DatasetError(
            f"{where}: {row['cw_ref']} carries status {row['status']!r} — "
            f"the queue holds open work only, and a completed case belongs "
            f"to history in policies.jsonl")
    if row["cw_ref"] in taken:
        raise DatasetError(
            f"{where}: {row['cw_ref']} is already taken — a reference names "
            f"exactly one piece of work")
    for item in row["evidence"]:
        for key in EVIDENCE_KEYS:
            if key not in item:
                raise DatasetError(
                    f"{where}: evidence on {row['cw_ref']} is missing "
                    f"{key!r}")
