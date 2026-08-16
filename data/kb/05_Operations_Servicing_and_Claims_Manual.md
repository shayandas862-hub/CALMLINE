# Aldercrest Life Assurance plc (trading as "Aldercrest Life")
*meta: doc=05-OPS | sec=frontmatter | aud=all | type=caveats | data=mixed*
# Document 5 — Operations, Policy Servicing & Claims Procedures Manual (MASTER)
*meta: doc=05-OPS | sec=frontmatter-title | aud=all | type=caveats | data=mixed*
**Version 2026.3 | Effective 13 July 2026 | Owner: Chief Operating Officer | Classification: Internal — RAG Knowledge Base**

> **Note:** This is the master cross-product version of the operations layer. The **same operational content is also embedded, tailored per product, inside each product master document (Documents 1–3) as "Part II"**, so each product document is self-contained for RAG retrieval. This master document is retained as the single source of truth for the cross-product procedures. Company-specific procedures, authority levels, SLAs, reference formats and thresholds are fictional but internally consistent; all data-protection, security, financial-crime, third-party-authority and consumer-protection rules are grounded in real UK law and regulation with cited URLs in Section 18.

---

## 1. PURPOSE AND SCOPE
*meta: doc=05-OPS | sec=1 | aud=all | type=overview | data=mixed*

### 1.1 What this manual is
*meta: doc=05-OPS | sec=1.1 | aud=all | type=overview | data=fictional*
This is the cross-product operational "engine" for Aldercrest Life. It sits alongside the three product master documents — **Lifelong Protection** (Whole of Life Assurance), **Horizon Bond** (Onshore Investment Bond) and **Retirement Account** (Personal Pension) — and the **FCA Regulatory Mandate** document. Where a product document describes *what a product is*, this manual describes *how we service it, verify who we are dealing with, move money, pay claims, and oversee the whole flow*.

### 1.2 Scope
*meta: doc=05-OPS | sec=1.2 | aud=all | type=overview | data=fictional*
Applies across all three products and to every inbound/outbound contact, servicing transaction, claim, and oversight activity. Governs front office (call handlers), back office (case processors) and ops (oversight/QA/MI).

### 1.3 How it feeds the RAG/AI system
*meta: doc=05-OPS | sec=1.3 | aud=all | type=routing | data=fictional*
The agentic RAG-based customer service AI uses this manual as the authoritative procedural layer. Each numbered section is a self-contained chunk. The AI must: identify the **contact type** and **caller type** (Section 2), then the **transaction type** (Sections 6–9); enforce **identity/authority gates** (Sections 3 and 5) *before* disclosing or changing anything; route to the correct **audience layer** (Section 17); apply the **authority matrix** (Section 14) and **SLA table** (Section 15); escalate where this manual says "refer" or "escalate".

### 1.4 Fictional reference-number formats (internally consistent)
*meta: doc=05-OPS | sec=1.4 | aud=all | type=data_dictionary | data=fictional*
Policy numbers: `LP-` (Lifelong Protection), `HB-` (Horizon Bond), `RA-` (Retirement Account), + 8 digits, e.g. `HB-40582213`. Interaction log `CN-` + 10; case/work item `CW-` + 9; complaint `CMP-` + 8; claim `CLM-` + 8; financial-crime referral `FC-` + 7.

---

## 2. INBOUND CONTACT HANDLING (master flow)
*meta: doc=05-OPS | sec=2 | aud=all | type=overview | data=mixed*

### 2.1 Channels
*meta: doc=05-OPS | sec=2.1 | aud=back_office | type=procedure | data=mixed*
Telephone (front office), secure portal message (authenticated), email (monitored — treated as unsecured; no outbound personal data unless encrypted, see 4.6), post (scanned into the case system within 1 business day), and the adviser portal (authorised advisers).

### 2.2 The master inbound flow (all channels)
*meta: doc=05-OPS | sec=2.2 | aud=back_office | type=procedure | data=mixed*
1. **Capture the contact** — open a `CN-` log: channel, date/time, stated identity, stated relationship, nature of request.
2. **Classify the caller type** (2.3).
3. **Verify identity/authority** to the level required (Sections 3 and 5). *No personal data disclosed and no change actioned until the correct gate is passed.*
4. **Triage** to a transaction type (6–9), a claim (9), a complaint (11), or a regulator/legal request (10).
5. **Screen for risk** — vulnerability (12), fraud/financial crime (13), sanctions (8 and 13).
6. **Act or route** — resolve within front-office authority, or raise a `CW-` case with evidence attached.
7. **Log the outcome** and any follow-up SLA.

### 2.3 Who can contact us — caller types and what to capture
*meta: doc=05-OPS | sec=2.3 | aud=back_office | type=procedure | data=mixed*
**(a) The policyholder / life assured / plan holder (data subject).** Capture full name, policy number, DOB, address, request. Verify per Section 3.
**(b) Authorised third parties** (detail in Section 5): financial adviser (LOA) — firm, FRN, adviser name, scope; attorney under an **LPA** (property & financial affairs) — donor/attorney details, OPG reference; attorney under an **EPA**; **Court of Protection deputy** — deputyship order reference; **executor/personal representative** — deceased/representative details, grant status; **third-party mandate** holder; **a person calling for a vulnerable customer** — customer consent (where capacity) and relationship.
**(c) Regulators / government / legal bodies** — FCA, HMRC, courts, police, OFSI, ICO. Capture requesting body, named officer, legal basis cited, information sought. Route to control functions per Section 10; do not disclose from the front line.

### 2.4 Data-protection principle at first contact
*meta: doc=05-OPS | sec=2.4 | aud=back_office | type=legal | data=real*
Verify identity **before** disclosing any personal data (UK GDPR Art 5; ICO guidance). Before verification, confirm only generic non-personal information.

---

## 3. IDENTITY VERIFICATION & AUTHENTICATION (KYC at servicing)
*meta: doc=05-OPS | sec=3 | aud=all | type=overview | data=mixed*

### 3.1 Governing principle (real law)
*meta: doc=05-OPS | sec=3.1 | aud=back_office | type=legal | data=real*
UK GDPR Art 5(1)(f) and the DPA 2018 require appropriate security. ICO *Right of access* guidance: be satisfied of the requester's identity before disclosing personal data. Also a fraud control (Section 13).

### 3.2 Standard verification (SV) — for any disclosure or low-risk change
*meta: doc=05-OPS | sec=3.2 | aud=back_office | type=procedure | data=fictional*
Three of four: policy number; full name + DOB; registered correspondence address (or last-4 of the premium-collection account); memorable-data item set at onboarding. Portal and adviser-portal contacts are SV-passed by authentication unless a step-up trigger applies.

### 3.3 Enhanced verification (EV) — for high-risk changes
*meta: doc=05-OPS | sec=3.3 | aud=back_office | type=procedure | data=fictional*
SV **plus** (a) a one-time passcode to the **registered** mobile/email (never a newly supplied contact) **plus** (b) one further check (call-back to the registered number, documentary evidence, or knowledge-based questions on recent activity). Required for: bank/Direct Debit changes; withdrawals/surrenders/pension access above the front-office band; an address change followed within 30 days by a bank change or withdrawal; adding/removing a third-party authority or beneficiary on a high-value policy.

### 3.4 Step-up triggers (force EV)
*meta: doc=05-OPS | sec=3.4 | aud=back_office | type=procedure | data=fictional*
Change-a-detail-then-transact; failed SV element with "corrections"; urgency to pay a new payee; detail mismatch; contact shortly after a password reset or address change.

