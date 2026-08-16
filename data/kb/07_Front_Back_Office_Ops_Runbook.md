# DOCUMENT 7 — FRONT OFFICE, BACK OFFICE & OPERATIONS RUNBOOK
*meta: doc=07-RUNBOOK | sec=frontmatter | aud=all | type=caveats | data=mixed*
## Aldercrest Life Assurance plc — how the operation actually runs
*meta: doc=07-RUNBOOK | sec=frontmatter-title | aud=all | type=caveats | data=mixed*

**Version 2026.1 | Effective 13 July 2026 | Owner: Chief Operating Officer | Classification: Internal — RAG Knowledge Base**

> **Why this document exists:** Document 5 says *what* must be done and by whom. This runbook says *how the operation runs* — the call lifecycle, case states, maker-checker controls, payment rails, gone-away and unclaimed handling, error remediation, incident management, QA and workforce practice, and the governance limits on the AI assistant itself. It is the layer that turns procedures into a working front office, back office and ops function.
> **Grounding:** Aldercrest operating standards (codes, thresholds, scripts, sampling rates) are fictional but realistic. Regulatory anchors (DISP, FG21/1, PS21/3, PECR, UK GDPR, Equality Act, Dormant Assets Act 2022, Confirmation of Payee) are real and sourced in §10.
> **RAG convention:** every `##`/`###` is one chunk; tables and §10 are atomic; each section carries a `meta:` line.

---

## 1. OPERATING MODEL OVERVIEW

### 1.1 The three functions and the handoffs between them
*meta: doc=07-RUNBOOK | sec=1.1 | aud=all | type=overview | data=fictional*
**Front office** owns the contact: identify, verify, resolve within authority, or capture and hand off. **Back office** owns the case: evidence, processing, controls, payment. **Ops** owns the system: queues, quality, incidents, MI, regulatory returns. The handoffs are explicit artefacts, not conversations — front office creates a `CW-` case with mandatory fields and evidence attached; back office returns work to front office only via a customer-contact request; ops intervenes through queue reprioritisation, QA feedback and incident command. Every handoff carries the `CN-` interaction id so the audit trail is unbroken end to end.

### 1.2 Operating hours, coverage and escalation windows
*meta: doc=07-RUNBOOK | sec=1.2 | aud=ops | type=ops | data=fictional*
Contact centre 08:00–18:00 Mon–Fri, 09:00–13:00 Sat (bereavement line only). Back office 08:30–17:00 Mon–Fri. Ops duty manager on call 07:00–19:00; major-incident on-call 24/7. Bereavement and vulnerability escalations are answered within the same session — never queued to a callback unless the customer asks. Payment cut-off 15:00 (§5.2).

### 1.3 Target operating metrics
*meta: doc=07-RUNBOOK | sec=1.3 | aud=ops | type=table | data=fictional*
Calls answered within 60 seconds: **80%**. Abandonment: **<5%**. First-contact resolution: **≥70%** of servicing intents. Case SLA attainment: **≥95%**. QA pass rate: **≥90%**. Complaint volume: **<0.5%** of contacts. Verification-failure rate: monitored, no target (a rising rate signals either fraud pressure or a broken script). AI containment (resolved without human): tracked, **never targeted** — a containment target would incentivise the assistant to answer things it should escalate (§8.6).

---

## 2. FRONT OFFICE — CONTACT LIFECYCLE

### 2.1 Call open: greeting, recording notice and intent capture
*meta: doc=07-RUNBOOK | sec=2.1 | aud=customer | type=script | data=mixed*
Standard open: *"Good morning, Aldercrest Life, [name] speaking. Calls are recorded for training and security. How can I help today?"* The recording notice is required at the point of collection — recordings are personal data under UK GDPR and the notice supports the transparency duty (Art 13); retention 7 years (Doc 5 §4.10). Capture the **intent in the customer's own words** before navigating any system — the assistant classifies against the intent taxonomy (Doc 5 §20), but the verbatim is retained on `CN-` for QA and complaint-recognition review.

### 2.2 Verification stage: what the agent may and may not say
*meta: doc=07-RUNBOOK | sec=2.2 | aud=back_office | type=script | data=mixed*
Run SV (Doc 5 §3.2) **before** any policy-specific statement. Permitted pre-verification: general product information, opening hours, how to write in, that a bereavement team exists. **Prohibited pre-verification:** confirming a policy exists, confirming a name or address held on file, confirming a payment was made, or "helpfully" correcting a caller's wrong detail — correction is itself disclosure. If the caller supplies a detail that is wrong, do not say which element failed; say *"I'm not able to verify enough detail to continue on this call"* and offer the secure route (Doc 5 §3.5). Never read back a memorable word or full bank number.

