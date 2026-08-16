-- ---------------------------------------------------------------------------
-- 0002 — the trace store (v4 phase 5)
--
-- A separate migration rather than an addition to 0001_init.sql, for two
-- reasons. 0001 is 357 lines, already past the repo's 300-line rule. And it is
-- the migration deliberately NOT applied, because it drops
-- three v2 tables; adding to it would widen a decision that is still open. This
-- file only creates, so it can be applied on its own whenever that decision
-- lands.
--
-- One row per agent query, shaped by `06-RAGOPS:4.1`. Every number the ops
-- screen shows is a fold over this table, so a figure on the board can always
-- be reproduced from the rows behind it.
--
-- APPEND-ONLY BY INTENT. Nothing here grants update or delete, and the code
-- offers neither. Gate-bypass doubles as a data-breach detector
-- (`06-RAGOPS:4.2`); a record of a breach that can be edited afterwards is not
-- a record of a breach.
-- ---------------------------------------------------------------------------

create table if not exists traces (
    trace_id       text primary key,

    -- The interaction this query belonged to. Nullable because a query can be
    -- asked before any interaction is open — a rules question that names no
    -- policy needs no `CN-` (07-RUNBOOK:4.1) — and a trace that could not be
    -- written in that case would leave the honest path unrecorded.
    cn_ref         text,
    ts             text not null,
    channel        text not null default 'console',

    -- CalmLine's own roles, not the KB's [customer|agent|ops]: the session
    -- holds these three and nothing else can reach the console.
    user_role      text not null
                   check (user_role in ('front_office', 'back_office', 'ops')),

    -- No producer anywhere in the codebase. Nullable and left null rather than
    -- filled from a taxonomy CalmLine never built.
    resolved_intent text,

    -- Retrieval, as it happened: what narrowed it, what came back, what
    -- survived reranking, what the answer actually cited. `cited` carries
    -- {chunk_id, version} pairs, and that pair is what stale_citation_rate
    -- folds over.
    filters_applied  jsonb not null default '{}'::jsonb,
    retrieved        jsonb not null default '[]'::jsonb,
    reranked         jsonb not null default '[]'::jsonb,
    cited            jsonb not null default '[]'::jsonb,

    answer_text      text not null default '',

    -- {flag, reason}. An abstention states its reason — the model enforces it,
    -- and an unexplained one would inflate abstention_rate with nothing behind
    -- it.
    abstained        jsonb not null default '{"flag": false}'::jsonb,
    guardrail_events jsonb not null default '[]'::jsonb,

    -- none | CW-nnnnnnnnn | FC-nnnnnnn | CMP-nnnnnnnn | VULN. Only `CW-` has a
    -- producer today; the rest are the KB's routes, kept as a vocabulary.
    handoff          text,

    -- {retrieve, generate}, split because the two halves fail differently.
    latency_ms       jsonb not null default '{}'::jsonb,

    -- Which model answered, and by which path. NULL model_id on the keyword
    -- path is correct and required: naming a model that never ran is the
    -- pretence `mode` exists to prevent. The pairing is enforced in the schema
    -- type; this constraint keeps the table honest on its own.
    model_id         text,
    mode             text not null check (mode in ('live', 'keyword')),
    constraint traces_mode_names_its_model check (
        (mode = 'live'    and model_id is not null) or
        (mode = 'keyword' and model_id is null)
    ),

    kb_version       text,
    feedback         jsonb,

    created_at       timestamptz not null default now()
);

-- The four slices the ops screen actually makes. `model_id` earns its index
-- from the standing practice of swapping models to compare them on the same
-- questions (D-CL-061): every metric takes that filter, so every metric hits
-- this column.
create index if not exists traces_cn_ref_idx     on traces (cn_ref);
create index if not exists traces_ts_idx         on traces (ts);
create index if not exists traces_user_role_idx  on traces (user_role);
create index if not exists traces_model_id_idx   on traces (model_id);