### 3.5 When verification FAILS
*meta: doc=05-OPS | sec=3.5 | aud=back_office | type=procedure | data=fictional*
Disclose nothing (do not confirm the policy exists); offer a secure alternative (write to the registered address, or use the portal); log the failed attempt; refer repeated/suspicious failures to Financial Crime as possible impersonation (Section 13), without tipping off if a SAR is contemplated (13.4).

---

## 4. DATA PROTECTION & SECURITY IN EVERY INTERACTION
*meta: doc=05-OPS | sec=4 | aud=all | type=overview | data=mixed*

### 4.1 Legal framework (real)
*meta: doc=05-OPS | sec=4.1 | aud=back_office | type=legal | data=real*
Aldercrest Life is a **data controller** under **UK GDPR** and the **DPA 2018**, regulated by the **ICO**. The **Data (Use and Access) Act 2025** (Royal Assent 19 June 2025) is being commenced through 2025–26; treat current ICO guidance as operative.

### 4.2 Lawful basis (UK GDPR Article 6)
*meta: doc=05-OPS | sec=4.2 | aud=back_office | type=legal | data=real*
Contract (Art 6(1)(b)); legal obligation (Art 6(1)(c) — AML/CDD, tax reporting, complaints, retention); legitimate interests (Art 6(1)(f) — fraud prevention, admin, subject to an LIA); consent (Art 6(1)(a) — marketing only, revocable at any time).

### 4.3 Special-category (health) data — Article 9
*meta: doc=05-OPS | sec=4.3 | aud=back_office | type=legal | data=real*
Health data (underwriting, terminal-illness/death claims, ill-health pension access) needs **both** an Art 6 basis **and** an Art 9 condition — principally **explicit consent (Art 9(2)(a))** at underwriting and **establishment/exercise/defence of legal claims (Art 9(2)(f))** at claim stage. Stricter minimisation, enhanced security, appropriate policy document where a DPA 2018 Schedule 1 condition applies. Visible only to staff who need it.

### 4.4 Data minimisation
*meta: doc=05-OPS | sec=4.4 | aud=back_office | type=legal | data=real*
Collect/disclose only what is necessary (Art 5(1)(c)). To a third party, disclose only what falls within their verified authority (Section 5).

### 4.5 Sharing with third parties
*meta: doc=05-OPS | sec=4.5 | aud=back_office | type=procedure | data=real*
**Can share** with a verified party within a verified scope, the minimum needed. **Cannot share** anything with an unverified caller; anything beyond an authority's scope (e.g. a "servicing only" LOA does not permit a surrender); health/claims detail with an address-change helper.

### 4.6 Secure handling
*meta: doc=05-OPS | sec=4.6 | aud=back_office | type=procedure | data=real*
Outbound personal data only if encrypted/secure-messaged (misdirected email/post is a leading breach cause — double-check recipients); post to the **registered** address; portal is the default secure channel; apply Art 32 access controls, encryption, least-privilege.

### 4.7 Subject Access Requests (SARs/DSARs)
*meta: doc=05-OPS | sec=4.7 | aud=back_office | type=procedure | data=real*
Verbal or written, any channel — **log immediately** as a `CW-` DSAR and route to the Data Protection Office. **Deadline: within one calendar month** of receipt (extendable by up to two further months if complex/numerous, with reasons told within one month). "Stop the clock" only to clarify a bulk request or obtain ID. **Redact** third-party data; apply exemptions (Section 10.4). Usually **no fee**. Special-category data delivered encrypted.

### 4.8 Rectification and erasure
*meta: doc=05-OPS | sec=4.8 | aud=back_office | type=procedure | data=real*
Rectification (Art 16): correct inaccurate data promptly with evidence. Erasure (Art 17): frequently overridden by legal/regulatory retention duties (4.9) — explain why while retention applies.

### 4.9 Personal data breaches — the 72-hour duty
*meta: doc=05-OPS | sec=4.9 | aud=back_office | type=procedure | data=real*
Log all suspected breaches (misdirected post/email, lost device, unauthorised access, wrong-caller disclosure) on the breach register. The DPO assesses risk; if the threshold is met, notify the **ICO without undue delay and, where feasible, within 72 hours** (UK GDPR Art 33) — the clock starts on reasonable certainty a breach occurred and does not pause outside business hours. If **high risk**, tell individuals without undue delay (Art 34). Phased reporting permitted.

### 4.10 Record retention (fictional but lawful-basis-anchored)
*meta: doc=05-OPS | sec=4.10 | aud=back_office | type=table | data=fictional*
Policy/servicing records **6 years** after the policy ends; **claims** 6 years after settlement; **AML/CDD** 5 years after the relationship ends (MLR 2017); **complaints** ≥3 years (DISP); **DSAR logs** 3 years; **vulnerability support-need records** only as long as needed. "Keep forever" is not permitted.

---

## 5. THIRD-PARTY AUTHORITY — DETAILED RULES
*meta: doc=05-OPS | sec=5 | aud=all | type=overview | data=mixed*

### 5.0 Overarching authority rule
*meta: doc=05-OPS | sec=5.0 | aud=back_office | type=procedure | data=fictional*
Authority must be **verified** and the request must fall **within the verified scope**. Otherwise refuse that specific instruction, explain what would make it acceptable, offer the customer-direct route, and log the refusal on `CN-`. No partial disclosure "to be helpful", and never accept an instruction or a change of contact detail from an unverified third party — an unsolicited "I have new details for your customer" contact is a recognised fraud vector (Doc 7 §5.6).

### 5.1 Financial adviser authority (Letter of Authority)
*meta: doc=05-OPS | sec=5.1 | aud=back_office | type=procedure | data=mixed*
Client-signed LOA naming Aldercrest Life and the firm; firm's FCA FRN checked on the FCA Register; adviser linked to the firm. Scope usually "servicing and information". An LOA does **not** authorise receiving claim/surrender proceeds or changing the customer's bank details.

### 5.2 Lasting Power of Attorney (Property & Financial Affairs)
*meta: doc=05-OPS | sec=5.2 | aud=back_office | type=procedure | data=real*
Mental Capacity Act 2005; valid only once **registered with the OPG**. Verify via the **"Use a lasting power of attorney"** online service (attorney access code beginning "V" + LPA reference), the **stamped paper LPA** (OPG validation perforated through every page), or an **OPG100** register search. Check it is registered and **not revoked**, the attorney acts **within scope**, and the appointment type (**jointly** vs **jointly and severally**). Health-and-welfare LPAs give no financial authority.

### 5.3 Enduring Power of Attorney (EPA)
*meta: doc=05-OPS | sec=5.3 | aud=back_office | type=procedure | data=real*
Older instrument (pre-1 Oct 2007), property/financial only; OPG-registered once capacity is lost; no online register — verify the stamped paper instrument or via the OPG.

### 5.4 Court of Protection deputyship
*meta: doc=05-OPS | sec=5.4 | aud=back_office | type=procedure | data=real*
Where no LPA/EPA and the person lacks capacity: verify the **deputyship court order** covers property & financial affairs and is current (deputies supervised by the OPG).

### 5.5 Executors / personal representatives (deceased customer)
*meta: doc=05-OPS | sec=5.5 | aud=back_office | type=procedure | data=real*
Authority evidenced by **Grant of Probate** (executors) or **Letters of Administration** (administrators). Where the policy is **in trust** or has a valid **nomination**, proceeds pass outside the estate — verify the trustees/nominated beneficiaries instead. See Section 9.

### 5.6 Third-party mandates and one-off authorities
*meta: doc=05-OPS | sec=5.6 | aud=back_office | type=procedure | data=mixed*
A signed **mandate** lets a named person operate the policy within set limits; a one-off authority is logged on the `CN-` record and expires immediately after.