### 2.3 Do-not-say list (advice boundary and disclosure limits)
*meta: doc=07-RUNBOOK | sec=2.3 | aud=customer | type=script | data=mixed*
Front office and the AI assistant are **information-only**. Prohibited: "you should", "the best option for you is", "I'd recommend", any comparison framed as a recommendation, any tax computation presented as advice, any prediction of investment performance, any assurance a claim will be paid before assessment. Permitted: factual explanation of options and consequences, signposting to a regulated adviser, **Pension Wise/MoneyHelper**, or the customer's own accountant. This is the line between information and **regulated advice** — crossing it is both a conduct breach and a Consumer Duty failure. Scripted redirect: *"I can explain how each option works, but I can't tell you which to choose — for that you'd want regulated advice."*

### 2.4 Hold, transfer and warm handoff
*meta: doc=07-RUNBOOK | sec=2.4 | aud=back_office | type=procedure | data=fictional*
Explain before holding, give an expected duration, return within 2 minutes or check back. **Warm transfer** (agent briefs the receiving team while the customer waits) is mandatory for: bereavement, suspected vulnerability, suspected fraud, and any complaint. **Cold transfer** is permitted only for routine misroutes. The receiving agent must not ask the customer to re-verify from scratch where the transferring agent has already completed SV and records it on `CN-` — repeat verification of a bereaved or distressed customer is a recognised harm.

### 2.5 Complaint recognition at first contact
*meta: doc=07-RUNBOOK | sec=2.5 | aud=back_office | type=procedure | data=real*
A complaint is **any expression of dissatisfaction** (Doc 5 §11.1) — the customer need not say "complaint". Recognition triggers: "I'm not happy", "this is unacceptable", "you've messed up", "I've had to call three times", "I want compensation", "this isn't good enough". On recognition: acknowledge, apologise for the experience (not liability), log `CMP-` **in the same contact**, and attempt resolution. **Never** deflect ("that's just how the process works"), never ask the customer to "put it in writing" as a condition of logging, and never close a `CN-` with an unlogged expression of dissatisfaction — under-recording complaints is a reportable control failure and a common regulatory finding.

### 2.6 Wrap-up, disposition codes and after-call work
*meta: doc=07-RUNBOOK | sec=2.6 | aud=back_office | type=table | data=fictional*
Every contact closes with a disposition code on `CN-`:
`RES-FCR` resolved at first contact · `RES-INFO` information only · `CASE-RAISED` handed to back office (`CW-`) · `VER-FAIL` verification failed · `AUTH-REFUSED` authority not verified, instruction refused · `VULN-FLAG` support need recorded · `COMP-LOGGED` complaint raised · `FC-REF` financial-crime referral · `BEREAV` bereavement notification · `CALLBACK` callback booked · `MISROUTE` transferred out. After-call work target 90 seconds; notes must state **what was verified, what was disclosed, what was actioned** — the three facts every subsequent reviewer, auditor or ombudsman needs.

### 2.7 Accessibility and communication adjustments at point of contact
*meta: doc=07-RUNBOOK | sec=2.7 | aud=customer | type=procedure | data=real*
Offer and record: interpreter services, Relay UK for deaf/speech-impaired customers, large print, Braille and audio formats, extra time, and a trusted third party on the call. These are **reasonable adjustments** under the **Equality Act 2010** as well as FG21/1 good practice — they are provided on request without justification or evidence, and the preference is stored so the customer never has to ask twice (Doc 5 §6.12).

---

## 3. FRONT OFFICE — VULNERABILITY AND BEREAVEMENT IN PRACTICE

### 3.1 Spotting vulnerability on a live contact
*meta: doc=07-RUNBOOK | sec=3.1 | aud=back_office | type=procedure | data=mixed*
Signals: confusion or repetition; a third party answering for the customer or prompting audibly; distress, crying, or references to bereavement, illness or job loss; difficulty with numbers or documents; unusual urgency about money; disclosure of a diagnosis. None of these is proof — the response is to **offer support and adjust**, not to label or restrict (Doc 5 §12.2). Vulnerability is often **transient**: a customer vulnerable during bereavement may not be six months later; support flags are reviewed, not permanent.

