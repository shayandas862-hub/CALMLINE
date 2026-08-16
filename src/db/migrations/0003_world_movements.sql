-- ---------------------------------------------------------------------------
-- 0003 — the world's movements (v4.5 phase 1)
--
-- Two hundred policies are about to be built with real financial histories, and
-- a history has to be able to explain its own value: what the fund did, the
-- annual management charge, the bonus added at an interval. Those four kinds
-- are new in `src/records/models.py`; this file teaches the database the same
-- vocabulary.
--
-- It closes a gap as well as widening one. 0001 declared `kind text not null`
-- and nothing more, so the closed vocabulary lived only in Python. Anything
-- holding a connection string could write a movement the application has never
-- heard of — and `pg_store.current_value` sums by asking whether a kind is a
-- known debit, so an unrecognised one would quietly count as a credit and
-- inflate the policy's value. The constraint below is the backstop the
-- architecture already assumes: generation decides correctness, transcription
-- carries it, and the database refuses anything transcription corrupts.
--
-- A separate file rather than an edit to 0001, for the reason 0002 was: 0001 is
-- still unapplied and carries an open decision about three v2 tables. Editing
-- it to widen a vocabulary would settle that decision by accident. This file
-- only creates and alters, so it can be applied whenever 0001 lands.
--
-- SAFE TO RUN TWICE. Postgres has no `add constraint if not exists`, so the add
-- asks the catalogue first.
-- ---------------------------------------------------------------------------

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'transactions_kind_known'
          and conrelid = 'transactions'::regclass
    ) then
        alter table transactions
            add constraint transactions_kind_known check (kind in (
                -- credits — money arriving, and what the fund gave
                'opening',
                'premium',
                'contribution',
                'transfer_in',
                'credit_adjustment',
                'investment_return',
                'bonus',
                -- debits — money leaving, and what the fund took back
                'withdrawal',
                'surrender',
                'payout',
                'claim_payment',
                'regular_withdrawal',
                'segment_surrender',
                'ufpls_payment',
                'debit_adjustment',
                'investment_loss',
                'charge'
            ));
    end if;
end
$$;
