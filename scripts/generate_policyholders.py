#!/usr/bin/env python3
"""Generate 50–100 synthetic policyholders shaped for the v4 Party model.

This writes the **v4 identity manifest** — the 80 holders that seed the running
book. It is deliberately *not* the world: v4.5's two hundred policies and the
cast around them are built by `world/identities/`, and land in `data/world/`.
Until the world replaces the book wholesale, this file and its output stay
exactly as they are, because v4.5 changes no running behaviour.

What both share is `world.identities.reserved`, which is the single definition
of what a synthetic identity looks like — the reserved telephone range, the
unregistrable domain, the unallocated postcode area, the non-human name
vocabularies (D-CL-022). Holding a second copy here is how the two would
quietly drift apart, and a drifted copy is how a detail stops being reserved
without anyone noticing.

Deterministic per --seed, so the committed output is reproducible:

    python scripts/generate_policyholders.py                 # 80 holders
    python scripts/generate_policyholders.py --count 100 --seed 7
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from world.identities.reserved import (  # noqa: E402
    FAMILY_TOKENS,
    GIVEN_TOKENS,
    adult_dob,
    reserved_address,
    reserved_email,
    reserved_phone,
    synthetic_name,
)

_PRODUCTS = (
    ("LP", "lifelong_protection"),
    ("HB", "horizon_bond"),
    ("RA", "retirement_account"),
)
# The three KB sample records keep their numbers; the generator must not
# collide with them (they seed the book separately in v4 phase 2).
KB_SAMPLE_POLICY_NOS = frozenset({"LP-20419876", "HB-40582213", "RA-77103428"})

_VULNERABILITY_CATEGORIES = ("communication", "recent_bereavement", "health")


def _policy_no(rng: random.Random, prefix: str, used: set[str]) -> str:
    while True:
        number = f"{prefix}-{rng.randint(10_000_000, 99_999_999)}"
        if number not in used and number not in KB_SAMPLE_POLICY_NOS:
            used.add(number)
            return number


def _vulnerability(rng: random.Random, n: int) -> dict | None:
    if rng.random() >= 0.06:  # a small, honest minority carry a support flag
        return None
    return {"support_needs_ref": f"SN-{n:04d}",
            "category": rng.choice(_VULNERABILITY_CATEGORIES)}


def generate_book(*, count: int, seed: int, as_of: date) -> list[dict]:
    """Return `count` Party-shaped records (50–100, per the operator's spec)."""
    if not 50 <= count <= 100:
        raise ValueError(f"count must be 50–100, got {count}")
    rng = random.Random(seed)
    names_used: set[str] = set()
    policy_nos_used: set[str] = set()
    book: list[dict] = []

    for i in range(count):
        n = 1001 + i  # PH-1001+ — clear of the KB-derived PH-0001… range
        prefix, product = rng.choice(_PRODUCTS)
        book.append({
            "party_id": f"PH-{n:04d}",
            "name": synthetic_name(rng, names_used),
            "dob": adult_dob(rng, as_of),
            "registered_address": reserved_address(rng),
            "contact": {
                "phone": reserved_phone(rng),
                "email": reserved_email(f"ph-{n:04d}"),
                "registered": True,
            },
            "scottish_taxpayer": rng.random() < 0.15,
            "vulnerability_flag": _vulnerability(rng, n),
            "id_verified_level": None,  # verification happens only at the gate
            "policy": {"policy_no": _policy_no(rng, prefix, policy_nos_used),
                       "product": product},
        })
    return book


def write_jsonl(book: list[dict], path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(h, ensure_ascii=False) + "\n" for h in book),
                    encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=80, help="50–100 holders")
    parser.add_argument("--seed", type=int, default=4)
    parser.add_argument("--as-of", default="2026-07-25",
                        help="reference date for ages (never the wall clock)")
    parser.add_argument("--out", default="data/synthetic/policyholders.jsonl")
    args = parser.parse_args()

    book = generate_book(count=args.count, seed=args.seed,
                         as_of=date.fromisoformat(args.as_of))
    write_jsonl(book, args.out)

    by_product: dict[str, int] = {}
    for holder in book:
        by_product[holder["policy"]["product"]] = (
            by_product.get(holder["policy"]["product"], 0) + 1)
    flagged = sum(1 for h in book if h["vulnerability_flag"])
    print(f"wrote {len(book)} synthetic policyholders → {args.out}")
    print(f"  products: {by_product} · vulnerability flags: {flagged} · seed {args.seed}")


if __name__ == "__main__":
    main()