### 3.2 Disclosure-handling protocol (TEXAS-style)
*meta: doc=07-RUNBOOK | sec=3.2 | aud=back_office | type=script | data=real (framework) / fictional (wording)*
When a customer discloses a health or personal circumstance, follow the industry-standard drill-down used across UK financial services (the Money Advice Trust's **TEXAS** protocol): **T**hank them for telling you; **E**xplain how the information will be used; obtain e**X**plicit consent to record it; **A**sk targeted questions about the support they need; **S**ignpost to internal support or external help. Explicit consent matters because health disclosures are **special-category data** (UK GDPR Art 9, Doc 5 §4.3). Scripted: *"Thank you for telling me — that's helpful. I'd like to note it on your record so you don't have to explain again. Are you happy for me to do that? Is there anything that would make dealing with us easier?"* For a distressed customer, the companion **BRUCE** approach (**B**ehaviour, **R**emembering, **U**nderstanding, **C**ommunication, **E**valuation) guides how far to probe capability without interrogating.

### 3.3 When to pause a transaction on vulnerability grounds
*meta: doc=07-RUNBOOK | sec=3.3 | aud=back_office | type=procedure | data=mixed*
Pause and escalate — do not simply refuse — where: a third party is directing a withdrawal that benefits them; the customer cannot explain the purpose of a large payment; the customer appears not to understand an irreversible consequence (PCLS/UFPLS, Doc 3 §6); or there are signs of coercion. Explain the pause in neutral terms (*"I want to make sure we get this exactly right, so I'm asking a colleague to review it today"*), never accuse, and document the reasoning **both ways** — the decision to proceed needs recording as much as the decision to hold (Doc 5 §12.4). Autonomy is respected: an informed customer may make a decision others would consider unwise.

### 3.4 Bereavement handling standard
*meta: doc=07-RUNBOOK | sec=3.4 | aud=customer | type=script | data=mixed*
The first contact after a death sets the tone for the whole claim. Standards: answer in the same session; take the death notification without demanding the caller's authority up front (notification ≠ claim, Doc 5 §9.1); ask for the **minimum** at first contact (name, policy number if known, date of death, caller's relationship and contact details); never ask a grieving caller to repeat details already given; issue requirements in **one** pack, not piecemeal; accept **certified copies** and return originals promptly. Use plain, warm language: *"I'm very sorry. I'll take a few details now and then write to you with everything we need in one letter, so you're not chasing."* Death notified via **Tell Us Once** or the **Death Notification Service** must be treated as equivalent to direct notification.

---

## 4. BACK OFFICE — CASE MANAGEMENT

### 4.1 Case states and lifecycle
*meta: doc=07-RUNBOOK | sec=4.1 | aud=back_office | type=table | data=fictional*
Every `CW-` case moves through defined states: **NEW** (created, unallocated) → **ALLOCATED** → **IN-PROGRESS** → **PENDED** (awaiting something, see §4.2) → **READY-FOR-CHECK** → **CHECKED** (four-eyes passed, §4.3) → **AUTHORISED** (where value bands require, Doc 5 §14) → **COMPLETED**. Terminal alternatives: **REJECTED** (instruction not valid), **WITHDRAWN** (customer cancelled), **REFERRED** (moved to Legal/Financial Crime/Claims). SLA clocks run in IN-PROGRESS and READY-FOR-CHECK; they **stop** in PENDED only where the pend reason is customer-side (§4.2) — a pend for internal reasons does not stop the clock, which prevents SLA gaming.

### 4.2 Pend reason codes
*meta: doc=07-RUNBOOK | sec=4.2 | aud=back_office | type=table | data=fictional*
Customer-side (clock stops): `P-DOC` awaiting documents · `P-ID` awaiting identity evidence · `P-AUTH` awaiting authority evidence (LPA/grant/deed/TRS URN) · `P-SIG` awaiting signature · `P-DEC` awaiting customer decision. Internal (clock runs): `P-UW` with underwriting · `P-LEG` with Legal · `P-FC` with Financial Crime · `P-TAX` with Tax · `P-SYS` system issue · `P-3P` awaiting a third party (ceding scheme, GP report). Every pend requires a **chase cycle**: chase at day 10, day 20, and close-or-escalate at day 30 (fictional standard). Pend reasons are the single most useful diagnostic in ops MI — a spike in `P-AUTH` usually means a front-office requirements script has drifted.

### 4.3 Maker-checker and segregation of duties
*meta: doc=07-RUNBOOK | sec=4.3 | aud=back_office | type=procedure | data=fictional*
**Four-eyes** applies to: any payment out; any change of bank mandate; any beneficiary, trust or trustee change; any claim assessment; any redress calculation; any manual override of a system-calculated figure. The **maker cannot be the checker**, and neither may be a person with a recorded personal connection to the customer (declared conflict, Doc 4 A18). The checker re-performs the control — re-checks the evidence and recalculates the figure — rather than confirming the maker's conclusion; sign-off is recorded with `maker_id` and `checker_id` on the case (Doc 5 §19). **Dual authorisation** above value thresholds is a separate, additional control (Doc 5 §14): four-eyes tests correctness, dual authorisation tests authority.

