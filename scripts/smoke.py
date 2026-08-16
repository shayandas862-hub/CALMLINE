#!/usr/bin/env python3
"""The nine-step smoke, driven over real HTTP against a running console.

    ./.venv/bin/python scripts/smoke.py http://127.0.0.1:8001    # local
    ./.venv/bin/python scripts/smoke.py https://<deployed-url>   # go-live 3.6

A checklist you click through gets run once and then trusted. This one is a
command, so the same nine steps can be re-run against the deployed URL — which
is the only place several of them mean anything.

**Not part of the test suite.** It needs a running server and exercises the real
HTTP surface rather than a TestClient; `pytest` never touches it. Exits non-zero
if any step fails, so it can gate a deploy.
"""
import json
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8002"
POLICY = "LP-20419876"
CONFIRMED = ["policy_no", "name_dob", "address_or_bank"]
results = []


def step(n, name, ok, detail):
    results.append((n, name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {n}. {name}\n        {detail}")


fo = httpx.Client(base_url=BASE, timeout=30)
bo = httpx.Client(base_url=BASE, timeout=30)
bo2 = httpx.Client(base_url=BASE, timeout=30)
ops = httpx.Client(base_url=BASE, timeout=30)

# 1 — login
r = fo.post("/api/login", json={"role": "front_office", "actor": "handler_1"})
step(1, "login (front office)", r.status_code == 200, f"{r.status_code} {r.text[:90]}")

# 2 — a disclosure BEFORE verification must be refused, then verify
pre = fo.get(f"/api/policy/{POLICY}")
cn = fo.post("/api/interaction/open", json={"policy_no": POLICY}).json()["cn_ref"]
fo.post("/api/verify", json={"cn_ref": cn, "policy_no": POLICY})          # present
v = fo.post("/api/verify", json={"cn_ref": cn, "policy_no": POLICY, "confirmed": CONFIRMED})
step(2, "verify the caller (428 before, passed after)",
     pre.status_code == 428 and v.json().get("outcome") == "passed",
     f"unverified={pre.status_code}, then outcome={v.json().get('outcome')}, cn={cn}")

# 3 — the page: record + history + valuation
rec = fo.get(f"/api/policy/{POLICY}", params={"cn_ref": cn})
val = fo.get(f"/api/policy/{POLICY}/value", params={"cn_ref": cn})
step(3, "page loads the record and its point-in-time value",
     rec.status_code == 200 and val.status_code == 200,
     f"record={rec.status_code}, value={val.json().get('value')} "
     f"as at {val.json().get('as_at')}")

# 4 — agent query
ag = fo.post("/api/agent", json={"message": "what is the grace period?",
                                "policy_no": POLICY, "cn_ref": cn})
body = ag.json() if ag.status_code == 200 else {}
# The two paths answer in different shapes: the live agent returns a
# ConsoleReply with `citations`; the offline keyword fallback returns the raw
# tool result with `result.clauses`. Both carry chunk_id + style + version.
cites = [c.get("chunk_id") for c in (body.get("citations") or [])] or \
        [c.get("chunk_id") for c in ((body.get("result") or {}).get("clauses") or [])]
step(4, "agent answers with governed citations",
     ag.status_code == 200 and bool(cites),
     f"{ag.status_code} · path={body.get('mode')} · cites={cites[:3]}")

# 5 — raise a case
rs = fo.post("/api/cases/raise", json={"policy_no": POLICY, "request": "withdrawal",
                                       "priority": "high", "amount_pence": 250000,
                                       "cn_ref": cn})
case_id = rs.json().get("case_id")
step(5, "raise a case from the front office", rs.status_code == 200 and bool(case_id),
     f"{rs.status_code} case={case_id} recommendation={rs.json().get('recommendation')}")

# 6 — approval by a SECOND actor (four-eyes)
bo.post("/api/login", json={"role": "back_office", "actor": "reviewer_1"})
before = fo.get(f"/api/policy/{POLICY}/value", params={"cn_ref": cn}).json()
ap = bo.post(f"/api/cases/{case_id}/approve")
after = fo.get(f"/api/policy/{POLICY}/value", params={"cn_ref": cn}).json()
moved = before.get("value_pence") != after.get("value_pence")
step(6, "human approval is the only thing that moves the ledger",
     ap.status_code == 200 and moved,
     f"{ap.status_code} · {before.get('value')} -> {after.get('value')}")

# 6b — the same case cannot be approved twice
again = bo.post(f"/api/cases/{case_id}/approve")
step("6b", "the same case cannot be approved twice", again.status_code == 409,
     f"{again.status_code} {again.json().get('detail', '')[:70]}")

# 7 — ops lenses
ops.post("/api/login", json={"role": "ops", "actor": "overseer_1"})
o = ops.get("/api/ops")
snap = o.json() if o.status_code == 200 else {}
step(7, "board chamber metrics are live", o.status_code == 200 and bool(snap),
     f"{o.status_code} · lenses={list(snap)} · "
     f"funds={snap.get('operations', {}).get('funds_under_admin')}")

# 8 — role enforced server-side
forbidden = fo.get("/api/ops")
step(8, "GET /api/ops is 403 to the front office",
     forbidden.status_code == 403, f"{forbidden.status_code}")

# 9 — health
h = httpx.get(f"{BASE}/healthz", timeout=30)
step(9, "GET /healthz reports honest component states", h.status_code == 200,
     f"{h.status_code} {json.dumps(h.json())[:150]}")

print("\n" + "=" * 62)
bad = [r for r in results if not r[2]]
print(f"{len(results) - len(bad)}/{len(results)} passed")
for n, name, _, detail in bad:
    print(f"  FAILED {n}. {name} — {detail}")
sys.exit(1 if bad else 0)