### 5.7 If authority cannot be verified
*meta: doc=05-OPS | sec=5.7 | aud=back_office | type=procedure | data=mixed*
Refuse the specific instruction, explain, set out the route to compliance, and log. No partial disclosure.

### 5.8 Trustee lifecycle and edge cases (cross-product)
*meta: doc=05-OPS | sec=5.8 | aud=back_office | type=procedure | data=real (law) / fictional (process)*
Trusteeship is **personal**: an LPA attorney **cannot act as trustee** for an incapacitated trustee — replacement is **by deed under s.36 Trustee Act 1925** (CoP considerations where the trustee is also settlor/beneficiary). Death of a trustee: survivors continue; last trustee's PRs may appoint. Instructions require **all trustees** unless the deed says otherwise. Offshore trustee → EDD + tax flags → refer. **TRS proof (URN)** collected for registrable trusts — bond trusts always registrable; pure-protection policy trusts excluded while the policy is held (exclusion ends if proceeds held >2 years after death); pilot/bypass trusts become registrable on funding. Product detail: Doc 1 §12.3/§II.6.13, Doc 2 §12.6/§II.6.10, Doc 3 §14.

---

## 6. POLICY SERVICING PROCEDURES
*meta: doc=05-OPS | sec=6 | aud=all | type=overview | data=mixed*

Each mini-procedure: **what · who · what we need · steps · authority · SLA · exceptions.** SV minimum unless stated. One procedure per `###` chunk. Product-tailored versions live in each product doc §II.6.

### 6.1 Change of address
*meta: doc=05-OPS | sec=6.1 | aud=back_office | type=procedure | data=fictional*
SV; validate; confirm to **both** old and new address; 30-day watch. Front office; same day. *Exception:* address + bank/withdrawal within 30 days → EV + Financial Crime watch.

### 6.2 Change of name
*meta: doc=05-OPS | sec=6.2 | aud=back_office | type=procedure | data=fictional*
SV + evidence (marriage/civil-partnership certificate, deed poll, decree absolute). Back office; 3 business days.

### 6.3 Change of bank / Direct Debit (HIGH RISK)
*meta: doc=05-OPS | sec=6.3 | aud=back_office | type=procedure | data=fictional*
Policyholder only (not an LOA); attorney/deputy within scope. SV + EV; verify new account; verification hold before first collection/payment; confirm to registered contact. Back office; 2 business days. *Exception:* urgency/third-party account/mismatch → possible APP fraud (Section 13).

### 6.4 Correspondence preferences / marketing consent
*meta: doc=05-OPS | sec=6.4 | aud=back_office | type=procedure | data=mixed*
SV; marketing on **consent** (UK GDPR + PECR — Doc 4 A16; as easy to withdraw as to give); opt-out immediate. Front office; same day (suppression ≤24h).

### 6.5 Contribution / premium amount or frequency
*meta: doc=05-OPS | sec=6.5 | aud=back_office | type=procedure | data=mixed*
SV; product-rule check — Retirement Account: **annual allowance/MPAA**; Lifelong Protection: cover/guarantee effect; Horizon Bond: premium/top-up rules. Back office; 3 business days / next cycle.

### 6.6 Indexation add/remove
*meta: doc=05-OPS | sec=6.6 | aud=back_office | type=procedure | data=fictional*
SV; explain effect (Consumer Duty understanding). Back office; 3 business days.

### 6.7 Beneficiaries / expression of wishes
*meta: doc=05-OPS | sec=6.7 | aud=back_office | type=procedure | data=mixed*
A personal right; generally not an attorney unless expressly permitted → escalate. SV; signed form; subject to any trust. Back office; 5 business days.

### 6.8 Trust set-up / trustee change
*meta: doc=05-OPS | sec=6.8 | aud=back_office | type=procedure | data=fictional*
SV; executed trust deed / deed of appointment-and-retirement; ID for new trustees; Scots-law deed for Scottish settlors. Senior case handler; 10 business days.

### 6.9 Fund switches (Bond & Pension)
*meta: doc=05-OPS | sec=6.9 | aud=back_office | type=procedure | data=fictional*
SV; confirm permitted funds/limits/charges (Bond: permitted-asset/PPB guard, Doc 2 §3.7). Back office; instruction placed ≤2 business days.

### 6.10 Target retirement age (Pension)
*meta: doc=05-OPS | sec=6.10 | aud=back_office | type=procedure | data=mixed*
SV; check minimum pension age (55, rising to 57 from 6 April 2028). Back office; 3 business days.

### 6.11 Duplicate documents
*meta: doc=05-OPS | sec=6.11 | aud=back_office | type=procedure | data=fictional*
SV; issue to registered contact/portal. Front office; 3 business days.

### 6.12 Vulnerable-customer support flags
*meta: doc=05-OPS | sec=6.12 | aud=back_office | type=procedure | data=mixed*
Capture sensitively; special-category care (Section 12). Front office; same day.

### 6.13 TRS reference capture and discrepancy reporting
*meta: doc=05-OPS | sec=6.13 | aud=back_office | type=procedure | data=real (duty) / fictional (process)*
At trust onboarding, trustee change, or claim funding: determine registrability (§5.8); request the **TRS URN / proof of registration**; record it on the AuthorityRecord (§19); if the TRS entry is materially wrong, file a **discrepancy report** to HMRC. Hold new trust business where proof is outstanding beyond 30 days (fictional standard). Back office; 5 business days.

---

## 7. PUTTING MONEY IN
*meta: doc=05-OPS | sec=7 | aud=all | type=overview | data=mixed*

**Who:** policyholder; adviser within scope; third party (extra source-of-funds scrutiny). SV; product eligibility.
**AML/source of funds:** for large/unusual inflows apply CDD and establish source of funds/wealth under **MLR 2017**. Fictional trigger: single ≥ **£25,000**, or aggregate ≥ **£50,000**/12 months, or any third-party/high-risk-jurisdiction payment → source-of-funds evidence and risk assessment. **EDD** for PEPs, high-risk-country links, or higher-risk indicators (MLR 2017 reg 33).
**Product-specific:** Retirement Account — check **annual allowance (£60,000, 2025/26, tapered for high earners)** and **MPAA (£10,000)**; confirm relief-at-source; flag over-contribution. Horizon Bond — record top-up as an increment; new **5% allowance clock**; new segments. Lifelong Protection — increments may require re-underwriting (health data — 4.3).
**Authority & SLA:** standard back office, 3 business days; large/EDD held until CDD complete, 5–10 business days.

---

## 8. TAKING MONEY OUT
*meta: doc=05-OPS | sec=8 | aud=all | type=overview | data=mixed*

### 8.1 Universal controls before any payment out
*meta: doc=05-OPS | sec=8.1 | aud=back_office | type=procedure | data=mixed*
1. Identity: **SV + EV**. 2. Authority and right to receive proceeds (to the **registered** account unless a verified legal authority directs otherwise). 3. **Sanctions screening** against the **UK Sanctions List** — a confirmed match stops the payment and is reported to **OFSI** (not risk-based). 4. **Tax-consequence flag** and signposting. 5. Vulnerability and fraud checks.

### 8.2 Horizon Bond — withdrawals and surrenders
*meta: doc=05-OPS | sec=8.2 | aud=back_office | type=procedure | data=mixed*
Partial withdrawal within the **5% per year** tax-deferred allowance (cumulative) → no immediate tax; exceeding it → **chargeable event gain**; issue a **chargeable event certificate**; note **top-slicing**. Segment surrender is often more efficient than a partial withdrawal across all segments — surface both. Standard SLA 5 business days after checks.