### 4.4 Work allocation and prioritisation
*meta: doc=07-RUNBOOK | sec=4.4 | aud=ops | type=procedure | data=fictional*
Cases are allocated by skill group and prioritised: **P1** bereavement, terminal illness, vulnerability-flagged, complaint-linked, and anything at SLA breach → same day. **P2** payments out, transfers, anything with a customer-facing deadline → within SLA. **P3** routine servicing. **P4** internal admin and reconciliation. Ageing is monitored per §7.1; the oldest item in each queue is reviewed daily by the team manager. Prioritisation is never by value alone — a £500 bereavement claim outranks a £250,000 routine surrender.

### 4.5 Correspondence, indexing and document control
*meta: doc=07-RUNBOOK | sec=4.5 | aud=back_office | type=procedure | data=mixed*
Inbound post is scanned and indexed to the policy within **1 business day**; unindexed items go to an exceptions queue worked daily. Outbound correspondence uses approved templates only — free-text letters require team-manager approval, because template control is how Consumer Duty **consumer-understanding** standards are actually enforced at scale. All customer-facing templates are readability-tested and reviewed annually. Documents are issued to the **registered** address or portal only (Doc 5 §6.11). Certified copies of grants, deeds and certificates are accepted; originals are returned by tracked post within 5 business days.

---

## 5. BACK OFFICE — MONEY MOVEMENT

### 5.1 Payment authorisation chain
*meta: doc=07-RUNBOOK | sec=5.1 | aud=back_office | type=procedure | data=fictional*
No payment leaves without: verified identity (SV+EV, Doc 5 §3.3), verified authority and right to receive (Doc 5 §5), **sanctions screening of the payee** (Doc 5 §13.3), four-eyes check (§4.3), and value-band authorisation (Doc 5 §14). The releasing individual is recorded on the Payment record (`released_by`). Payments to a **newly registered** bank account are held until the verification hold expires (§5.3).

### 5.2 Payment rails, cut-offs and value dates
*meta: doc=07-RUNBOOK | sec=5.2 | aud=back_office | type=table | data=fictional (operational) / real (rail behaviour)*
**Faster Payments (FPS)** — default for amounts up to £250,000; typically same-day/near-instant; used for most surrenders, withdrawals and claim payments. **BACS** — used for regular/bulk payments such as scheduled income and annuity payments; **three-working-day** cycle (submit day 1, process day 2, credit day 3). **CHAPS** — same-day high value, used above £250,000 or where a same-day guarantee is required; higher cost, requires senior authorisation. **Cut-off 15:00** — releases after cut-off carry the next business day's value date. Customer-facing timescales in Doc 5 §15 are quoted to **release**, not receipt; agents must not promise clearing times outside Aldercrest's control.

### 5.3 Payee verification and Confirmation of Payee
*meta: doc=07-RUNBOOK | sec=5.3 | aud=back_office | type=procedure | data=real (mechanism) / fictional (thresholds)*
Where available, run **Confirmation of Payee** — the UK account-name-checking service — before the first payment to a new account. Outcomes: **match** → proceed with standard controls; **close match** → confirm the correct spelling with the customer through the registered contact, never by accepting the new detail on the same call; **no match** → do **not** pay; treat as a potential APP-fraud indicator (Doc 5 §13.2) and re-verify independently; **unavailable** → apply a manual check and extend the verification hold. Aldercrest's hold on first payment to a new account is **2 business days**, waived only by a team manager with a documented reason.

### 5.4 Failed, returned and recalled payments
*meta: doc=07-RUNBOOK | sec=5.4 | aud=back_office | type=procedure | data=fictional*
A returned payment (closed/invalid account) reopens the case at **IN-PROGRESS**, notifies the customer through the registered channel, and requires **re-verification** of any replacement account — a returned payment is a known fraud entry point, because it creates a legitimate reason to supply new bank details. Payment recall (money sent in error) is attempted immediately through the paying bank; the customer is told what happened and by when it will be fixed, and an error record is opened (§7.3). Mis-payment to a third party is assessed as a **potential personal data breach** as well as a financial error (Doc 5 §4.9).

