-- CalmLine — schema v4 (rewritten in place, D-CL-006 precedent).
-- Apply to the CalmLine Supabase project,
-- via the Supabase SQL editor or `apply_migration`.
--
-- TWO HALVES, mirroring the two stores the whole system is built on:
--
--   the corpus half   — `kb_chunks`, the Aldercrest knowledge base and the ONLY
--                       corpus the agent may cite. Written and applied in v4
--                       phase 1; phase 2 does not touch it.
--   the records half  — the system of record: parties, policies, per-product
--                       detail, the money ledger and the change journal, plus
--                       interactions, cases and evidence. Facts live here.
--
-- Rules come from the first, facts from the second, and nothing crosses over.
--
-- The v2 demo relics (`mock_policy_records`, `audit_log` and the old
-- sandbox-scoped `cases`) are retired with this rewrite: the demo app they
-- served was deleted in v4 phase 0.

-- pgvector powers embedding search; pg_trgm powers the trigram keyword index.
-- Hybrid search (vector + tsvector, RRF-merged) comes from the vendored pipeline.
create extension if not exists vector;
create extension if not exists pg_trgm;

-- ---------------------------------------------------------------------------
-- The knowledge base. 441 chunks are parsed from data/kb/ by
-- src/corpus/kb_parser.py and 438 are seeded here. The three
-- type='sample_record' chunks are NEVER INSERTED AT ALL (AD-CL-023) — not
-- merely inserted without an embedding, because `tsv` below is
-- `generated always`, so any row present is reachable by keyword search even
-- with a null vector. Facts come from the system of record; no policy record
-- may sit in the retrieval index to be cited stale. Phase 2 seeds the book from
-- those three chunks' markdown directly.
--
-- chunk_id ('doc:sec', e.g. '02-BOND:4.4') is the real primary key, not a
-- surrogate: it derives from the section number, so re-wording never moves a
-- citation and every re-seed upserts idempotently.
--
-- Dimension 1536 = src/constants.EMBED_DIM (OpenAI text-embedding-3-small),
-- guarded by tests/test_migration.py.
create table if not exists kb_chunks (
    chunk_id       text primary key,
    -- filterable metadata — retrieval is filter-then-search, and `aud` is
    -- derived from the server-side session, never from the client.
    doc            text not null,
    sec            text not null,
    aud            text not null,
    type           text not null,
    -- provenance drives citation behaviour: the raw `data=` value is kept
    -- alongside its derived style so the derivation can be re-run without
    -- re-parsing the markdown (AD-CL-027).
    provenance     text not null,
    citation_style text not null
                   check (citation_style in ('cite_source', 'aldercrest_standard',
                                             'mixed_explain', 'effective_date_required')),
    heading        text not null,
    heading_path   text not null,
    text           text not null,
    token_estimate integer not null,
    -- change control (data/kb/README.md §5): hash unchanged -> skip the embed;
    -- changed -> re-embed, same id, version + 1; id gone -> tombstone by setting
    -- superseded_by, never a silent drop.
    content_hash   text not null,
    version        integer not null default 1,
    superseded_by  text references kb_chunks (chunk_id),
    embedding      vector(1536),
    -- the heading is indexed with the body: 15 chunks are section headers whose
    -- prose lives in their subsections, and body-only indexing would make them
    -- unreachable by keyword.
    tsv            tsvector generated always as
                   (to_tsvector('english', heading || ' ' || text)) stored,
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);

create index if not exists kb_chunks_embedding_hnsw_idx
    on kb_chunks using hnsw (embedding vector_cosine_ops)
    with (m = 16, ef_construction = 64);

create index if not exists kb_chunks_tsv_idx
    on kb_chunks using gin (tsv);

create index if not exists kb_chunks_trgm_idx
    on kb_chunks using gin (text gin_trgm_ops);

-- filter-then-search: these two run before the similarity ordering.
create index if not exists kb_chunks_aud_idx on kb_chunks (aud);
create index if not exists kb_chunks_doc_idx on kb_chunks (doc);

-- ---------------------------------------------------------------------------
-- Retiring the v2 demo relics.
--
-- These served the demo app deleted in v4 phase 0 and were left behind by
-- phase 1's corpus-only rewrite. They are DROPPED rather than left in place
-- because `cases` shares its name with the v4 table and nothing else: the old
-- one was sandbox-scoped, with a different key and a different state machine.
-- `create table if not exists` would silently keep the wrong shape on any
-- database where phase 1's migration has already run — which is every one of
-- them. audit_log goes first: it references cases.
--
-- Destructive by design, and safe here: no v4 code reads any of the three.
--
-- Scoped to the schema being migrated (v4.5 phase 5): an unqualified DROP
-- resolves through the search_path, so a rehearsal apply into a scratch
-- schema — whose search_path keeps `public` for the extension types — would
-- otherwise reach past the scratch schema and drop public's tables. The
-- relics are retired wherever THIS apply is running, and nowhere else.
-- audit_log still goes first: it references cases.
do $$
declare
    relic text;
