# The writing brief — how a contact note and a case narrative are written

> **The standing instruction.** Written down rather than held in a session, so
> the 1,882nd piece is written to the same standard as the first.
>
> Every figure quoted below was measured from the committed dataset. Where this
> brief forbids something, it is because the numbers will not support it — not
> because it is bad style.

## What is being written

**1,406 contact notes** — one per contact — and **476 case narratives** — one per
case — across **189 policies**. Eleven policies have no contacts and get nothing.

The prose goes in `data/world/stories.jsonl` and **nowhere else**. `note_slot` in
`policies.jsonl` stays empty: that file is regenerated from a seed and would take
anything written into it.

**The policy is the unit of work.** Read one policy's whole history, write its
notes and narratives, save, move on. Do not write twenty policies at once —
twenty policies summarised in one pass produces twenty variations of one story,
and that is the single thing this phase exists to avoid.

## The voice

A handler writing up a contact **just after it happened**, into a system other
handlers will read. Not a letter to the customer, not a report to a manager.

- **Past tense, third person.** "Called to ask about…", not "I spoke to…".
- **Terse.** One to three sentences for a note. Two to four for a narrative.
- **No sign-off, no greeting, no name of the handler.** The system records who
  wrote it; the note does not.
- **Plain.** No "customer advises", no "as per", no "kindly". Handlers write
  quickly, not badly.
- **The caller is a person, not "the customer" every time.** "He"/"she"/"they",
  "the holder", their age when the record supports it. **Never their name** —
  the validator refuses names by design, because the world's placeholder names
  ("Prism Quasar 75") identify nobody and would wreck the voice.

**Habits to break — added by the task-5 review after the first ninety-two
notes were read back:**

- **Vary the explaining verb.** "Explained that…" opened a sixth of the first
  batch's second sentences. Told, set out, went through, confirmed, talked
  through — or no scaffold at all, when the explanation is the note.
- **Vary the refusal record.** The *rule* — a failed verification discloses
  nothing — is absolute; the sentence "could not be verified, so nothing was
  confirmed or disclosed" must not become a stamp. Record instead what they
  asked for, what they were told to send in, or that the standard letter went.
- **Make the caller a person without a name.** The review first recommended
  names; the task-4 validator refused them, and it is right — the world's
  placeholder names would read absurdly in a handler's note. Personhood comes
  from age, circumstance and continuity instead: "he was 51 and short of the
  minimum age", "the third such approach on this number".
- **Let length follow content.** "Updated and confirmed back." is a complete
  note. A complaint can run four sentences. The action–explanation–outcome
  three-beat is a default, not a metre.

**Match the channel.** This is checkable and it is got wrong constantly:

| Channel | The note opens like |
|---|---|
| `phone` | "Called to…", "Rang about…" |
| `email` | "Emailed asking…", "Wrote in about…" |
| `post` | "Letter received…", "Wrote in…" |
| `portal` | "Message through the portal…", "Submitted online…" |
| `adviser_portal` | "Request in through the adviser portal…" — see below |

A `post` contact did not ring up. An `email` contact was not on the telephone.

**`adviser_portal` now implies an adviser mandate — reconciled, then verified.**
240 of the 301 `adviser_portal` contacts used to sit on policies with no mandate;
the generation now remaps those to ordinary channels, and
`tests/test_world_consistency.py` holds the line. So an `adviser_portal` contact
may honestly be written as the firm or its named individuals acting — check
`cast_for` for who they are. Everywhere else, write the substance, not the
sender.

## Variety comes from the lives, not from being asked for it

A pension that lapsed in 2011 and a bond surrendered after a bereavement do not
need to be told to sound different. **Read the actual history and write what it
says.** If two notes come out the same, it is usually because the history was not
read, not because the world is uniform.

What genuinely differs, policy to policy, and is worth using:

- **the product** — a whole-of-life policy, an onshore bond and a personal
  pension are three different conversations
- **the status** — a lapsed policy, a paid-up one and one still running
- **the events** — a lapse, a premium review, a chargeable event, a death and
  claim, an MPAA trigger
- **the money** — a £600-a-year pension and a £29,000 bond are not the same call
- **the outcome** — the five below are five different notes
- **the evidence requirement** — twelve distinct ones, and they are the reason a
  case took the shape it did

