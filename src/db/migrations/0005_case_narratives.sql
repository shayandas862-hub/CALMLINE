-- ---------------------------------------------------------------------------
-- 0005 — somewhere to put a case narrative (v4.5 phase 5)
--
-- Found the way 0004 was found: by checking the schema against what phase 4
-- actually wrote. `stories.jsonl` carries TWO kinds of prose — 1,406 contact
-- notes and 476 case narratives — and the schema has a home only for the
-- first. `contact_notes` (0004) requires a `cn_ref`, and a narrative belongs
-- to a case, not to a call: a case can gather evidence across weeks and the
-- narrative is the write-up of the piece of work, not of any one contact.
-- Without this table the load would report success having quietly left a
-- third of the hand-written prose behind — the exact failure the loader
-- exists to make impossible.
--
-- The shape is 0004's, deliberately, and for the same reasons: attributable
-- and immutable, a correction is a NEW row pointing at what it corrects, and
-- `written_at` is supplied by the caller so a historical narrative carries
-- the date of the work rather than the date of the load.
--
-- CREATES ONLY, SAFE TO RUN TWICE — guarded creates, catalogue-checked
-- trigger, same as 0003 and 0004. `refuse_mutation()` is defined in 0001.
-- ---------------------------------------------------------------------------

create table if not exists case_narratives (
    narrative_id bigint generated always as identity primary key,

    -- Which piece of work this narrates, and which policy it was about. Both
    -- are foreign keys so a narrative about a case that never happened is
    -- refused by the database rather than by a hopeful application check.
    cw_ref       text not null references cases (cw_ref),
    policy_no    text not null references policies (policy_no),

    -- The write-up itself. A blank narrative is not a record of anything.
    body         text not null check (length(btrim(body)) > 0),

    author       text not null check (length(btrim(author)) > 0),
    written_at   timestamptz not null,

    -- A correction points at what it corrects. Null for an original.
    corrects_id  bigint references case_narratives (narrative_id),

    recorded_at  timestamptz not null default now()
);

create index if not exists case_narratives_cw_ref_idx
    on case_narratives (cw_ref, narrative_id);

create index if not exists case_narratives_policy_idx
    on case_narratives (policy_no, written_at);

do $$
begin
    if not exists (
        select 1
        from pg_trigger
        where tgname = 'case_narratives_append_only'
          and tgrelid = 'case_narratives'::regclass
    ) then
        create trigger case_narratives_append_only
            before update or delete on case_narratives
            for each row execute function refuse_mutation();
    end if;
end
$$;