### 5.5 Suspense, unallocated cash and reconciliation
*meta: doc=07-RUNBOOK | sec=5.5 | aud=back_office | type=procedure | data=fictional*
Receipts that cannot be matched to a policy go to **suspense** and are worked daily; items unresolved after **30 days** are escalated to Finance and reported in the monthly control pack. Bank, fund and policy ledgers are reconciled daily; breaks are aged and owned individually. Unallocated cash is never used to offset another customer's shortfall. Reconciliation breaks over £10,000 or older than 5 business days are reported to the ops governance forum (§7.5).

### 5.6 Gone-away customers and tracing
*meta: doc=07-RUNBOOK | sec=5.6 | aud=back_office | type=procedure | data=mixed*
Returned mail marks the policy **gone-away**: suppress further mailing to the failed address, flag the record, and attempt tracing (electronic tracing bureau, then a tracing agent for higher-value cases). Never disclose to anyone contacting on the customer's behalf without full authority checks (Doc 5 §5) — an unsolicited "I have a new address for your customer" contact is a recognised fraud vector and must be verified through the customer, not the caller. Reunification effort is a **Consumer Duty** expectation, not a courtesy: customers cannot get good outcomes from a product they have lost touch with.

### 5.7 Unclaimed and dormant assets
*meta: doc=07-RUNBOOK | sec=5.7 | aud=back_office | type=procedure | data=real (scheme) / fictional (thresholds)*
Where a benefit is due but the customer or beneficiary cannot be found, the amount is held, the record retained, and tracing repeated at **annual** intervals; the liability is never written off. The UK **Dormant Assets Scheme**, expanded by the **Dormant Assets Act 2022** to include insurance and pension assets, allows eligible dormant assets to be transferred to the scheme for social good **while the customer's right to reclaim the full amount is preserved indefinitely**. Participation is voluntary; where Aldercrest participates, reclaim requests are handled as a **priority** case (P1) and paid in full. Nothing in the scheme reduces what the customer is owed.

---

## 6. OPS — INCIDENTS, RESILIENCE AND CONTINUITY