begin
    foreach relic in array array['audit_log', 'mock_policy_records', 'cases']
    loop
        if to_regclass(format('%I.%I', current_schema(), relic)) is not null then
            execute format('drop table %I.%I', current_schema(), relic);
        end if;
    end loop;
end
$$;

-- ---------------------------------------------------------------------------
-- THE RECORDS HALF — the system of record.
--
-- Money is integer PENCE everywhere (bigint, never numeric or float), so a
-- balance is exact and a rounding rule can never creep into storage.
-- Every time a row states is INJECTED by the caller; only bookkeeping columns
-- default to now(), because the system's own clock is not a business fact.
-- ---------------------------------------------------------------------------

create table if not exists parties (
    party_id            text primary key
                        check (party_id ~ '^PH-[0-9]{4}$'),
    name                text not null,
    dob                 date not null,
    registered_address  text not null,
    contact             jsonb not null default '{}'::jsonb,
    scottish_taxpayer   boolean not null default false,
    -- special-category care: a reference and a category, never the detail.
    vulnerability_flag  jsonb,
    -- a cached snapshot; the verification history is authoritative (phase 3).
    id_verified_level   text check (id_verified_level in ('SV', 'EV')),
    id_verified_at      timestamptz,
    created_at          timestamptz not null default now()
);

-- The three per-product grammars (KB `05-OPS:1.4`). Validated in code at
-- construction and again here, so a direct insert cannot bypass the rule.
create table if not exists policies (
    policy_no           text primary key
                        check (policy_no ~ '^(LP|HB|RA)-[0-9]{8}$'),
    product             text not null
                        check (product in ('lifelong_protection', 'horizon_bond',
                                           'retirement_account')),
    status              text not null default 'in_force'
                        check (status in ('in_force', 'lapsed', 'paid_up',
                                          'claimed', 'surrendered')),
    start_date          date not null,
    holder_party_id     text not null references parties (party_id),
    lives_assured       jsonb not null default '[]'::jsonb,
    lives_assured_basis text not null default 'single'
                        check (lives_assured_basis in ('single', 'joint_last_survivor')),
    trust               jsonb,
    adviser_loa         jsonb,
    bank_last4          text check (bank_last4 ~ '^[0-9]{4}$'),
    created_at          timestamptz not null default now()
);

create index if not exists policies_holder_idx on policies (holder_party_id);
create index if not exists policies_product_idx on policies (product);

-- Lifelong Protection only. `basis` is a SET of bases: the LP sample record
-- reads "reviewable, unit-linked" — the charge basis and the investment basis
-- are separate axes and a policy carries both (D-CL-037).
create table if not exists cover_components (
    policy_no          text primary key references policies (policy_no),
    sum_assured_pence  bigint not null check (sum_assured_pence >= 0),
    basis              text[] not null check (array_length(basis, 1) >= 1),
    premium_pence      bigint not null check (premium_pence >= 0),
    premium_frequency  text not null default 'monthly'
                       check (premium_frequency in ('monthly', 'yearly')),
    next_collection    date,
    riders             text[] not null default '{}',
    next_review_date   date,
    indexation         jsonb not null default '{}'::jsonb
);

-- Horizon Bond and Retirement Account, one row per fund.
-- `amc_bp` is basis points (0.65% -> 65) so the charge is an exact integer.
create table if not exists fund_holdings (
    id          bigint generated always as identity primary key,
    policy_no   text not null references policies (policy_no),
    fund_id     text not null,
    fund_name   text not null,
    split_pct   integer not null check (split_pct between 1 and 100),
    amc_bp      integer not null check (amc_bp >= 0),
    price_date  date not null,
    pathway     integer check (pathway between 1 and 4),
    unique (policy_no, fund_id)
);

-- Policy-level product terms. One row per policy, shaped by its product:
-- the bond's segments and 5% allowance, the pension's contributions,
-- transfers-in, expression of wish and tax state.
create table if not exists product_terms (
    policy_no   text primary key references policies (policy_no),
    bond_terms  jsonb,
    pension_terms jsonb,
    pension_tax jsonb
);

-- The control state behind a policy's displayed bank_last4. `change_history`
-- is the fraud watch: "bank changed, then a large withdrawal two weeks later"
-- is only answerable because it is kept.
create table if not exists bank_mandates (
    policy_no       text primary key references policies (policy_no),
    account_last4   text not null check (account_last4 ~ '^[0-9]{4}$'),
    verified        boolean not null default false,
    hold_until      date,
    change_history  jsonb not null default '[]'::jsonb
);

-- Third parties are first class (AD-CL-033): the identity gate checks these
-- and enforces their scope in code.
create table if not exists authority_records (
    authority_id   text primary key,
    policy_no      text not null references policies (policy_no),
    party_id       text not null,
    type           text not null
                   check (type in ('LOA', 'LPA', 'EPA', 'deputy', 'PR',
                                   'trustee', 'mandate', 'one_off')),
    scope          text[] not null default '{}',
    evidence_ref   text not null default '',
    verified_date  date,
    status         text not null default 'unverified'
                   check (status in ('active', 'expired', 'unverified', 'revoked'))
);

create index if not exists authority_records_policy_idx
    on authority_records (policy_no);