### 8.3 Retirement Account — pension access
*meta: doc=05-OPS | sec=8.3 | aud=back_office | type=procedure | data=mixed*
**PCLS** up to 25%, subject to the **Lump Sum Allowance £268,275** (2025/26). **Flexi-access drawdown** — taxable income triggers the **MPAA (£10,000)**. **UFPLS** — 25% tax-free / 75% taxed; triggers the MPAA even on the first payment. **Annuity** — new contract; risk warnings. Confirm minimum pension age (55, rising to 57 from 6 April 2028); emergency-tax and MPAA warnings; **Pension Wise** signposting; scam checks (Section 13). Note the legislated inclusion of unused pension funds in the estate for IHT **from 6 April 2027**. **PCLS/UFPLS are not cancellable** — tax consequences cannot be reversed (FCA/HMRC statement, 2025). SLA 5–10 business days.

### 8.4 Lifelong Protection
*meta: doc=05-OPS | sec=8.4 | aud=back_office | type=procedure | data=mixed*
Surrender value only where the plan has an investment/cash value; otherwise "taking money out" is a **claim** (Section 9) or a lapse/cancellation query.

---

## 9. CLAIMS PROCEDURES (death, terminal illness)
*meta: doc=05-OPS | sec=9 | aud=all | type=overview | data=mixed*

### 9.1 Notification of death — who can notify
*meta: doc=05-OPS | sec=9.1 | aud=back_office | type=claims | data=mixed*
Anyone (relative, executor, adviser, funeral director, or via the **Death Notification Service / Tell Us Once** concept). Register the death and open a `CLM-`; route to the Bereavement Team; apply vulnerability sensitivity. Notification ≠ claim; pay only a verified claimant.