## The five outcomes, and what each note has to do

| Outcome | Count | The note must |
|---|---|---|
| `case_raised` | 476 | end by saying work was raised — the case follows |
| `information_given` | 242 | say what was told them; nothing changed |
| `refused_verification` | 239 | 🔴 record that the caller **could not be verified** |
| `referred` | 237 | say who it went to, and why it was not dealt with there |
| `resolved` | 212 | say what was done and that it was finished on the contact |

🔴 **`refused_verification` is the one that matters most.** 239 notes — one in
six. The caller failed the identity gate, so **nothing about the policy was
disclosed to them.** The note therefore may not contain the value, the address,
the premium, the fund, or anything else off the record. It records what was
asked for, that verification failed, and what they were told to do instead.

A `refused_verification` note that quotes the policy's value is a data breach
written down. This is the product's entire subject; get it right here.

## What the numbers will not support

**Rule 5 applies to prose.** A figure in a note that is in no ledger row is a
fabricated number wearing a sentence, and it is harder to catch than one in a
table. Every amount, date and event in a note must be in that policy's record.

Five things the world does not have. **Do not write around them by inventing
them:**

1. **The premium is usually flat.** 43 of 70 protection policies post a premium
   and an identical same-day charge, to the penny, for up to 32 years. **Do not
   write that a premium was reviewed upward unless the ledger moved** — and check,
   because sometimes it did: `LP-20000137` goes £120.00 → £141.60 in 2024, after a
   `premium_review` recording `premium_increased`.
2. **A `premium_review` recording `unsustainable` has no visible consequence.**
   24 of them. The consequence would have been to the cover, and the cover has no
   history. Write the review and what was said about it; do not write a new
   premium or a reduced sum assured, because neither figure exists.
3. **The cover has a figure but no history.** Read `_headline` before quoting
   anything: `headline_value_pence` is the **sum assured** on a protection
   policy — `LP-20002055`'s death benefit paid £9,944.39 against a headline of
   exactly £9,944.39 — so a protection policy's *current* cover can be stated.
   What does not exist is what it was **before** each of the 449 indexations and
   152 reviews. *"Why has my cover gone down?"* is a conversation you can write;
   **the earlier amount is not.**

   🔴 **On a bond or a pension `headline_value_pence` is not the value.** It is
   `max(current fund, highest the fund ever reached)`, so on `HB-20002740` the
   headline is £31,738.54 and the fund is £17,568.30. It is the most prominent
   number on the record and quoting it as "what the policy is worth" is wrong by
   £14,170.24 on that one policy alone. **The current value is the last
   `balance_after_pence` in the ledger, and nothing else.**
4. **Recurring amounts never vary.** 141 policies repeat one figure eight times or
   more — `HB-20002740` takes exactly £1,461.35 every year for eleven years. **Do
   not write "asked us to increase it"**, or a review of the withdrawal, or an
   indexation of it. It was the same every year, and the note should read like
   somebody doing the same thing again.
5. **466 cases are `servicing` and 10 are `claim_linked`, each with one evidence
   item.** The ten are the death claims. Do not narrate a transfer, a DSAR or a
   review the case record does not carry, and do not invent a second piece of
   evidence.
6. **A lapse now states its own arithmetic — use it.** Every whole-of-life
   `lapse` detail names the missed due date, and the event date is that plus the
   30-day grace (plus the stated months of unit-cancellation where a fund
   carried the cover). Both dates are on the record; quote them, and never
   invent a different interval.

**Some contact arrives after the policy closed.** People do ring about closed
policies, so write it as what it is — a query on a finished policy — not as live
business. Do not write a withdrawal being paid from a lapsed plan.

## Nobody may be invented — and nobody may be borrowed

Every person a story names must exist in `people.jsonl` **and hold that role on
that policy**. `world/stories/validate.py` asserts this over the whole world,
offline, forever.

**115 of the 200 policies have no third party at all.** On those, the only person
the note may refer to is the holder. A trustee of somebody else's policy is a
stranger to this one.

`world.stories.workfile.cast_for(world, policy_no)` is the list. Read it before
referring to anyone.

### 🔴 Refer to people by their **role**, never by their name