### 6.1 Incident severity model
*meta: doc=07-RUNBOOK | sec=6.1 | aud=ops | type=table | data=fictional*
**SEV1** — an important business service is unavailable or customer harm is occurring at scale (claims cannot be paid; telephony down; suspected data breach affecting many customers). Immediate major-incident call; COO and DPO informed; 30-minute update cadence. **SEV2** — significant degradation with a workaround (one product's servicing unavailable; a batch failed). Duty manager owns; 2-hour cadence. **SEV3** — limited impact, contained (a template error, a single failed interface). Standard queue. **SEV4** — no customer impact. Any incident with a potential personal-data element triggers the **72-hour ICO assessment clock** at the point of reasonable certainty (Doc 5 §4.9) — the incident and the breach assessment run in parallel, never sequentially.

### 6.2 Major incident roles and communications
*meta: doc=07-RUNBOOK | sec=6.2 | aud=ops | type=procedure | data=fictional*
Roles: **Incident Manager** (runs the call, owns the timeline), **Technical Lead**, **Customer Impact Lead** (assesses harm, drafts customer messaging), **Compliance/DPO Lead** (regulatory clocks and notifications), **Comms Lead**. Customer messaging must be honest about impact and expected resolution; agents receive a holding script within 30 minutes so the front line is never left improvising. Post-incident: a written review within **10 business days** covering timeline, root cause, customer impact, redress required (§7.3), and actions with owners and dates.

### 6.3 Operational resilience — important business services
*meta: doc=07-RUNBOOK | sec=6.3 | aud=ops | type=legal | data=real (framework) / fictional (tolerances)*
Under the FCA/PRA operational-resilience regime (**PS21/3**), Aldercrest identifies **important business services**, sets **impact tolerances** (the maximum tolerable disruption), and tests its ability to stay within them. Identified IBSs: **paying claims**, **paying retirement benefits**, **customer contact and servicing**, **payment execution**. Illustrative impact tolerances: claims payment **2 business days**; contact channels **4 hours**; payment execution **1 business day**. Where a tolerance would be breached, the incident is automatically SEV1 and reportable to the regulator. The AI assistant is a **component** of the customer-contact service, not a service itself — its failure must degrade gracefully to human handling (§8.7), never stop the service.

### 6.4 Business continuity and third-party failure
*meta: doc=07-RUNBOOK | sec=6.4 | aud=ops | type=procedure | data=mixed*
Continuity plans cover site loss, telephony loss, core-system loss and **key third-party failure** (fund administrator, print/mail vendor, tracing bureau, AI/cloud provider). Under **SYSC 8** and PRA SS2/21, outsourcing does not transfer accountability — Aldercrest retains full responsibility for outsourced outcomes and must hold exit plans and audit rights (Doc 4 A15). Manual workarounds are documented and rehearsed annually: claims can be assessed and authorised on paper with dual sign-off if the case system is unavailable, because a system outage is not a defence for an unpaid bereavement claim.

---

## 7. OPS — QUALITY, ERRORS AND GOVERNANCE

### 7.1 QA framework, sampling and calibration
*meta: doc=07-RUNBOOK | sec=7.1 | aud=ops | type=procedure | data=fictional*
Risk-based sampling per agent per month: **8 contacts** standard; **15** for agents in their first 90 days; **100% review** of any contact involving a declined claim, a fraud referral, or a vulnerability pause. Scoring covers: identity/authority gates passed; disclosure limited to scope; advice boundary respected (§2.3); complaint recognition (§2.5); vulnerability handling (§3.2); accurate outcome; record quality (**SYSC 9**). A single **critical fail** — disclosing to an unverified caller, giving advice, missing a complaint, ignoring a vulnerability disclosure — fails the whole assessment regardless of other scores. Monthly **calibration** sessions score the same contacts across assessors and managers to keep marking consistent; calibration variance above 10% triggers re-training of assessors, not agents.

### 7.2 Complaint root-cause taxonomy
*meta: doc=07-RUNBOOK | sec=7.2 | aud=ops | type=table | data=fictional*
`RC-DELAY` service delay/SLA breach · `RC-ERR` processing error · `RC-COMM` unclear or wrong communication · `RC-CHG` charges dispute · `RC-PERF` investment performance · `RC-CLAIM` claim decision/handling · `RC-TAX` unexpected tax consequence · `RC-SALE` sale/suitability · `RC-ACCESS` accessibility/vulnerability handling · `RC-FRAUD` fraud-related · `RC-DATA` data protection · `RC-AI` AI assistant answer quality. Each is tagged to product, channel and originating team. Themes are reported monthly and feed **product governance (PROD 4)** and the annual **Consumer Duty** outcomes assessment. `RC-TAX` on the Bond and `RC-COMM` on Lifelong Protection premium reviews are the two known systemic hotspots and are reported by exception every month.

### 7.3 Error handling, redress calculation and remediation
*meta: doc=07-RUNBOOK | sec=7.3 | aud=back_office | type=worked_example | data=mixed*
Any error is logged (`REM-`) whether or not the customer noticed — self-identified errors are a control strength, not a failure. Redress principle: restore the customer to the position they would have been in (Doc 5 §11.4). **Worked example:** a £20,000 surrender is paid 12 days late through an internal pend error. Redress = interest for the delay at **8% simple per year**: £20,000 × 8% × (12 ÷ 365) = **£52.60**, plus a distress-and-inconvenience payment where the delay caused real disruption, plus a written apology explaining the cause and the fix. Income tax is deducted from the interest element where required and a deduction certificate issued. Where the same error may have affected others, ops opens a **remediation review**: define the population, quantify the impact, contact all affected customers (not only complainants), and report the review through governance (§7.5). Proactive remediation of a whole affected population is the clearest evidence of Consumer Duty compliance.

### 7.4 Manual overrides and exception logging
*meta: doc=07-RUNBOOK | sec=7.4 | aud=back_office | type=procedure | data=fictional*
Any manual override of a system-calculated value — a fund price, a tax figure, an SLA date, an allowance calculation — requires a documented reason, four-eyes approval (§4.3), and an entry on the exception log reviewed weekly by ops. Overrides are a leading indicator: a rising override rate on one calculation usually means the underlying rule or system is wrong, and the fix belongs in the system, not in a workaround.

### 7.5 Governance forums and MI cadence
*meta: doc=07-RUNBOOK | sec=7.5 | aud=ops | type=table | data=fictional*
**Daily** — queue and SLA stand-up; oldest-item review; incident status. **Weekly** — QA results and calibration; exception and override log; pend-reason analysis; financial-crime referrals; AI assistant metrics (Doc 6 §4.2). **Monthly** — Operations Governance Forum: KPI pack, complaints root cause, remediation reviews, breach register, reconciliation breaks, vendor performance. **Quarterly** — Consumer Duty outcomes review; product fair-value input (PROD 4); operational-resilience testing results. **Annual** — board-approved Consumer Duty assessment; BCP rehearsal; template readability review; retention-schedule review. Every forum has a named owner, a standing agenda and recorded actions — MI that no one is accountable for acting on is decoration.

---

## 8. AI ASSISTANT — OPERATING GOVERNANCE

### 8.1 Deployment model: agent-assist and customer self-service
*meta: doc=07-RUNBOOK | sec=8.1 | aud=all | type=procedure | data=fictional*
The RAG assistant runs in two modes. **Agent-assist** (front and back office): retrieves and drafts, the human decides and acts; the human is accountable for the outcome. **Customer self-service** (portal): answers **information-only** questions and can initiate low-risk servicing (§8.3), with everything else handed to a human. The assistant never operates in a mode where it both decides and executes a financial transaction without a human control point.

### 8.2 Human-in-the-loop requirements
*meta: doc=07-RUNBOOK | sec=8.2 | aud=all | type=procedure | data=fictional*
A human **must** be in the loop before: any payment out; any change of bank mandate; any beneficiary, trust or trustee change; any claim decision; any irreversible pension action (PCLS/UFPLS); any refusal that would leave a customer without a route; any complaint response; any disclosure to a third party or authority. The assistant may prepare, evidence and recommend all of these — it may not complete them. This maps to the same four-eyes and authority controls that govern human processing (§4.3, Doc 5 §14): the AI is treated as a **maker**, never a checker or authoriser.

### 8.3 Permitted autonomous actions
*meta: doc=07-RUNBOOK | sec=8.3 | aud=all | type=table | data=fictional*
Permitted without human review, subject to identity gates: answering product and process questions from the knowledge base; explaining tax mechanics **generically** with a signpost; quoting SLAs and requirements lists; confirming what documents are needed; logging a callback; recording a marketing preference change; issuing a duplicate document to the **registered** contact; raising a `CW-` case, a `CMP-` complaint record, or a `VULN-FLAG` support need. Everything else is prepare-and-hand-off.

### 8.4 Prohibited actions
*meta: doc=07-RUNBOOK | sec=8.4 | aud=all | type=table | data=fictional*
The assistant must never: give advice or a recommendation (§2.3); state or imply a claim will be paid before assessment; disclose anything before the identity gate is passed (Doc 5 §3); accept a third party's authority without verified evidence (Doc 5 §5); process an instruction from an attorney that is outside LPA scope (e.g. changing a beneficiary, acting as trustee — Doc 5 §5.8); confirm or deny a policy exists to an unverified caller; explain a financial-crime hold or reveal anything touching a SAR (**tipping off**, Doc 5 §13.4); quote a not-yet-in-force rule as current law without its effective date; or compute a customer-specific tax liability as though it were advice.

### 8.5 Abstention, confidence and fallback
*meta: doc=07-RUNBOOK | sec=8.5 | aud=all | type=procedure | data=fictional*
The assistant abstains and hands off when: retrieval returns no chunk above the relevance floor; retrieved chunks **conflict** (e.g. a product rule against a procedure); the question depends on a customer-specific fact not present in the record; the answer would require an inference the knowledge base does not support; or the topic is on the prohibited list (§8.4). Abstention language is plain and non-alarming: *"I don't want to give you a partial answer on this — let me get a colleague who can look at your specific policy."* A wrong confident answer is a materially worse outcome than a handoff; **abstention is a success state, not a failure**, and is measured as such (Doc 6 §4.2).

### 8.6 Why containment is not a target
*meta: doc=07-RUNBOOK | sec=8.6 | aud=ops | type=ops | data=fictional*
Deflection or containment rates are **tracked but never targeted**. A containment target creates direct pressure to answer questions that should be escalated — precisely the failure mode that produces disclosure breaches, missed vulnerability, unrecorded complaints and bad claim outcomes. Ops measures **correct routing** (was the handoff decision right?) and **answer quality**, and treats a rise in containment without a matching rise in quality as a red flag, not a win. This is the Consumer Duty framing: good outcomes, not cheap ones.

### 8.7 Graceful degradation
*meta: doc=07-RUNBOOK | sec=8.7 | aud=ops | type=procedure | data=mixed*
If the assistant, the vector store or the model is unavailable, the customer-contact service continues on human handling with published fallback scripts — the AI is a component of an important business service, not the service (§6.3). Degradation is announced internally within 15 minutes; agents are told explicitly that assist is unavailable so they do not act on stale or partial suggestions. Loss of the assistant is at most **SEV2** unless contact handling itself is impaired.

### 8.8 Transparency to customers
*meta: doc=07-RUNBOOK | sec=8.8 | aud=customer | type=procedure | data=mixed*
Customers using self-service are told they are interacting with an AI assistant and how to reach a person at any point — a single, always-visible route, never buried. This supports the Consumer Duty **consumer-support** outcome (a customer must not face unreasonable barriers) and UK GDPR transparency (Doc 4 A17). Where the assistant has materially informed a decision recorded on a customer's file, that is noted on the case so any later reviewer or ombudsman can reconstruct what the customer was told.

### 8.9 Accountability and oversight
*meta: doc=07-RUNBOOK | sec=8.9 | aud=ops | type=legal | data=mixed*
Accountability for the assistant's outputs sits with the accountable Senior Manager for operations under **SM&CR** — it cannot be delegated to a vendor (Doc 4 A6, A15). A **DPIA** is required and maintained for the assistant as innovative technology processing personal data at scale, including special-category data (Doc 4 A17). Any AI disclosure error is logged as a **potential personal data breach** (`BR-`, Doc 5 §4.9). Knowledge-base changes follow the controlled change process in **Doc 6 §2**, including the eval regression gate before promotion — an uncontrolled edit to the knowledge base is a change to a regulated customer-facing process.

---

## 9. RUNBOOK GLOSSARY
*meta: doc=07-RUNBOOK | sec=9 | aud=all | type=glossary | data=mixed*
**FCR** — first-contact resolution. **Disposition code** — the outcome code closing every contact (§2.6). **Warm transfer** — briefed handoff with the customer held. **Pend** — case paused awaiting something (§4.2). **Maker-checker (four-eyes)** — a second person re-performs the control (§4.3). **Dual authorisation** — a second approver above a value threshold. **P1–P4** — case priority bands (§4.4). **FPS/BACS/CHAPS** — UK payment rails (§5.2). **Confirmation of Payee (CoP)** — account-name checking before payment. **Gone-away** — customer unreachable at the registered address (§5.6). **Dormant Assets Scheme** — statutory scheme for unclaimed assets, reclaim right preserved (§5.7). **SEV1–SEV4** — incident severity (§6.1). **IBS** — important business service under PS21/3. **Impact tolerance** — maximum tolerable disruption. **TEXAS/BRUCE** — vulnerability disclosure and capability protocols (§3.2). **Critical fail** — a QA failure that fails the whole assessment (§7.1). **Remediation review** — proactive fix for a whole affected population (§7.3). **Agent-assist** — AI drafts, human decides (§8.1). **Abstention** — the assistant declining to answer and handing off (§8.5). **Containment** — share resolved without a human; tracked, never targeted (§8.6).

---

## 10. SOURCES (atomic reference chunk)
*meta: doc=07-RUNBOOK | sec=10 | aud=all | type=sources | data=real*
- FCA DISP (complaints, incl. recognition and time limits) — https://handbook.fca.org.uk/handbook/DISP/
- FCA FG21/1 vulnerable customers — https://www.fca.org.uk/publications/finalised-guidance/guidance-firms-fair-treatment-vulnerable-customers
- FCA Consumer Duty (PRIN 2A) — https://handbook.fca.org.uk/handbook/prin2a
- FCA PS21/3 operational resilience — https://www.fca.org.uk/publications/policy-statements/ps21-3-building-operational-resilience
- FCA SYSC 8 (outsourcing) and SYSC 9 (records) — https://handbook.fca.org.uk/handbook/SYSC/
- PRA SS2/21 outsourcing and third-party risk — https://www.bankofengland.co.uk/prudential-regulation/publication/2021/march/outsourcing-and-third-party-risk-management-ss
- FOS — compensation for distress and inconvenience — https://www.financial-ombudsman.org.uk/businesses/putting-things-right/compensation-distress-inconvenience
- FOS — putting things right (redress approach) — https://www.financial-ombudsman.org.uk/businesses/putting-things-right
- Money Advice Trust — vulnerability protocols (TEXAS/BRUCE) — https://www.moneyadvicetrust.org/training-and-consultancy
- Equality Act 2010 (reasonable adjustments) — https://www.legislation.gov.uk/ukpga/2010/15/contents
- Relay UK (accessibility) — https://www.relayuk.bt.com/
- Confirmation of Payee (Pay.UK) — https://www.wearepay.uk/what-we-do/overlay-services/confirmation-of-payee/
- Dormant Assets Act 2022 — https://www.legislation.gov.uk/ukpga/2022/5/contents
- Dormant Assets Scheme (gov.uk) — https://www.gov.uk/government/collections/dormant-assets-scheme
- Tell Us Once — https://www.gov.uk/after-a-death/organisations-you-need-to-contact-and-tell-us-once
- Death Notification Service — https://www.deathnotificationservice.co.uk/
- ICO — call recording and transparency — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/
- ICO — DPIAs — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/data-protection-impact-assessments-dpias/
- PECR (electronic marketing) — https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/

---
*End of Document 7 v1. Procedures: Document 5. Products: Documents 1–3. Regulation: Document 4. RAG evals and change management: Document 6.*
