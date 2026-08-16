"""Schema guards — text assertions on the migration SQL, no database needed.

Two halves, two owners. The **corpus** half (`kb_chunks`) was written and applied
in v4 phase 1 and is not touched here. The **records** half is phase 2's: the
system of record, modelled to the v4 data model.

These keep the committed SQL aligned with contracts enforced elsewhere in code,
so a drift fails here rather than in production. The real applied-schema check
is the marker-gated integration test.
"""

import re
from pathlib import Path

from src import constants
from src.records.models import ALL_KINDS

MIGRATION = Path(__file__).resolve().parent.parent / "src" / "db" / "migrations" / "0001_init.sql"
WORLD_MIGRATION = (Path(__file__).resolve().parent.parent
                   / "src" / "db" / "migrations" / "0003_world_movements.sql")

RECORD_TABLES = ("parties", "policies", "cover_components", "fund_holdings",
                 "bank_mandates", "authority_records", "transactions",
                 "record_changes", "interactions", "cases", "evidence")

# v2 demo relics the records rewrite retires.
RETIRED_TABLES = ("mock_policy_records", "audit_log", "policy_clauses")


def sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def table_block(name: str) -> str:
    """The column definitions of one create-table statement.

    Split on the statement terminator `\\n);`, not the first `;` — a comment
    inside the block may legitimately contain one.
    """
    return sql().split(f"create table if not exists {name}")[1].split("\n);")[0]


# ── the corpus half, unchanged from phase 1 ──────────────────────────────
def test_extensions_for_hybrid_search():
    text = sql()
    assert "create extension if not exists vector" in text
    assert "create extension if not exists pg_trgm" in text


def test_embedding_dimension_matches_the_constants_contract():
    match = re.search(r"embedding\s+vector\((\d+)\)", sql())
    assert match, "kb_chunks must declare an embedding vector column"
    assert int(match.group(1)) == constants.EMBED_DIM


def test_the_corpus_table_is_kb_chunks():
    assert "create table if not exists kb_chunks" in sql()


def test_chunk_id_is_the_primary_key():
    assert re.search(r"chunk_id\s+text\s+primary key", table_block("kb_chunks"))


def test_the_filterable_metadata_columns_exist():
    block = table_block("kb_chunks")
    for column in ("doc", "sec", "aud", "type"):
        assert re.search(rf"\b{column}\s+text\s+not null", block), f"missing {column}"


def test_the_filterable_columns_are_indexed():
    text = sql()
    assert "kb_chunks_aud_idx" in text
    assert "kb_chunks_doc_idx" in text


def test_provenance_and_its_derived_citation_style_are_stored():
    block = table_block("kb_chunks")
    assert "provenance" in block
    assert "citation_style" in block


def test_change_control_columns_support_incremental_reembedding():
    block = table_block("kb_chunks")
    assert "content_hash" in block
    assert re.search(r"version\s+integer\s+not null\s+default\s+1", block)
    assert "superseded_by" in block


def test_hybrid_search_indexes_are_present():
    text = sql()
    assert "tsv" in text and "to_tsvector" in text, "generated tsvector column required"
    assert "using hnsw" in text and "vector_cosine_ops" in text, "HNSW vector index required"
    assert "gin_trgm_ops" in text, "trigram GIN index required"


def test_the_tsvector_covers_the_heading_as_well_as_the_body():
    match = re.search(r"to_tsvector\('english',([^)]*)\)", sql())
    assert match, "generated tsvector column required"
    assert "heading" in match.group(1) and "text" in match.group(1)


# ── the records half ─────────────────────────────────────────────────────
def test_every_record_table_exists():
    text = sql()
    for name in RECORD_TABLES:
        assert f"create table if not exists {name}" in text, f"missing table: {name}"


def test_the_v2_demo_relics_are_retired():
    # The old sandbox-scoped cases table, the mock record store and the audit
    # log belonged to the v2 demo app deleted in phase 0. A comment naming one
    # is fine; a definition of it is not.
    text = sql()
    for name in RETIRED_TABLES:
        assert f"create table if not exists {name}" not in text, f"{name} must be gone"
    assert "sandbox_id" not in text, "the sandbox scoping went with the demo app"


def test_the_relics_are_explicitly_dropped_not_merely_omitted():
    # Phase 1's migration has already run on every live database, so the old
    # tables exist there. `create table if not exists cases` would silently keep
    # the v2 shape — the rewrite has to drop it first.
    #
    # Since v4.5 phase 5 the drops are pinned to current_schema() inside a DO
    # block: an unqualified DROP resolves through the search_path, so a
    # rehearsal apply into a scratch schema would otherwise have reached past
    # it and dropped public's tables. Same intent, scoped delivery — audit_log
    # still first (it references cases), and the old cases still goes before
    # the new one is created.
    text = sql()
    drops = text.index("array['audit_log', 'mock_policy_records', 'cases']")
    assert "current_schema()" in text, "the drops must be schema-scoped"
    assert drops < text.index("create table if not exists cases"), \
        "drop the old cases before creating the new"


def test_policy_numbers_carry_the_kb_grammar():
    # ^(LP|HB|RA)-\d{8}$ — validated in code at construction, and again here so
    # a direct insert cannot bypass it.
    block = table_block("policies")
    assert "LP" in block and "HB" in block and "RA" in block
    assert "check" in block