**Measured: the world's names do not identify anybody.** Full names are unique
across all 299 people, but **only because each carries a trailing number** —
`Alpha Feldspar 2` is a trustee and `Alpha Feldspar 265` is a policyholder, and
they are different people. 49 two-word name prefixes are shared by two or more
people; `Omega Nimbus` is **four** people across three roles; all 299 share just
**30 surnames**, one of which covers 18 of them.

So "Mr Feldspar rang" is ambiguous by construction, and "Alpha Feldspar 2 rang"
reads like a serial number rather than a person and would undo the realism this
phase exists to produce.

**Write the role: "the trustee", "both trustees", "her attorney", "the deputy",
"the personal representative".** This is what real handler notes do anyway — the
system already shows the name beside the note, so the handler writes the
relationship, which is the part that is not on screen.

The rule that follows, and the one `validate.py` enforces: **a note may claim a
role only if this policy's cast holds it.** "The trustee instructed us" on a
policy with no trust is a failure, exactly as the card describes — and it is a far
stronger check than matching names, because the role is the thing that carries
authority.

**The holder is the exception**, and is normally just "he", "she", "they" or "the
holder" — a note rarely names the person whose file it is.

**`AF-` is a firm, not a person.** The firm has a name and a reference and no date
of birth; the people it has authorised are the `PH-3xxx` party ids on the mandate.
"The adviser rang" is fine when the mandate names individuals; "Mr Cornice rang"
requires `PH-3001` to be on *this* policy's mandate.

### The operational record was reconciled with the parties — write to the evidence

The fault phase 4 first measured here — 112 cases asserting a trustee, adviser
or attorney the policy does not have — **is fixed at generation** and locked by
`tests/test_world_consistency.py`: every evidence requirement and every refusal
reason now names only parties the policy holds. So the narrative may follow the
evidence exactly: if it says trustee signatures were obtained, the trust and its
trustees are real and `cast_for` lists them.

The standing rules survive the fix, because they are what the validator
enforces: **never name a party the cast does not hold**, and **do not invent a
requirement** to make a narrative easier than the evidence.

## The shape of a note

Three things, in this order, and not all of them every time:

1. **what they wanted** — from `intent`, but in their words, not the category's
2. **what happened** — verification, what was said, what was checked
3. **where it went** — resolved, raised as a case, referred, or refused

`intent`, `outcome` and `channel` are **closed vocabularies, not sentences.**
"Requested a withdrawal" is a category. What the caller actually said is the note.
Never write the category verbatim into the prose — no note should contain the
string `withdrawal_request`.

**Examples, from real rows.** These are the register, not templates to fill:

> `HB-20002740` · `CN-2002740009` · phone · withdrawal_request · case_raised
> *"Rang to set up the annual withdrawal again, same as last year. Confirmed
> identity and the account it goes to. Raised for the December run."*

> `LP-20000137` · `CN-1000137006` · post · withdrawal_request · refused_verification
> *"Wrote in asking to take money out of the plan. The details given did not match
> the record and we could not verify the writer, so nothing was confirmed or
> disclosed. Wrote back explaining what we need."*

> `RA-20001507` · `CN-3001507011` · phone · complaint · resolved
> *"Unhappy that the tax taken on the lump sum was more than expected. Talked
> through how it was worked out and why the allowance applies once. Accepted the
> explanation and did not want it taken further."*

## The shape of a case narrative

**Why the case was raised, what was needed, and what was decided.** Two to four
sentences. It is written by the person who worked it, not the person who took the
call, so it does not repeat the note — it carries on from it.

A `refused` decision — 39 of 473 — must say what was not satisfied, in the terms
the evidence uses, subject to the rule above about absent parties.

Money that moved must match `authorised_movement_on` and the ledger row behind it.
It is usually **later than the case closed** — often the next policy anniversary —
and a narrative that says the money went out the same day is wrong.

## Before saving a policy

- [ ] every contact has a note, every case a narrative — no holes
- [ ] no figure that is not in the ledger; no date that is not in the record
- [ ] nobody named who is not in this policy's cast
- [ ] `refused_verification` notes disclose nothing
- [ ] the channel matches how they got in touch
- [ ] no category string in the prose
- [ ] read the policy's notes end to end: does it read like **one person's** file?
