"""Open live work into the dataset — a separate, re-runnable step.

    .venv/bin/python -m world.load.queue
    .venv/bin/python -m world.load.queue --as-of 2026-07-28 --seed 7 --count 8

Open cases are the only thing in the world that ages; everything else is
history, and history does not rot. So the queue is refreshed by its own step,
appending to `queue.jsonl` and touching not a byte of anything historical —
a demo left alone for three weeks gets a fresh queue with two commands: run
this, reload.

Dates are **injected** (`--as-of`, defaulting to the world's birth date),
never the wall clock. References continue deterministically from whatever
each policy already carries, in the same policy-derived grammar as history,
so two runs produce two sets and no collisions. Requests and evidence come
from a fixed catalogue whose lines assert nothing about parties — the
reconciliation's rule: evidence may only name parties the policy has, and the
safest sentence is one that names none.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

from world import WORLD_BIRTH_DATE
from world.dataset import DEFAULT_ROOT, DatasetError, read_world
from world.dataset.manifest import digest_of
from world.dataset.queue_rows import LIVE_STATUSES
# The one copy of the reference formula — product digit, serial, index. Its
# docstring records the collision the obvious version caused; importing it is
# safer than a second copy, module-private name notwithstanding.
from world.operations.skeleton import _reference

__all__ = ["LIVE_STATUSES", "append_queue", "open_queue"]

# (request, case type, status, priority, needs-evidence). Requests name the
# ask and nothing else — no party, no asserted record state. The four live
# case types finally all get used; claim_linked stays history's, because a
# live claim needs a death the queue must not invent.
_PROFILES = (
    ("withdrawal_request — {pence}p", "servicing", "pending_review", "high",
     True),
    ("address_change", "servicing", "pending_review", "low", False),
    ("subject access request — full record", "DSAR", "pending_review",
     "medium", True),
    ("transfer enquiry — origin scheme details awaited", "transfer",
     "held_for_review", "medium", False),
    ("annual review", "review", "pending_review", "low", False),
    ("withdrawal_request — {pence}p", "servicing", "blocked", "high", True),
)

# Real requirement lines from the book's own evidence vocabulary, party-free.
_EVIDENCE = {
    "pending_review": ("identity confirmed to standard verification",
                       "05-OPS:3.2", "yes"),
    "blocked": ("identity could not be verified to the required standard",
                "05-OPS:3.2", "no"),
}

_SLA_DAYS = {"high": 1, "medium": 3, "low": 7}


def open_queue(world: Any, *, as_of: date, seed: int,
               count: int = 8) -> tuple[dict, ...]:
    """``count`` open cases against in-force policies, deterministically."""
    rng = random.Random(f"queue-{seed}")   # never hash(): stable across runs
    candidates = [policy for policy in world.policies
                  if policy.status == "in_force"]
    if not candidates:
        raise DatasetError("no in-force policy to open live work on")

    next_case = _next_indices(world, kind="cases")
    next_evidence = _next_indices(world, kind="evidence")

    rows = []
    for _ in range(count):
        policy = candidates[rng.randrange(len(candidates))]
        request, case_type, status, priority, evidenced = _PROFILES[
            rng.randrange(len(_PROFILES))]
        if "{pence}" in request:
            balance = (policy.entries[-1].balance_after_pence
                       if policy.entries else 0)
            if balance < 5_000:
                request, case_type, status, priority, evidenced = _PROFILES[1]
            else:
                request = request.format(
                    pence=balance * rng.randrange(5, 21) // 100)

        policy_no = policy.policy_no
        index = next_case[policy_no] = next_case.get(policy_no, 0) + 1
        opened = as_of - timedelta(days=rng.randrange(0, 6) if evidenced else 0)

        evidence = []
        if evidenced and status in _EVIDENCE:
            requirement, source, satisfies = _EVIDENCE[status]
            eindex = next_evidence[policy_no] = \
                next_evidence.get(policy_no, 0) + 1
            evidence.append({
                "evidence_id": _reference("EVD", 9, policy_no, eindex),
                "requirement": requirement, "requirement_source": source,
                "received_on": min(opened + timedelta(days=1), as_of)
                               .isoformat(),
                "received_via": ("portal", "post", "email")[rng.randrange(3)],
                "satisfies": satisfies})

        due = as_of + timedelta(days=_SLA_DAYS[priority])
        rows.append({
            "cw_ref": _reference("CW", 9, policy_no, index),
            "policy_no": policy_no,
            "cn_ref": None,
            "opened_on": opened.isoformat(),
            "request": request,
            "type": case_type,
            "status": status,
            "priority": priority,
            "sla_due": f"{due.isoformat()}T17:00:00",
            "evidence": evidence,
        })
    return tuple(rows)


def _next_indices(world: Any, *, kind: str) -> dict[str, int]:
    """The highest reference index each policy already carries — history and
    queue both — so a new reference continues rather than collides."""
    highest: dict[str, int] = {}

    def note(policy_no: str, reference: str) -> None:
        index = int(reference[-3:])
        if index > highest.get(policy_no, 0):
            highest[policy_no] = index

    for operations in world.operations.values():
        for case in operations.cases:
            if kind == "cases":
                note(operations.policy_no, case.cw_ref)
            else:
                for item in case.evidence:
                    note(operations.policy_no, item.evidence_id)
    for row in world.queue:
        if kind == "cases":
            note(row["policy_no"], row["cw_ref"])
        else:
            for item in row["evidence"]:
                note(row["policy_no"], item["evidence_id"])
    return highest


def append_queue(root: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Add live work to `queue.jsonl` and refresh the manifest around it.

    Refuses whole on a reference already in the file — all of it or none of
    it, the same discipline as the prose appender. Historical files are not
    opened for writing here at all, which is what "alters nothing historical"
    means structurally rather than behaviourally.
    """
    rows = list(rows)
    path = root / "queue.jsonl"
    existing = ([line for line in
                 path.read_text(encoding="utf-8").splitlines() if line]
                if path.is_file() else [])
    seen = {json.loads(line)["cw_ref"] for line in existing}

    encoded = []
    for row in rows:
        if row["cw_ref"] in seen:
            raise DatasetError(
                f"queue.jsonl already holds {row['cw_ref']} — refusing "
                f"rather than writing one reference twice")
        seen.add(row["cw_ref"])
        encoded.append(json.dumps(row, sort_keys=True))

    body = "".join(line + "\n" for line in existing + encoded).encode("utf-8")
    path.write_bytes(body)

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lines = len(body.splitlines())
    manifest["files"]["queue.jsonl"] = {"lines": lines,
                                        "sha256": digest_of(body)}
    manifest["counts"]["queue"] = lines
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--as-of", default=WORLD_BIRTH_DATE.isoformat(),
                        help="the queue's own clock — injected, never wall")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--count", type=int, default=8)
    args = parser.parse_args()

    root = Path(args.root)
    world = read_world(root)
    rows = open_queue(world, as_of=date.fromisoformat(args.as_of),
                      seed=args.seed, count=args.count)
    append_queue(root, rows)
    print(f"opened {len(rows)} live cases as of {args.as_of} → "
          f"{root / 'queue.jsonl'}")
    for row in rows:
        print(f"  {row['cw_ref']}  {row['policy_no']}  {row['priority']:6} "
              f"{row['status']:15} {row['request']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DatasetError as refusal:
        print(f"REFUSED — {refusal}", file=sys.stderr)
        raise SystemExit(1)