def test_policies_reference_their_party():
    assert re.search(r"holder_party_id\s+text\s+not null\s+references parties",
                     table_block("policies"))


def test_money_columns_are_integer_pence_not_floats():
    for match in re.finditer(r"(\w*_pence)\s+(\w+)", sql()):
        assert match.group(2) in ("bigint", "integer"), (
            f"{match.group(1)} is {match.group(2)} — money must be integer pence")


def test_no_column_anywhere_is_declared_a_floating_point_type():
    # Matched against column declarations, not prose: the comments legitimately
    # mention numeric and float in explaining why neither is used.
    declarations = re.findall(r"^\s{4}(\w+)\s+(\w+)", sql(), re.M)
    for column, kind in declarations:
        assert kind not in ("numeric", "float", "real", "double"), (
            f"{column} is declared {kind}")


# ── append-only, enforced by the database and not only by the app ────────
def test_transactions_are_append_only_by_trigger():
    text = sql()
    assert "transactions_append_only" in text
    assert re.search(r"create trigger transactions_append_only", text)
    assert re.search(r"before\s+update\s+or\s+delete\s+on\s+transactions", text)


def test_record_changes_are_append_only_by_trigger():
    text = sql()
    assert "record_changes_append_only" in text
    assert re.search(r"before\s+update\s+or\s+delete\s+on\s+record_changes", text)


def test_the_append_only_guard_raises_rather_than_ignoring_the_write():
    # Silently swallowing an update would leave the caller believing it worked.
    assert re.search(r"raise exception", sql(), re.I)


def test_a_transaction_belongs_to_a_policy_and_carries_its_own_time():
    block = table_block("transactions")
    assert "references policies" in block
    assert re.search(r"\bat\s+timestamptz\s+not null", block), (
        "the movement's own timestamp is injected, not defaulted to now()")


def test_the_ledger_sequence_is_unique_per_policy():
    text = sql()
    assert re.search(r"unique\s*\(\s*policy_no,\s*seq\s*\)", text)


def test_record_changes_carry_actor_source_and_injected_time():
    block = table_block("record_changes")
    for column in ("entity_type", "entity_id", "changes", "actor", "source_ref", "at"):
        assert column in block, f"record_changes must carry {column}"


# ── the casework half ────────────────────────────────────────────────────
def test_cases_are_keyed_by_the_cw_grammar():
    block = table_block("cases")
    assert "cw_ref" in block
    assert "CW-" in block


def test_case_type_and_authority_level_are_stored():
    block = table_block("cases")
    assert "type" in block
    assert "authority_level_required" in block


def test_evidence_hangs_off_a_case_and_names_the_rule_that_demanded_it():
    block = table_block("evidence")
    assert "requirement_source" in block, "the KB chunk id that demanded it"
    assert "references cases" in block


def test_evidence_carries_no_money():
    # Recording what someone sent in moves nothing; a money column here would
    # invite the two journals to disagree.
    assert "pence" not in table_block("evidence")


def test_interactions_are_keyed_by_the_cn_grammar():
    block = table_block("interactions")
    assert "cn_ref" in block
    assert "CN-" in block


# ── 0003 — the world's movements (v4.5 phase 1) ──────────────────────────
def world_sql() -> str:
    return WORLD_MIGRATION.read_text(encoding="utf-8")


def test_the_world_movements_migration_exists():
    # A new file rather than an edit to 0001. 0001 is unapplied and carries a
    # pending decision about removing three v2 tables; editing it to widen a
    # vocabulary is how that decision gets taken by accident.
    assert WORLD_MIGRATION.exists(), "0003_world_movements.sql must exist"


def test_the_transaction_kind_vocabulary_is_constrained_in_the_database():
    # 0001 left `kind` a bare `text not null`, so the closed vocabulary existed
    # only in Python and anything holding a connection string could write a
    # movement the application has never heard of.
    assert re.search(r"check\s*\(\s*kind\s+in\s*\(", world_sql()), (
        "the transaction kind vocabulary must be constrained in the schema")


def test_the_database_vocabulary_matches_the_code_exactly():
    # Two copies of a vocabulary is how they end up disagreeing. This is the
    # test that notices — in either direction.
    match = re.search(r"check\s*\(\s*kind\s+in\s*\((.*?)\)\)", world_sql(), re.S)
    assert match, "the kind constraint must list its vocabulary"
    assert set(re.findall(r"'([a-z_]+)'", match.group(1))) == set(ALL_KINDS)


def test_the_four_world_movements_are_accepted():
    listed = set(re.findall(r"'([a-z_]+)'", world_sql()))
    for kind in ("investment_return", "investment_loss", "charge", "bonus"):
        assert kind in listed, f"the database must accept {kind}"


def test_the_migration_creates_and_alters_only():
    # The pending decision 0001 carries is precisely a question about removing
    # tables. This file must add nothing to that question.
    assert "drop" not in world_sql().lower()


def test_the_migration_is_safe_to_run_twice():
    # Postgres has no `add constraint if not exists`, so idempotency is the
    # migration's own job: ask the catalogue before adding.
    text = world_sql()
    assert "pg_constraint" in text, "guard the add against the catalogue"
    assert re.search(r"if\s+not\s+exists", text)