-- ---------------------------------------------------------------------------
-- The money journal. Append-only is enforced by a TRIGGER, not by convention:
-- the application has exactly one write path (`src/casework/approval.py`), and
-- this makes that true of the database as well, for anything holding a
-- connection string.
create table if not exists transactions (
    txn_id               text primary key,
    policy_no            text not null references policies (policy_no),
    seq                  integer not null,
    kind                 text not null,
    amount_pence         bigint not null check (amount_pence >= 0),
    balance_after_pence  bigint not null check (balance_after_pence >= 0),
    reason               text not null default '',
    actor                text not null,
    -- the movement's own time, supplied by the caller — never defaulted to now()
    at                   timestamptz not null,
    recorded_at          timestamptz not null default now(),
    unique (policy_no, seq)
);

create index if not exists transactions_policy_at_idx
    on transactions (policy_no, at);

-- ---------------------------------------------------------------------------
-- The non-money journal (D-CL-026): every mutating store operation lands here
-- with who did it, what it came from and when. The ledger above journals money;
-- this journals everything else, so "every change is auditable" is literal
-- across the whole store and any past state is replayable.
create table if not exists record_changes (
    seq          bigint generated always as identity primary key,
    entity_type  text not null,
    entity_id    text not null,
    changes      jsonb not null default '[]'::jsonb,
    actor        text not null,
    -- always a case, an interaction, or the seed — never an unattributed edit.
    source_ref   text not null
                 check (source_ref ~ '^(CW-[0-9]{9}|CN-[0-9]{10}|seed)$'),
    at           timestamptz not null,
    recorded_at  timestamptz not null default now()
);

create index if not exists record_changes_entity_idx
    on record_changes (entity_type, entity_id, seq);

-- Both journals refuse to be rewritten. Raising rather than silently ignoring
-- the write matters: a swallowed UPDATE leaves the caller believing it worked.
create or replace function refuse_mutation() returns trigger as $$
begin
    raise exception 'append-only: % on % is not permitted', tg_op, tg_table_name;
end;
$$ language plpgsql;

drop trigger if exists transactions_append_only on transactions;
create trigger transactions_append_only
    before update or delete on transactions
    for each row execute function refuse_mutation();

drop trigger if exists record_changes_append_only on record_changes;
create trigger record_changes_append_only
    before update or delete on record_changes
    for each row execute function refuse_mutation();

-- ---------------------------------------------------------------------------
-- Contact, casework and the things customers send in.

-- One inbound or outbound contact (`CN-` + 10). A seeded historical row may
-- carry no channel: a sample record says what happened and when, not through
-- which channel, and a gap is more honest than a guess.
create table if not exists interactions (
    cn_ref                text primary key
                          check (cn_ref ~ '^CN-[0-9]{10}$'),
    policy_no             text not null references policies (policy_no),
    opened_at             timestamptz not null,
    channel               text check (channel in ('phone', 'portal', 'email',
                                                  'post', 'adviser_portal')),
    caller_party_id       text,
    claimed_relationship  text not null default '',
    verification_ref      text,
    intent                text not null default '',
    outcome               text not null default '',
    closed_at             timestamptz
);

create index if not exists interactions_policy_idx on interactions (policy_no);

-- The back office's work item (`CW-` + 9). The AI never moves a case past
-- pending_review; completing one requires the human click.
create table if not exists cases (
    cw_ref                    text primary key
                              check (cw_ref ~ '^CW-[0-9]{9}$'),
    policy_no                 text not null references policies (policy_no),
    request                   text not null,
    type                      text not null default 'servicing'
                              check (type in ('servicing', 'DSAR', 'transfer',
                                              'review', 'claim_linked')),
    authority_level_required  text,
    priority                  text not null default 'medium'
                              check (priority in ('high', 'medium', 'low')),
    status                    text not null default 'pending_review'
                              check (status in ('pending_review', 'completed',
                                                'blocked', 'held_for_review')),
    recommendation            text check (recommendation in ('proceed', 'do_not_proceed')),
    checklist                 jsonb not null default '[]'::jsonb,
    human_decision            text,
    sla_due                   timestamptz,
    created_at                timestamptz not null default now(),
    audit                     jsonb not null default '[]'::jsonb
);

create index if not exists cases_status_sla_idx on cases (status, sla_due);

-- "The things they have sent in" (§3.2 step 8). NOT a ledger row — recording
-- what arrived moves no money, which is why there is no amount column here.
-- `requirement_source` is the chunk id of the KB rule that demanded it, so
-- "why did we ask for this" is answerable.
create table if not exists evidence (
    evidence_id         text primary key,
    cw_ref              text not null references cases (cw_ref),
    policy_no           text not null references policies (policy_no),
    requirement         text not null,
    requirement_source  text not null,
    description         text not null default '',
    received_via        text not null default 'post'
                        check (received_via in ('phone', 'portal', 'email',
                                                'post', 'adviser_portal')),
    received_at         timestamptz,
    taken_by            text not null default '',
    satisfies           text not null default 'unverifiable'
                        check (satisfies in ('yes', 'no', 'unverifiable'))
);

create index if not exists evidence_case_idx on evidence (cw_ref);