### 9.2 Documents required
*meta: doc=05-OPS | sec=9.2 | aud=back_office | type=claims | data=mixed*
Certified **death certificate** (always); where payable to the **estate**, **grant of probate**/**letters of administration**; where **in trust**, the **trust deed** and **trustee** identities (proceeds pass outside the estate); where a valid **nomination** (e.g. Retirement Account death benefit), verify the nominated beneficiaries; claimant ID and authority.

### 9.3 Verifying the claimant's authority
*meta: doc=05-OPS | sec=9.3 | aud=back_office | type=claims | data=mixed*
Named beneficiary, trustee, or personal representative with a grant; competing claims → senior claims assessor.

### 9.4 Policy-in-force & early-years / non-disclosure checks
*meta: doc=05-OPS | sec=9.4 | aud=back_office | type=claims | data=mixed*
Confirm the policy was in force. For early claims, review against **CIDRA (Consumer Insurance (Disclosure and Representations) Act 2012)**: the customer's duty is to **take reasonable care not to make a misrepresentation**; remedies depend on whether a qualifying misrepresentation was **deliberate/reckless** (avoid, refuse, retain premium where fair) or **careless** (proportionate remedy). Investigate fairly, evidence the original Q&A, apply Consumer Duty and vulnerability care.

### 9.5 Sanctions screening before payment
*meta: doc=05-OPS | sec=9.5 | aud=back_office | type=claims | data=mixed*
Screen claimant/beneficiary against the **UK Sanctions List**; a confirmed match halts payment and is reported to **OFSI**.

### 9.6 Trust vs estate payment
*meta: doc=05-OPS | sec=9.6 | aud=back_office | type=claims | data=mixed*
In trust/valid nomination: pay trustees/beneficiaries, usually no grant needed, faster. To the estate: pay personal representatives on the grant.

### 9.7 IHT interaction (signpost, no tax advice)
*meta: doc=05-OPS | sec=9.7 | aud=back_office | type=claims | data=mixed*
Policy in trust generally outside the estate; policy to the estate may be within it (40% above available nil-rate bands; NRB £325,000, RNRB up to £175,000, 2025/26, frozen). Signpost the product doc and a professional adviser. For pensions, note the legislated IHT change from 6 April 2027.

### 9.8 Terminal illness claims (Lifelong Protection)
*meta: doc=05-OPS | sec=9.8 | aud=back_office | type=claims | data=mixed*
Where offered, a claim on medical evidence of a terminal prognosis (commonly life expectancy under 12 months — per plan terms). Need SV; the life assured's **consent** to obtain medical evidence (special-category — 4.3); medical reports. Heightened vulnerability sensitivity.

### 9.9 Timescales and authority
*meta: doc=05-OPS | sec=9.9 | aud=back_office | type=table | data=fictional*
Acknowledge notification **1 business day**; issue requirements **3 business days**; assess **5 business days** from full documents; pay **5 business days** from assessment. Claim-payment authority: handler ≤ **£50,000**; team manager **£50,000–£250,000**; **dual authorisation** above **£250,000**; Head of Claims above **£1,000,000**; declined/non-disclosure and disputed claims require senior claims + compliance sign-off regardless of value.

---

## 10. HANDLING REGULATORS AND GOVERNMENT / LEGAL THIRD PARTIES
*meta: doc=05-OPS | sec=10 | aud=all | type=overview | data=mixed*

### 10.1–10.3
*meta: doc=05-OPS | sec=10.1 | aud=regulatory | type=legal | data=real*
Covers FCA, HMRC, TPR, courts, police, OFSI, ICO. Front line does **not** disclose; capture the request and route to the control function (DPO / MLRO / Tax / Legal). Require written, headed, signed requests citing a legal basis; confirm the named officer. Emergency/life-at-risk requests escalated immediately to the DPO.

### 10.4 Legal basis for disclosing to authorities (real)
*meta: doc=05-OPS | sec=10.4 | aud=regulatory | type=legal | data=real*
The **DPA 2018 Schedule 2 para 2 "crime and taxation" exemption** disapplies certain UK GDPR transparency/individual-rights provisions **to the extent** compliance would prejudice crime prevention/detection, apprehension/prosecution, or assessment/collection of tax — applied case by case; still identify a lawful basis (and Art 9/Schedule 1 condition for special-category/criminal data). Disclosure may also be required by court order. Disclose only what is necessary and proportionate.

### 10.5 Who authorises internally
*meta: doc=05-OPS | sec=10.5 | aud=regulatory | type=legal | data=real*
DPO (ICO/data); MLRO/Head of Financial Crime (law-enforcement/financial-crime); Legal/Company Secretary (court orders/FCA), with senior sign-off.

### 10.6 No tipping off
*meta: doc=05-OPS | sec=10.6 | aud=regulatory | type=legal | data=real*
In money-laundering cases, do not reveal a SAR has been/may be made — the **tipping-off** offence (POCA 2002 s.333A). Route via the MLRO.

---

## 11. COMPLAINTS HANDLING (DISP-based)
*meta: doc=05-OPS | sec=11 | aud=all | type=overview | data=mixed*

Handled under FCA **DISP** and the **Consumer Duty**. Subsections: recognition (11.1), timescales (11.2), FOS rights (11.3), redress (11.4), root cause and reporting (11.5).

### 11.1 Definition and recognition
*meta: doc=05-OPS | sec=11.1 | aud=back_office | type=procedure | data=real*
A complaint is **any expression of dissatisfaction**, oral or written, about a product or service, alleging financial loss, material distress or inconvenience. The customer need not use the word "complaint". Recognition is a front-office duty — "I'm not happy", "this is unacceptable", "I've had to call three times" all qualify; recognition prompts and the do-not-deflect rule are in **Doc 7 §2.5**. **Log every complaint** as `CMP-` with root-cause data, in the same contact. A complaint may be made by the customer or an authorised representative.

### 11.2 Timescales and final response
*meta: doc=05-OPS | sec=11.2 | aud=back_office | type=procedure | data=real*
Acknowledge promptly and keep the complainant updated. **Summary resolution communication** where resolved by close of the **third business day** after receipt (DISP 1.5). Otherwise issue a **final response by the end of 8 weeks** (DISP 1.6). If it is not resolved by 8 weeks, send a written explanation of why, when a response is expected, and the complainant's **Financial Ombudsman Service** referral rights. These are **calendar** clocks — they do not pause for weekends or holidays.

### 11.3 FOS referral rights and jurisdiction
*meta: doc=05-OPS | sec=11.3 | aud=back_office | type=procedure | data=real*
Eligible complainants may refer to the **FOS** free of charge, generally within **six months** of the date the firm sent its final response (DISP 2.8.2R), subject to the six-year/three-year limits — and the final response **must** state that six-month limit. Contract-based personal pensions fall to the FOS; some occupational-scheme administration disputes fall to **The Pensions Ombudsman** instead — signpost the correct body.

### 11.4 Redress, interest and goodwill
*meta: doc=05-OPS | sec=11.4 | aud=back_office | type=procedure | data=mixed*
Where a customer has lost out, put them back in the position they would have been in but for the error. **Financial loss:** restore the position (reinstate units at the correct price, refund charges, re-run the transaction at the correct date). **Interest:** the conventional award on money wrongly withheld or paid late is **8% simple per year** for the period the customer was out of pocket — the FOS's standard approach; deduct income tax on the interest element where required and issue a tax deduction certificate. **Distress and inconvenience:** a modest non-financial award where warranted. **Goodwill:** discretionary, capped at **£250** at team-manager level, above that senior sign-off; goodwill must never be used to buy off a valid complaint or to avoid recording a root cause. Worked calculation and remediation process: **Doc 7 §7.3**.

### 11.5 Root cause and reporting
*meta: doc=05-OPS | sec=11.5 | aud=ops | type=procedure | data=real*
Capture cause, product, outcome and redress against the root-cause taxonomy (Doc 7 §7.2); feed themes into product governance and the annual Consumer Duty outcomes assessment. Report under **DISP 1.10** (consolidated return; first reporting period **1 January – 30 June 2027** per PS25/19) and publish a complaints summary where a return reports **500+** complaints (DISP 1.10A). Retain complaint records at least 3 years.

## 12. VULNERABLE CUSTOMERS
*meta: doc=05-OPS | sec=12 | aud=all | type=overview | data=mixed*

Grounded in FCA **FG21/1** and the **Consumer Duty**. Subsections: framework (12.1), identifying and recording (12.2), adjustments (12.3), safeguarding (12.4). Live-contact practice, disclosure protocols and bereavement standards: **Doc 7 §3**.

### 12.1 Framework and definition
*meta: doc=05-OPS | sec=12.1 | aud=back_office | type=legal | data=real*
A vulnerable customer is someone who, due to their personal circumstances, is **especially susceptible to harm**, particularly when a firm is not acting with appropriate care. Vulnerability is a spectrum driven by four factors: **health, life events, resilience, capability**. It is frequently **transient** — a bereaved customer may need support now and not in six months — so support records are reviewed, not permanent.

### 12.2 Identifying and recording
*meta: doc=05-OPS | sec=12.2 | aud=back_office | type=procedure | data=mixed*
Enable disclosure through any channel. Record the **support need and the adjustment**, never a "vulnerable" label. Support-need data may be **special-category** (health) — capture with an appropriate lawful basis and Art 9 condition, minimise, and restrict access (§4.3). Explicit consent to record is obtained using the disclosure protocol in **Doc 7 §3.2**.

### 12.3 Reasonable adjustments and authorised helpers
*meta: doc=05-OPS | sec=12.3 | aud=back_office | type=procedure | data=real*
Offer adjustments: more time, alternative formats (large print, Braille, audio), a trusted third party present, specialist-team handling, interpreter and relay services. The **Equality Act 2010** duty to make reasonable adjustments applies alongside FCA guidance. Under **PRIN 2A.6.5R**, a person authorised to help conduct the customer's affairs (e.g. under a power of attorney) receives the **same level of support** as the customer. Outcomes for vulnerable customers must be **at least as good** as for others.

### 12.4 Safeguarding and suspected financial abuse
*meta: doc=05-OPS | sec=12.4 | aud=back_office | type=procedure | data=mixed*
Where financial abuse or a scam is suspected — a third party directing a withdrawal that benefits them, a customer unable to explain a large payment, signs of coercion — **pause the transaction**, escalate to the vulnerability/specialist team and, where relevant, Financial Crime, and consider a safeguarding referral. Balance the customer's autonomy against protection from harm, and document the reasoning **whichever way** the decision goes. Pause-and-escalate language: **Doc 7 §3.3**.

---

## 13. FRAUD AND FINANCIAL CRIME CONTROLS IN SERVICING
*meta: doc=05-OPS | sec=13 | aud=all | type=overview | data=mixed*

Subsections: impersonation (13.1), APP/bank-change fraud (13.2), sanctions (13.3), SARs and tipping off (13.4), CDD/EDD (13.5), source of funds (13.6), holds (13.7).

### 13.1 Impersonation fraud
*meta: doc=05-OPS | sec=13.1 | aud=back_office | type=procedure | data=mixed*
Identity gates (§3), confirmations to registered contacts only, and step-up triggers are the primary defences. Failed or suspicious verification is logged and referred to Financial Crime (`FC-`). Social-engineering patterns to watch: partial data knowledge, manufactured urgency, hostility to verification, audible coaching, and a caller who "just needs" one detail confirmed.

### 13.2 Authorised push payment (APP) and bank-change fraud
*meta: doc=05-OPS | sec=13.2 | aud=back_office | type=procedure | data=mixed*
Treat bank-detail and payee changes as high risk (§6.3, §8.1). Red flags: urgency; a third-party-supplied account; an address change followed by a bank change; background coaching; reluctance to use registered contacts; a "helper" who benefits from the payment. Controls: **EV**, **Confirmation of Payee** (Doc 7 §5.3), verification holds, confirmation to the registered contact, and escalation **before** funds are released. A returned payment is a known re-entry point for this fraud (Doc 7 §5.4).

### 13.3 Sanctions (OFSI)
*meta: doc=05-OPS | sec=13.3 | aud=back_office | type=legal | data=real*
Screen customers and payees against the **UK Sanctions List** (administered by **OFSI** under the Sanctions and Anti-Money Laundering Act 2018). Sanctions breaches are **strict liability**. On a confirmed match: **do not deal** with the funds or make them available; **freeze**; report to **OFSI without delay**; notify the FCA where relevant. This is never a commercial or risk-based judgement and is never waived for a plausible explanation.

### 13.4 Money laundering — SARs and tipping off
*meta: doc=05-OPS | sec=13.4 | aud=back_office | type=legal | data=real*
Staff who **know or suspect** money laundering must make an **internal SAR** to the **MLRO** without delay (POCA 2002 s.330). The MLRO decides on an external SAR to the **NCA** and, where the firm needs to proceed with a suspicious transaction, seeks a **Defence Against Money Laundering (DAML)**: notice period **seven working days** from the first working day after disclosure; if refused, a **31-day moratorium**, extendable by court order to a maximum of **186 days** (s.336A). **Never tip off** (s.333A) — do not tell a customer that a report has been or may be made, or that an investigation is contemplated; use neutral language and route queries via the MLRO.

### 13.5 CDD, SDD and EDD
*meta: doc=05-OPS | sec=13.5 | aud=back_office | type=legal | data=real*
Apply CDD at onboarding and when risk changes (MLR 2017 regs 27–28); life-policy **beneficiaries may be verified at or before payout**. **SDD** where genuinely low-risk (reg 37 — "a life insurance policy for which the premium is low" is a low-risk factor; the old MLR 2007 numeric exemption is repealed, so this is a risk factor, not an automatic exemption). **EDD** (regs 33, 35) for high-risk situations, FATF-listed **high-risk third countries**, and **PEPs**, their family members and close associates — senior-management approval, source of wealth and funds, enhanced ongoing monitoring continuing at least 12 months after the PEP leaves office. Follow **JMLSG** guidance (Part II §7, life sector).

### 13.6 Source of funds and wealth
*meta: doc=05-OPS | sec=13.6 | aud=back_office | type=procedure | data=mixed*
Establish source of funds for large or unusual inflows (§7.1 triggers: single ≥£25,000; aggregate ≥£50,000 in 12 months; any third-party payment; any high-risk-jurisdiction link) and source of **wealth** for EDD cases. Evidence, not assertion: bank statements, sale completion statements, probate documents, accountant's confirmation. Unexplained or evasive answers are themselves a suspicion indicator (§13.4).

### 13.7 Holds and account restrictions
*meta: doc=05-OPS | sec=13.7 | aud=back_office | type=procedure | data=fictional*
Financial Crime may place a hold on a policy or transaction pending investigation, a DAML decision or a sanctions determination. Holds are documented on `FC-`, time-limited and reviewed weekly; customer communications are managed with neutral language to avoid **tipping off** (§13.4). Release requires MLRO or Head of Financial Crime authorisation. A hold is never explained to the customer as "a money-laundering check".

## 14. AUTHORITY LEVELS MATRIX (fictional but realistic)
*meta: doc=05-OPS | sec=14 | aud=back_office | type=table | data=fictional*

| Transaction | Front office | Back office | Ops/Team manager | Senior manager | Dual authorisation |
|---|---|---|---|---|---|
| Disclose info after SV | ✅ | ✅ | — | — | — |
| Change of address / preferences | ✅ | ✅ | — | — | — |
| Change of name (with evidence) | — | ✅ | — | — | — |
| Change of bank/DD (EV) | — | ✅ | approves first payment | — | — |
| Contribution/premium change | — | ✅ | — | — | — |
| Beneficiary / trust / trustee change | — | ✅ | senior case handler | — | — |
| Top-up ≤ £25,000 | — | ✅ | — | — | — |
| Top-up > £25,000 / EDD case | — | prepares | — | approves | — |
| Withdrawal/surrender ≤ £25,000 | — | ✅ | — | — | — |
| Withdrawal/surrender £25,000–£100,000 | — | prepares | approves | — | — |
| Withdrawal/surrender > £100,000 | — | prepares | — | approves | ✅ above £250,000 |
| Pension access (any) | — | ✅ (within band) | approves > £50,000 | approves > £250,000 | ✅ above £250,000 |
| Transfer out / DB transfer | — | prepares | — | approves (advice verified) | ✅ high value |
| Death claim ≤ £50,000 | — | ✅ | — | — | — |
| Death claim £50,000–£250,000 | — | prepares | approves | — | — |
| Death claim > £250,000 | — | prepares | — | approves | ✅ |
| Death claim > £1,000,000 | — | prepares | — | Head of Claims | ✅ |
| Declined/non-disclosure claim | — | prepares | — | senior claims + compliance | — |
| Disclosure to regulator/police/court | — | — | — | DPO/MLRO/Legal | — |
| Sanctions freeze & OFSI report | — | — | escalate | MLRO/Head of Financial Crime | — |

---

## 15. SLA / PROCESSING-TIMESCALE TABLE (fictional)
*meta: doc=05-OPS | sec=15 | aud=ops | type=table | data=fictional*

| Transaction | Target SLA |
|---|---|
| Change of address / preferences / marketing opt-out | Same day (marketing suppression ≤ 24h) |
| Change of name (from evidence) | 3 business days |
| Change of bank/Direct Debit | 2 business days (+ verification hold) |
| Contribution/premium change | 3 business days / next cycle |
| Indexation add/remove | 3 business days |
| Beneficiary / expression of wishes | 5 business days |
| Trust set-up / trustee change | 10 business days |
| Fund switch | Instruction placed ≤ 2 business days |
| Target retirement age change | 3 business days |
| Duplicate documents | 3 business days |
| Top-up (standard / EDD) | 3 / 5–10 business days |
| Withdrawal / surrender (standard) | 5 business days after checks |
| Pension access | 5–10 business days |
| Transfer in / out | 10 business days (+ ceding-scheme time) |
| DSAR | 1 month (extendable to 3) |
| Personal data breach to ICO | ≤ 72 hours (where reportable) |
| Complaint — summary resolution / final response | 3rd business day / by 8 weeks |
| Death notification / requirements / assessment / payment | 1 / 3 / 5 / 5 business days |

**Business-day definition (applies to every SLA above):** Monday–Friday excluding England & Wales bank holidays; **daily cut-off 15:00** — instructions received after cut-off count from the next business day. Payment rails, value dates and cut-offs: **Doc 7 §5.2**. Statutory clocks (DSAR one month, ICO 72 hours, DISP 8 weeks) run in **calendar** time and never pause for weekends.

---

## 16. OPS / OVERSIGHT LAYER
*meta: doc=05-OPS | sec=16 | aud=ops | type=overview | data=mixed*

Subsections: queues/KPIs/QA (16.1), escalation (16.2), regulatory reporting (16.3), customer protections (16.4), AI monitoring (16.5). Operating cadence, QA sampling rates and governance forums: **Doc 7 §7**.

### 16.1 Queues, KPIs and quality assurance
*meta: doc=05-OPS | sec=16.1 | aud=ops | type=ops | data=fictional*
Ops monitors work queues by transaction type, age and SLA status, escalating breached and near-breach items. KPIs: SLA attainment, first-contact resolution, verification-failure rate, complaint volumes and upheld rate, claims cycle time, DSAR on-time rate, breach count, sanctions-hit rate. Risk-based **QA sampling** (higher for bank changes, withdrawals, claims and vulnerability) checks identity and authority gates, data minimisation, Consumer Duty outcomes and record quality (**SYSC 9** — orderly, sufficient, retrievable). Sampling rates, scoring and calibration: **Doc 7 §7.1**.

### 16.2 Breach, incident and complaint escalation
*meta: doc=05-OPS | sec=16.2 | aud=ops | type=ops | data=mixed*
Ops runs the breach register (`BR-`, §4.9) and complaints MI (§11.5); root-cause themes feed product and process fixes under the Consumer Duty. Operational incidents follow the severity model and major-incident process in **Doc 7 §6**; a potential personal-data element starts the 72-hour ICO assessment clock in parallel, never after the incident closes.

### 16.3 Regulatory reporting touchpoints
*meta: doc=05-OPS | sec=16.3 | aud=ops | type=ops | data=real*
**FCA:** complaints return under DISP 1.10 — a single consolidated return per **PS25/19**, first reporting period **1 January – 30 June 2027** — plus complaints publication under DISP 1.10A where a return reports 500+ complaints. **ICO:** personal-data-breach reporting (72 hours) and DSAR oversight. **HMRC:** chargeable-event certificates (Bond); relief-at-source and event reporting (Pension). **OFSI:** sanctions reporting. **NCA:** SARs via the MLRO. **TPR:** auto-enrolment touchpoints.

### 16.4 Customer protections referenced in oversight
*meta: doc=05-OPS | sec=16.4 | aud=ops | type=ops | data=real*
**FOS** — independent referral (§11.3). **FSCS** — long-term insurance (life assurance, insured personal pensions and annuities) protected at **100% with no upper limit** on firm failure; investments and SIPP operators to £85,000. For context the FSCS **deposit** limit rose to £120,000 per person per firm from 1 December 2025 — not the relevant limit for Aldercrest's long-term insurance business.

### 16.5 AI data-flow monitoring
*meta: doc=05-OPS | sec=16.5 | aud=ops | type=ops | data=fictional*
Ops monitors the assistant's routing accuracy (caller-type and transaction-type classification), **gate enforcement** (no disclosure before verification), escalation correctness and audit-log completeness. Any AI disclosure error is treated as a **potential personal data breach** and logged `BR-`. Metrics and trace schema: **Doc 6 §4**; behavioural limits and human-in-the-loop rules: **Doc 7 §8**.

---

## 17. AUDIENCE LAYERS (routing guide for the AI)
*meta: doc=05-OPS | sec=17 | aud=all | type=routing | data=fictional*

**(a) Customer-facing** — plain-language "what you need and what happens next": how to notify a death, what ID we need, timescales, tax signposting, complaint/FOS/FSCS rights.
**(b) Back office** — evidence checks, authority verification (OPG/probate), CDD/EDD, chargeable-event handling, case authority levels, SLAs.
**(c) Ops** — queues, KPIs, QA, breach/complaint MI, regulatory reporting, sanctions/SAR oversight, AI data-flow monitoring.
The AI selects the layer from the caller type (2.3) and the request. Regulator/police/court contacts always route to control functions (Section 10), never customer-facing self-service.

---

## 18. SOURCES (real URLs)
*meta: doc=05-OPS | sec=18 | aud=all | type=sources | data=real*

**ICO / UK GDPR / DPA 2018**
- Right of access / SARs — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/right-of-access/what-should-we-consider-when-responding-to-a-request/
- Time limits for rights requests — https://ico.org.uk/for-the-public/time-limits-for-responding-to-data-protection-rights-requests/
- Special category data — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/special-category-data/what-are-the-rules-on-special-category-data/
- Personal data breaches (72 hours) — https://ico.org.uk/for-organisations/report-a-breach/personal-data-breach/personal-data-breaches-a-guide/
- Data protection exemptions — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/exemptions/a-guide-to-the-data-protection-exemptions/
- Sharing data with law enforcement — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-sharing/sharing-personal-data-with-law-enforcement-authorities/
- UK GDPR Article 9 — https://www.legislation.gov.uk/eur/2016/679/article/9
- DPA 2018 Schedule 2 crime & taxation — https://www.legislation.gov.uk/ukpga/2018/12/schedule/2/part/1/crossheading/crime-and-taxation-general

**FCA Handbook / FCA**
- DISP 1.6 (complaints time limits) — https://handbook.fca.org.uk/handbook/disp1/disp1s6
- DISP 2.8 (FOS time limits) — https://handbook.fca.org.uk/handbook/disp2/disp2s8
- DISP 1.10 (complaints reporting) — https://handbook.fca.org.uk/handbook/DISP/1/10.html
- DISP 1.10A (complaints data publication) — https://handbook.fca.org.uk/handbook/DISP/1/10A.html
- PS25/19 (improving complaints reporting) — https://www.fca.org.uk/publications/consultation-papers/ps25-19-improving-complaints-reporting-process
- FG21/1 vulnerable customers — https://www.fca.org.uk/publications/finalised-guidance/guidance-firms-fair-treatment-vulnerable-customers
- COBS 19 (pensions) — https://handbook.fca.org.uk/handbook/COBS/19
- SYSC 9 record-keeping — https://handbook.fca.org.uk/handbook/sysc9/sysc9s1
- ScamSmart — https://www.fca.org.uk/scamsmart

**Financial crime / sanctions**
- POCA SARs / tipping off (NCA) — https://www.nationalcrimeagency.gov.uk/what-we-do/crime-threats/money-laundering-and-illicit-finance/suspicious-activity-reports
- OFSI UK financial sanctions guidance — https://www.gov.uk/government/publications/financial-sanctions-general-guidance/uk-financial-sanctions-general-guidance

**Powers of attorney / probate / bereavement**
- OPG100 register search — https://www.gov.uk/government/publications/find-out-if-someone-has-a-registered-attorney-or-deputy
- Use a lasting power of attorney — https://www.gov.uk/use-lasting-power-of-attorney
- Tell Us Once — https://www.gov.uk/after-a-death/organisations-you-need-to-contact-and-tell-us-once
- Death Notification Service — https://www.deathnotificationservice.co.uk/

**Consumer protections / tax**
- FSCS what we cover — https://www.fscs.org.uk/what-we-cover/
- FSCS pensions protection — https://www.fscs.org.uk/what-we-cover/pensions/
- FOS misrepresentation & non-disclosure (CIDRA) — https://www.financial-ombudsman.org.uk/businesses/complaints-deal/insurance/misrep-and-non-disclosure
- The Pensions Ombudsman — https://www.pensions-ombudsman.org.uk/
- Pension Wise (MoneyHelper) — https://www.moneyhelper.org.uk/en/pensions-and-retirement/pension-wise
- HMRC Inheritance Tax on pensions (from 6 April 2027) — https://www.gov.uk/government/publications/inheritance-tax-on-pensions
- HMRC tax on your private pension — https://www.gov.uk/tax-on-your-private-pension

---

## 19. DATA DICTIONARY — core entities and fields
*meta: doc=05-OPS | sec=19 | aud=back_office | type=data_dictionary | data=fictional*
Machine-readable schema behind the sample records (product docs §III.4) and workflows. Validation notes in brackets.

**Party** — `party_id`; `name`; `dob` [ISO date]; `registered_address`; `contact` (phone/email, registered flag); `scottish_taxpayer` [bool]; `vulnerability_flag` [none|support-needs ref, special-category care]; `id_verified_level` [none|SV|EV, timestamped].
**Policy** — `policy_no` [`LP-|HB-|RA-` + 8 digits]; `product`; `status` [in force|lapsed|paid-up|claimed|surrendered]; `start_date`; `holder_party_id`; `lives_assured[]`; `trust_ref` [nullable]; `adviser_loa` {firm, FRN, scope, expiry}; `bank_last4`.
**CoverComponent (LP)** — `sum_assured`; `basis` [guaranteed|reviewable|unit-linked]; `riders[]` [waiver|GIO]; `next_review_date`; `indexation` [on|off].
**FundHolding (HB/RA)** — `fund_id`; `units`; `price_date`; `value`; `pathway` [1–4|null]; (HB) `segments_total/remaining`; `5pct_allowance_used/available`.
**PensionTax (RA)** — `mpaa_triggered` [bool+date]; `protections` [FP2016|IP2016|none]; `ttfac` [ref|null]; `lsa_used`; `aa_headroom_estimate`.
**BankMandate** — `account_last4`; `verified` [bool]; `hold_until` [date]; `change_history[]` (fraud watch).
**AuthorityRecord** — `type` [LOA|LPA|EPA|deputy|PR|trustee|mandate|one-off]; `scope`; `evidence_ref` [OPG code/grant/Confirmation/deed]; `verified_date`; `status`.
**Interaction (CN-)** — `channel`; `caller_party_id`; `claimed_relationship`; `verification_outcome`; `intent`; `outcome`; `timestamps`.
**Case (CW-)** — `type` [servicing|DSAR|transfer|review]; `policy_no`; `sla_due`; `status`; `authority_level_required`; `evidence[]`.
**Claim (CLM-)** — `type` [death|terminal|death-benefit]; `date_of_death`; `age_at_death` [drives RA tax split]; `payee_basis` [trust|estate|nominee]; `sanctions_screen` [clear|hit]; `value`; `authority_band`.
**Complaint (CMP-)** — `received_date`; `summary_deadline` [day 3]; `final_deadline` [8 weeks]; `root_cause`; `outcome`; `fos_rights_sent` [bool].
**FinCrimeReferral (FC-)** — `trigger` [impersonation|APP|scam-flag|SAR|sanctions]; `hold_applied`; `mlro_decision`; `tipping_off_guard` [bool].

## 20. INTENT TAXONOMY & ROUTING MAP (atomic table)
*meta: doc=05-OPS | sec=20 | aud=all | type=routing | data=fictional*

| # | User intent (example utterance) | Route to | Audience |
|---|---|---|---|
| 1 | "Change my address" | Product doc §II.6.1 / here 6.1 | customer→back_office |
| 2 | "Update my bank details" | §II.6.3 / 6.3 (EV) | back_office |
| 3 | "How much can I withdraw tax-free from my bond?" | Doc 2 §4.2, §4.9 | customer |
| 4 | "Take £X from my bond" | Doc 2 §II.8 | back_office |
| 5 | "Take my tax-free cash / start drawdown" | Doc 3 §9.1–9.2, §II.8.2 | back_office |
| 6 | "What's the MPAA / can I still pay in?" | Doc 3 §4.3, §II.6.5 | customer |
| 7 | "Increase my life cover after having a baby" | Doc 1 §3.7, §II.6.9 | customer→back_office |
| 8 | "My premium review letter says pay more" | Doc 1 §3.8, §II.11 | customer |
| 9 | "Report a death" | Product doc §II.9 / here §9 | customer→back_office |
| 10 | "I'm an executor — what do you need?" | §5.5 / product §II.9 | customer |
| 11 | "I hold LPA for my mother" | §5.2 / product §II.5 | back_office |
| 12 | "Put my policy in trust" | Doc 1 §4.3–4.4, §II.6.8 | customer→back_office |
| 13 | "Switch my funds" | Product §II.6 (switch) / 6.9 | back_office |
| 14 | "Transfer my old pension in" | Doc 3 §II.6.10 + §II.12 | back_office |
| 15 | "Transfer out to another scheme" | Doc 3 §II.6.10, §II.13 | back_office |
| 16 | "Make a complaint" | §11 / product §II.11 | customer→back_office |
| 17 | "Send me all my data" (DSAR) | §4.7 / product §II.4.4 | back_office |
| 18 | "Police/HMRC information request" | §10 / product §II.10 | regulatory |
| 19 | "Am I protected if you go bust?" | §16.6 / Doc 4 A10 | customer |
| 20 | "Divorce — pension sharing order" | Doc 3 §11, §II.6.9 | back_office |
| 21 | "Why was my first pension payment overtaxed?" | Doc 3 §9.8 | customer |
| 22 | "Scam worry / cold call about my pension" | Doc 3 §II.12 | customer→back_office |
| 23 | Ops: "queue/SLA/KPI status" | §16 / product §II.15 | ops |
| 24 | Ops: "complaints return due when?" | §16.5 / Doc 4 A9a | ops |

## 21. CROSS-SOURCE DEMO SCENARIOS (multi-document reasoning)
*meta: doc=05-OPS | sec=21 | aud=all | type=case_study | data=mixed*
Designed to prove the RAG system reasons **across** sources. Complexity mix: WoL = LOW–MEDIUM, Bond = MEDIUM–HIGH (tax arithmetic), Pension = HIGH (allowance interplay).
1. **"Delta holds LPA and wants £30,000 from his mother's bond to a new account."** Needs: §5.2 (OPG verification) + §3.3/6.3 (EV, new payee) + Doc 2 §4.9/§II.8.2 (method comparison, excess-gain warning) + §13.2 (APP/abuse screen). 4-source chain with a safeguarding fork.
2. **"Scottish member, 55, wants one lump sum but plans to keep saving £900/month."** Needs: Doc 3 §9.3 vs §9.5 (UFPLS triggers MPAA; ≤£10,000 small pot doesn't) + §4.3 + §12 (S-code PAYE) + §9.8 (emergency tax). The correct answer changes with pot size — genuine reasoning, not lookup.
3. **"Trustees of a discretionary trust ask what tax arises if they surrender the bond vs assign segments to the adult beneficiary."** Needs: Doc 2 §4.8 (25% trustee rate, no top-slicing) + §4.7/§4.9 (gift assignment moves the gain) + Doc 1 §4.3 (trust context) + advice signpost.
4. **"Claim on a 10-month-old £500,000 whole of life policy; the death certificate says cause unknown."** Needs: Doc 1 §3.5 (suicide clause window) + §II.9.1 (CIDRA review) + §II.9.3/§II.13 (dual authorisation band) + Doc 4 (FOS if declined).
5. **"Member with Fixed Protection 2016 asks the AI to set up a £200/month contribution."** Needs: Doc 3 §4.6 (contribution voids FP2016) + §II.6.5 — correct behaviour is warn-and-refer, not process. Tests guardrails.
6. **"ICO deadline check: SAR received 30 June, complaint received 2 May, breach discovered Friday 6pm."** Needs: §4.7 (one month), §11 (8 weeks), §4.9 (72h, no weekend pause) — three clocks from three frameworks in one answer.

## 22. CHUNKING & METADATA CONVENTION (applies to all five documents)
*meta: doc=05-OPS | sec=22 | aud=all | type=routing | data=fictional*
- **Splitter:** heading-aware/recursive — split on `##`/`###`; every heading = one chunk; size-cap 800 tokens (merge tiny neighbours under the same parent up to ~500).
- **Overlap:** ~10% (60–120 tokens) on long prose only; **never** overlap-split tables, matrices, source lists, sample records — these are **atomic**.
- **Meta line schema** (first line under each heading): `doc` (01-WOL | 02-BOND | 03-PEN | 04-FCA | 05-OPS) · `sec` · `aud` (customer | back_office | ops | all | regulatory) · `type` (overview, eligibility, product_rule, tax_rule, journey, procedure, claims, table, legal, ops, glossary, faq, sample_record, case_study, routing, sources, worked_example, caveats, data_dictionary) · `data` (real | fictional | mixed). Index these as filterable fields; pre-filter by `aud` and `doc/product` before vector search.
- **Duplication handling:** identity/data-protection/financial-crime rules intentionally repeat per product for self-containment — dedupe at query time (MMR) or scope by `doc`.
- **Default audience for Doc 5 sections without inline meta:** 1–2 all; 3–9 back_office; 10 regulatory; 11–13 back_office; 14–15 back_office/ops tables; 16 ops; 17 all; 18 sources; 19 back_office; 20–22 all.
- **Citation rule for the app:** `data=real` chunks cite the Part C / §II.16 URL; `data=fictional` values are flagged as Aldercrest's own rules.

### Change log
*meta: doc=05-OPS | sec=Change log | aud=all | type=overview | data=mixed*
v2026.2 (13 July 2026): §6 split into per-procedure chunks; added §19 data dictionary, §20 intent routing, §21 cross-source scenarios, §22 chunking convention. Product docs 1–3 and Doc 4 rebuilt as v2 with expanded rules, Part III RAG assets and inline metadata.

### Document control
*meta: doc=05-OPS | sec=Document control | aud=all | type=overview | data=mixed*
- **Status:** Live (Version 2026.1). **Next review:** by 13 July 2027 or on material regulatory change.
- **Forward-looking items to monitor:** minimum pension age → 57 (6 April 2028); unused pension funds within IHT estate (6 April 2027); FCA consolidated complaints return first period (1 Jan–30 Jun 2027, PS25/19); commencement of the Data (Use and Access) Act 2025.
- **Fictional vs real:** all thresholds, team names, reference formats, SLAs and authority bands are Aldercrest Life's own (fictional) operating standards; all statutory/regulatory rules and 2025/26 figures are grounded in the real UK sources in Section 18.

*End of Document 5. The tailored, product-specific version of this operations layer is embedded as "Part II" in each of Documents 1–3.*
