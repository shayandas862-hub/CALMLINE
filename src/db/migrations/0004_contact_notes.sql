-- ---------------------------------------------------------------------------
-- 0004 — somewhere to put a note (v4.5 phase 2)
--
-- Found by checking the schema rather than assuming it: **there is no note
-- field anywhere**. `interactions` (0001, line 294) carries `intent` and
-- `outcome` — two short strings from closed vocabularies — and nothing that
-- could hold what was actually said on a call. The world about to be built
-- generates exactly that, and without this table it would live in the committed
-- files and be absent from the database.
--
-- A note is **attributable and immutable**: what was discussed, who wrote it,
-- when, against which contact and which policy. Append-only, like everything
-- else here that is evidence — a note editable after the call is not a record
-- of the call, it is a record of somebody's later opinion of the call. A
-- correction is a NEW note referencing the one it corrects, so the original
-- stays exactly as written and the sequence shows the handler changed their
-- mind.
--
-- **No new customer-facing reference format.** `docs/CONTEXT.md` lists six
-- grammars and a note is not among them; D-CL-109 settled that a reference
-- format is a real decision rather than a convenience. A note is keyed by a
-- generated identity, exactly as `record_changes` is — the house pattern for an
-- internal journal nobody ever quotes down a telephone.
--
-- CREATES ONLY. No `drop`, no `alter` to an existing table: 0001 is still
-- unapplied and carries an open decision about three v2 tables, and widening a
-- pending decision without asking is how that decision gets made by accident.
--
-- SAFE TO RUN TWICE. Postgres has no `create trigger if not exists`, so the
-- trigger asks the catalogue first — the same shape 0003 uses for its
-- constraint.
-- ---------------------------------------------------------------------------

create table if not exists contact_notes (
    note_id      bigint generated always as identity primary key,

    -- Which contact this was said on, and which policy it was about. Both are
    -- foreign keys so a note about a call that never happened is refused by
    -- the database rather than by a hopeful application check.
    cn_ref       text not null references interactions (cn_ref),
    policy_no    text not null references policies (policy_no),

    -- What was actually said. A blank note is not a record of anything.
    body         text not null check (length(btrim(body)) > 0),

    -- Who wrote it, and when they wrote it. `written_at` is supplied by the
    -- caller and never defaulted to now(), so a historical note carries the
    -- time of the call rather than the time of the load.
    author       text not null check (length(btrim(author)) > 0),
    written_at   timestamptz not null,

    -- A correction points at what it corrects. Null for an original.
    corrects_id  bigint references contact_notes (note_id),

    recorded_at  timestamptz not null default now()
);

create index if not exists contact_notes_cn_ref_idx
    on contact_notes (cn_ref, note_id);

create index if not exists contact_notes_policy_idx
    on contact_notes (policy_no, written_at);

-- Append-only is enforced by a TRIGGER, not by convention — the same guarantee
-- 0001 gives `transactions` and `record_changes`, and for the same reason: it
-- has to hold for anything holding a connection string, not only for the
-- application's own write path. `refuse_mutation()` is defined in 0001.
do $$
begin
    if not exists (
        select 1
        from pg_trigger
        where tgname = 'contact_notes_append_only'
          and tgrelid = 'contact_notes'::regclass
    ) then
        create trigger contact_notes_append_only
            before update or delete on contact_notes
            for each row execute function refuse_mutation();
    end if;
end
$$;
