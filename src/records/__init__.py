"""The system of record — CalmLine's factual, transactional store.

Parties, policies, per-product detail, an append-only transaction ledger and an
append-only change journal. Money is held as integer pence; every value is
synthetic; the logic is real. Kept behind a RecordStore interface so the
in-memory implementation here is swapped for Postgres with no change to the
ledger logic.
"""
