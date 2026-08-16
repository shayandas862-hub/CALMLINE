# DOCUMENT 1 — WHOLE OF LIFE ASSURANCE (PRODUCT MASTER) v2
*meta: doc=01-WOL | sec=frontmatter | aud=all | type=caveats | data=mixed*
## Aldercrest "Lifelong Protection"
*meta: doc=01-WOL | sec=frontmatter-title | aud=all | type=caveats | data=mixed*

**Fictional company:** Aldercrest Life Assurance plc ("Aldercrest Life"). Not a real FCA-authorised insurer; any resemblance coincidental.
**Grounding:** All regulators (FCA, PRA, HMRC, FOS, FSCS, ICO, OFSI, OPG) and all tax/regulatory figures are real, current for 2025/26, verified against sources in Document 4 and §II.16. Aldercrest charges, limits, SLAs and thresholds are fictional but realistic. Knowledge-base date: **13 July 2026.** Finance Act 2026 changes (Royal Assent 18 March 2026) that start in later tax years are flagged "legislated, not yet in force."
**RAG formatting convention:** split on headings — every `##`/`###` is one chunk (target 500–800 tokens; ~10% overlap for long prose only). Tables and Sources sections are **atomic** chunks. Each section carries a `meta:` line — `doc` | `sec` | `aud` (customer / back_office / ops / all / regulatory) | `type` | `data` (real = UK law/tax; fictional = Aldercrest standard; mixed).
**Complexity tier for RAG demo:** LOW–MEDIUM (protection logic, trust/IHT reasoning). Compare Bond (tax maths) and Pension (allowance interplay).

---

# PART I — PRODUCT

## 1. What the product is and its purpose
*meta: doc=01-WOL | sec=1 | aud=all | type=overview | data=mixed*
Whole of life assurance is a long-term contract of insurance that pays a guaranteed lump sum (the **sum assured**) whenever the life assured dies, for as long as premiums are maintained. Unlike term assurance, it has **no fixed end date** — a valid claim is certain provided the policy stays in force. Aldercrest Lifelong Protection is fundamentally a **protection** product, not an investment.

**Primary purposes:** leaving a guaranteed legacy/inheritance; funding an expected **inheritance tax (IHT)** liability so the estate need not be sold to pay it; funeral/final-expenses provision; and business protection (e.g. shareholder/key-person cover).

**Regulatory classification** (determines the FCA conduct rules — see Document 4 Part B): a whole of life plan with a surrender value or **unit-linked** element is a "life policy" and **designated investment business** under **COBS**; a **pure protection** plan with **no surrender value** falls under **ICOBS** (a firm may elect COBS).

**Aldercrest variants:** **Guaranteed (non-profit)** — premiums and sum assured fixed for life; no/negligible surrender value. **Reviewable** — premiums reviewed (first review year 10, then 5-yearly; mechanics in §3.8). **Unit-linked** — premiums buy fund units; monthly deduction meets the cost of cover; the plan has a surrender value.

## 2. Target market and eligibility
*meta: doc=01-WOL | sec=2 | aud=all | type=eligibility | data=fictional*
- **Target market:** adults wanting lifelong cover for estate/IHT planning, final expenses, or dependants with lifelong needs. **Not suitable** for temporary needs (term assurance is cheaper) or pure investment aims (bond/pension more suitable).
- **Entry age:** 18–85. **Residency:** UK resident at application; law of England & Wales (Scotland/NI variations in §10).
- **Lives assured:** single life; joint-life-first-death; **joint-life-second-death** (IHT planning — pays on the second death of a couple, when the IHT bill typically falls due; mechanics §3.9).
- **Minimum sum assured:** £5,000. No statutory maximum (underwriting and financial justification apply).

## 3. Product rules, features, charges

### 3.1 Cover shape and premiums
*meta: doc=01-WOL | sec=3.1 | aud=all | type=product_rule | data=fictional*
Cover: level; increasing/indexed (RPI or fixed % p.a.); or, for unit-linked, a maximum-cover / balanced / minimum-cover investment split. Premiums: monthly or annual Direct Debit; payable for life or ceasing at a chosen age (e.g. 90) with cover continuing.

### 3.2 Charges
*meta: doc=01-WOL | sec=3.2 | aud=all | type=product_rule | data=fictional*
Monthly policy fee £4.50. Unit-linked: fund AMCs 0.35%–1.00%; monthly cost-of-cover deduction by unit cancellation; allocation/valuation adjustments as disclosed in the Key Features Document.

### 3.3 Death benefit and surrender value
*meta: doc=01-WOL | sec=3.3 | aud=all | type=product_rule | data=fictional*
Death benefit: the greater of the sum assured and (unit-linked) the bid value of units (often 101% of fund value). Surrender value: guaranteed plans typically none; unit-linked plans have fund value less outstanding charges (often little in early years).

### 3.4 Terminal illness benefit
*meta: doc=01-WOL | sec=3.4 | aud=all | type=product_rule | data=fictional*
Standard feature: pays the sum assured early on diagnosis of a terminal illness with life expectancy under 12 months (claim process §II.9.2). Not payable where life expectancy exceeds 12 months or within the last 12 months of any premium-cessation age chosen.

### 3.5 Exclusions and the suicide clause
*meta: doc=01-WOL | sec=3.5 | aud=all | type=product_rule | data=fictional (aligned to UK market practice)*
Aldercrest applies minimal exclusions, consistent with UK market practice: **suicide within 12 months** of the start date, reinstatement date, or any increase (to the amount of the increase) — no benefit is payable and premiums are not refunded, except any amount payable to a lender under a deed of assignment. Fraud/misrepresentation is handled under CIDRA (§II.9.1 step 4), not as an exclusion. War/hazardous-pursuit exclusions apply only where an underwriting decision imposed them and they appear in the policy schedule.

### 3.6 Waiver of premium (optional rider)
*meta: doc=01-WOL | sec=3.6 | aud=all | type=product_rule | data=fictional*
Optional at outset (extra premium): if the policyholder is incapacitated and unable to follow their own occupation for more than the **26-week deferred period**, Aldercrest waives premiums for the duration of incapacity, up to the rider ceasing age of **65**. Claims need medical evidence (special-category data — §II.4.2) and periodic review. Cover continues in full while premiums are waived.

### 3.7 Guaranteed insurability option (GIO) — detailed rules
*meta: doc=01-WOL | sec=3.7 | aud=all | type=product_rule | data=fictional*
Where included, the policyholder may increase the sum assured **without medical evidence** within **90 days** of: marriage/civil partnership; birth or adoption of a child; or a new/increased mortgage. Limits: each increase ≤ the lower of **50% of the original sum assured** or **£150,000**; aggregate GIO increases ≤ **100% of the original sum assured**; option ends at age **55**, on claim, or if premiums are in arrears. The increase carries its own 12-month suicide restriction (§3.5) and is priced at the then-current rates for the life assured's age.

### 3.8 Reviewable premiums — review mechanics
*meta: doc=01-WOL | sec=3.8 | aud=all | type=product_rule | data=fictional*
At year 10 and 5-yearly after, Aldercrest tests whether the unit fund plus current premiums can sustain the cost of cover to age 100 on the review basis. Outcomes: (a) premiums unchanged; (b) premium increase required; (c) if the customer declines an increase, the **sum assured is reduced** to the supportable level; (d) on later reviews a plan can become unsustainable — the customer may pay more, reduce cover, or let the plan run until the fund is exhausted (it then lapses without value). **No new underwriting at review.** Review letters must meet Consumer Duty understanding standards; a review is a common complaint trigger (§II.11).

### 3.9 Joint-life mechanics
*meta: doc=01-WOL | sec=3.9 | aud=all | type=product_rule | data=fictional*
**Joint-life-first-death:** pays once on the first death; the policy then ends; a **separation option** lets each life take a single-life policy without underwriting on divorce/dissolution (within 90 days of decree). **Joint-life-second-death:** nothing is paid on the first death; premiums continue (unless a premium-cessation option was selected); the sum assured is paid on the second death — designed to meet the IHT bill that typically arises then (spouse exemption usually defers IHT on the first death).

### 3.10 Premium arrears, grace period, lapse and reinstatement
*meta: doc=01-WOL | sec=3.10 | aud=all | type=product_rule | data=fictional*
**Grace period 30 days** from a missed premium — cover continues; a claim in the grace period is paid net of the outstanding premium. Guaranteed plans **lapse without value** after the grace period. Unit-linked plans first continue by cancelling units to meet the cost of cover until the fund is exhausted, then lapse. **Reinstatement:** within **12 months** of lapse on payment of arrears plus a satisfactory declaration of health (full re-underwriting after 6 months or for large sums); a new 12-month suicide restriction applies from reinstatement (§3.5).

## 4. Tax treatment (real UK rules)

### 4.1 Premiums and proceeds
*meta: doc=01-WOL | sec=4.1 | aud=all | type=tax_rule | data=real*
Premiums are paid from taxed income; **no income tax relief**. A death lump sum from a protection policy is generally **free of income tax and CGT** for the beneficiary.

### 4.2 Inheritance tax and the estate
*meta: doc=01-WOL | sec=4.2 | aud=all | type=tax_rule | data=real*
If the deceased owned the policy and it is **not in trust**, proceeds form part of the estate and may be taxed at **40%** above available allowances. Per GOV.UK: **nil-rate band £325,000**; **residence nil-rate band up to £175,000** (main residence to direct descendants), tapering **£1 for every £2** of estate above **£2 million**; both **frozen to 5 April 2031**; rate **36%** where 10%+ of the net estate goes to charity. **Scope note (real, from 6 April 2025):** IHT moved from a domicile basis to a **residence basis** — a person is within IHT on worldwide assets once a **long-term UK resident** (broadly 10 of the last 20 tax years); relevant when policyholders move abroad (§11).

### 4.3 Trusts — CLTs, periodic and exit charges, exemptions
*meta: doc=01-WOL | sec=4.3 | aud=all | type=tax_rule | data=real*
Writing the policy in trust takes proceeds **outside the estate** and avoids probate delay. A transfer into a **discretionary trust** is a **chargeable lifetime transfer**; the trust sits in the **relevant property regime**: **periodic charge up to 6%** of relevant property above the trust's available NRB at each 10-year anniversary, plus **exit charges**. The policy is valued at transfer and at anniversaries at broadly the **higher of open-market value and premiums paid** — so place in trust **at inception** while value is negligible. Premiums into trust are usually covered by the **£3,000 annual exemption** or **normal expenditure out of income**. A **gift with reservation** (settlor benefits) undoes the IHT advantage. *Simplified worked example:* discretionary trust holds a policy valued at £425,000 at the 10-year point with a full £325,000 NRB available → charge applies to £100,000 at up to 6% = **≤ £6,000** (actual effective rate uses the HMRC settlement-rate computation — always calculate formally).

### 4.4 Aldercrest trust forms
*meta: doc=01-WOL | sec=4.4 | aud=all | type=product_rule | data=fictional*
**Absolute (bare)** — fixed beneficiaries; the gift is a potentially exempt transfer. **Discretionary** — flexible class; relevant property regime (§4.3). **Survivor's discretionary** — joint-life: pays the surviving partner if they survive 30 days, otherwise the named beneficiaries.

## 5. HOW TO BUY — the complete new business journey
*meta: doc=01-WOL | sec=5 | aud=all | type=journey | data=mixed*
1. **Advice vs non-advised:** advised (personal recommendation, suitability) or non-advised/execution-only; protection may be sold under ICOBS or COBS.
2. **Application & quotation:** personal details, sum assured, smoker status, occupation, health questions.
3. **Underwriting:** medical questionnaire; possible GP report (consent under the **Access to Medical Reports Act 1988**), nurse screening or exam for large sums; outcomes — standard, rated, exclusions, postponed, declined.
4. **KYC/AML:** identity verification under **MLR 2017**; low-premium protection with no surrender value is typically eligible for **simplified due diligence** (reg 37); **EDD** for PEPs/high-risk (regs 33/35).
5. **Cooling-off:** **30 calendar days** (COBS 15; ICOBS pure protection also 30 days).
6. **Cooling-off refund mechanics:** protection premiums are refunded **in full** on cancellation within the period; where a unit-linked single premium was invested, a **market-loss (shortfall) deduction** may reduce the refund if unit values fell before cancellation (COBS 15 permits this for investment elements).
7. **Documents issued:** Key Features Document, illustration, policy schedule and terms, trust forms (if used), cancellation notice.

## 6. Policy servicing after set-up (summary)
*meta: doc=01-WOL | sec=6 | aud=customer | type=overview | data=fictional*
Supported: change of address/name/bank; correspondence preferences; placing in trust; changing trustees; indexation on/off; premium frequency; sum assured up/down (increases underwritten unless GIO §3.7); reinstatement (§3.10); assignment. Beneficiary changes are via the trust or nomination. **Full step-by-step procedures, evidence and SLAs: Part II §II.6.**

## 7. Putting more money in (summary)
*meta: doc=01-WOL | sec=7 | aud=customer | type=overview | data=fictional*
Sum-assured increment (underwritten unless GIO); indexation increases (annual accept/decline); unit-linked top-ups. Operational checks: **§II.7.**

## 8. Taking money out (summary)
*meta: doc=01-WOL | sec=8 | aud=customer | type=overview | data=mixed*
Full surrender ends the policy for its surrender value (unit-linked only). Partial surrender may be available on unit-linked plans. Death and terminal-illness claims: **§II.9**. Tax: proceeds free of income tax/CGT; IHT depends on trust status (§4.2–4.3).

## 9(a). CUSTOMER-FACING INFORMATION
*meta: doc=01-WOL | sec=9a | aud=customer | type=customer_info | data=mixed*
- Plain language: "This plan pays a cash sum when you die, as long as you keep paying premiums. It can help your family with an inheritance tax bill or leave a legacy."
- You can ask us to: change your details; put the plan in trust (free); change trustees; change/decline indexation; change how you pay.
- Timescales: address change 2 working days; trust deed 10 working days; death claims typically paid within 5 working days of receiving all requirements.
- Your rights: complain to Aldercrest; after a final response (or 8 weeks) go to the **FOS**, free, generally within **6 months**. **FSCS** protects long-term insurance at **100% with no upper limit**.

## 9(b). BACK OFFICE INFORMATION (summary — detail in Part II)
*meta: doc=01-WOL | sec=9b | aud=back_office | type=overview | data=fictional*
Verify identity before any disclosure; confirmations to old **and** new address on address changes; trust deeds checked and registered (10-day SLA); increments routed to underwriting with authority limits; death claims verified (certificate, in-force check, first-two-years CIDRA review, trust vs estate payee, sanctions screening, value-banded authority); exceptions — arrears, disputed beneficiaries, suspected fraud, vulnerable/bereaved handling per FG21/1.

## 9(c). OPS/OVERSIGHT INFORMATION (summary — detail in Part II)
*meta: doc=01-WOL | sec=9c | aud=ops | type=overview | data=fictional*
Queues (new business, servicing, claims, complaints) with volume/ageing MI; KPIs — % claims in SLA, claim turnaround, complaint root causes, underwriting turnaround; QA sampling and suitability review; DISP-compliant escalation; FCA complaints return, PROD 4 fair-value reviews, annual board Consumer Duty assessment.

## 10. Scotland and Northern Ireland variations
*meta: doc=01-WOL | sec=10 | aud=all | type=legal | data=real*
- **Scotland:** transfer of a policy is an **assignation** (intimation to the insurer completes it), not an assignment. On death there is **no grant of probate** — executors obtain **Confirmation** from the sheriff court; Aldercrest accepts a **Certificate of Confirmation** for the policy asset. **Legal rights (legitim):** children and spouse/civil partner have indefeasible rights over the **moveable** estate (a policy paid to the estate is moveable) — relevant to disputed-estate claims. Contractual capacity from **age 16** (Age of Legal Capacity (Scotland) Act 1991). Scots trust law differs (trustees' powers/appointments) — trust deeds must be Scots-law versions.
- **Northern Ireland:** law broadly mirrors England & Wales; grants issue from the **NI Probate Office**.
- **Income tax note:** Scottish income tax rates apply only to **non-savings** income; a WoL death benefit is not income-taxed, so no Scottish-rate effect arises on claims.

## 11. Non-UK residence and cross-border notes
*meta: doc=01-WOL | sec=11 | aud=all | type=legal | data=mixed*
Cover continues if the policyholder moves abroad (premiums must be paid from a UK bank account — fictional Aldercrest rule); new applications require UK residency. IHT exposure now follows **long-term UK residence** (§4.2), so emigrants may remain within IHT for up to 10 years (real, from 6 April 2025) — signpost professional advice. Servicing for overseas customers uses the portal and registered post; sanctions screening applies to overseas payees (§II.8).

## 12. ADVANCED TRUST DESIGN & TAXATION (Whole of Life)

### 12.1 The Aldercrest trust suite — design choices
*meta: doc=01-WOL | sec=12.1 | aud=all | type=product_rule | data=mixed*
Beyond §4.4: **Absolute (bare)** — beneficiaries fixed at outset; gift = **PET**; beneficiary can demand their share at 18 (16 in Scotland); no flexibility, no periodic charges. **Discretionary** — wide class (spouse, children, remoter issue); gift = **CLT**; relevant property regime (§12.2); maximum flexibility, letter-of-wishes guides trustees. **Flexible (post-2006 interest in possession)** — a default beneficiary with trustee power to appoint away; since 22 March 2006 lifetime IIP trusts are **also relevant property** (taxed like discretionary) — a common misconception trap. **Survivor's discretionary** — joint-life: survivor benefits if surviving 30 days, else the class. **Business trust + cross-option** — §12.4.

### 12.2 IHT mechanics in depth — CLT/PET interaction, 14-year shadow, periodic/exit charges
*meta: doc=01-WOL | sec=12.2 | aud=all | type=tax_rule | data=real*
**Order matters:** a CLT uses the NRB for 7 years; make CLTs **before** PETs. **14-year shadow:** if a PET fails (death within 7 years), CLTs made in the 7 years **before that PET** are counted when taxing it — so gifts up to 14 years back can affect the bill. **Periodic (10-year) charge — full method:** notional transfer = relevant property − available NRB; lifetime rate 20% on the excess; **effective rate** = tax ÷ total relevant property; **actual rate = 30% × effective rate** (max 6%). *Worked:* property £425,000, full NRB £325,000 → 20% × £100,000 = £20,000; effective 4.706%; actual 1.412%; **charge = £425,000 × 1.412% ≈ £6,000**. **Exit charge:** actual-rate style charge pro-rated by **complete quarters** since the last 10-year anniversary (÷40). Policy valuation at these points: higher of open-market value and premiums paid (§4.3) — low for a healthy life, potentially large if the life assured is in severe ill-health at an anniversary (a genuine nuance trustees miss).

### 12.3 Trust Registration Service (TRS) — the protection-policy exclusion
*meta: doc=01-WOL | sec=12.3 | aud=all | type=legal | data=real*
UK express trusts must generally register on HMRC's **TRS**. **Key exclusion (MLR 2017 Sch 3A):** a trust holding only a **life policy that pays out solely on death, terminal/critical illness or disability** is **excluded while the policy is held** — so a pure-protection Lifelong Protection trust normally need not register. **The exclusion ends at claim:** if trustees hold the proceeds **beyond 2 years from death**, the trust must register (90-day window). Unit-linked plans with surrender value do **not** qualify for the exclusion → registrable. Back office asks for the **TRS URN / proof of registration** where a trust is registrable (§II.6.8) — a real MLR obligation on Aldercrest as a "relevant person".

### 12.4 Business protection — own-life-in-business-trust + cross-option
*meta: doc=01-WOL | sec=12.4 | aud=all | type=product_rule | data=real (structure) / fictional (terms)*
Shareholder protection: each owner takes an **own-life** Lifelong Protection policy written in a **business trust** for co-owners; a separate **double-option (cross-option) agreement** gives the estate a put and the survivors a call, exercisable after death. Why options, not a binding buy-sell: a **binding contract for sale destroys Business Relief** (the shares would be a contract-for-sale asset), while cross-options preserve it. Premium equalisation between shareholders avoids transfer-of-value issues. Claims: trustees receive proceeds; survivors buy shares under the option.

### 12.5 Trustee duties, powers and payments
*meta: doc=01-WOL | sec=12.5 | aud=all | type=legal | data=real*
Trustees act **unanimously** unless the deed says otherwise; must act within the deed, in beneficiaries' interests, taking proper advice. Statutory powers: **s.31 Trustee Act 1925** (income for a minor's maintenance; accumulation) and **s.32** (advancement of capital — up to the **whole** presumptive share for post-Oct-2014 trusts). Payments to **minors**: hold until 18, or pay a parent/guardian for the minor's benefit with receipts documented. **Bankrupt beneficiary** with an absolute interest: the trustee in bankruptcy may claim — refer to Legal. Letter of wishes is guidance, not binding.

---

# PART II — OPERATIONS, SERVICING & CLAIMS (Lifelong Protection)
*meta: doc=01-WOL | sec=II.0 | aud=all | type=overview | data=mixed*

> Product-tailored operational layer; the cross-product master is **Document 5**. Aldercrest procedures/thresholds are fictional; all legal/regulatory rules are real (sources §II.16).

## II.1 RAG mapping and audience layers
*meta: doc=01-WOL | sec=II.1 | aud=all | type=routing | data=fictional*
Identify **caller type** (§II.2) → enforce **identity/authority gates** (§II.3, §II.5) *before* disclosure/change → route to layer **(a) customer / (b) back office / (c) ops**. For WoL, "money out" is usually a **claim** (§II.9). References: policy `LP-`+8 digits; interaction `CN-`+10; case `CW-`+9; complaint `CMP-`+8; claim `CLM-`+8.

## II.2 Inbound contact handling — who can contact us
*meta: doc=01-WOL | sec=II.2 | aud=back_office | type=procedure | data=mixed*
Channels: phone, secure portal, email (unsecured — no outbound personal data unless encrypted), post (scanned in 1 business day), adviser portal. Flow: capture (`CN-`) → classify → verify → triage → risk-screen (vulnerability/fraud/sanctions) → act or raise `CW-` → log.
Caller types & capture: **policyholder/life assured** (name, `LP-`, DOB, address, request); **adviser (LOA)** (firm, FCA FRN, adviser, scope); **LPA/EPA attorney** (donor/attorney, OPG ref); **CoP deputy** (order ref); **executor/PR** (deceased + representative, grant status); **trustee** (trust deed, identities); **helper for a vulnerable customer** (consent, relationship); **regulators/legal** (body, officer, legal basis, information sought → §II.10, never front-line disclosure). Verify identity before disclosing anything (UK GDPR Art 5(1)(f)); pre-verification give only generic non-personal information.

## II.3 Identity verification & authentication (SV/EV)
*meta: doc=01-WOL | sec=II.3 | aud=back_office | type=procedure | data=mixed*
**Principle (real):** ICO right-of-access guidance — be satisfied of identity before disclosing personal data; also fraud prevention.
**SV** — three of four: `LP-` number; name + DOB; registered address (or last-4 of the collection account); memorable-data item.
**EV** — SV **plus** OTP to the **registered** contact (never a newly supplied one) **plus** one further check (call-back / documentary evidence / knowledge-based questions). Required for: bank/DD changes; unit-linked surrenders above the front-office band; address change followed within 30 days by a bank change; beneficiary/trust/trustee changes on high-value policies.
**Step-up triggers:** change-detail-then-transact; failed SV with "corrections"; urgency to a new payee; detail mismatch; contact soon after a password/address change.
**On failure:** disclose nothing (don't confirm the policy exists); offer registered-address/portal route; log; refer suspected impersonation to Financial Crime without tipping off.

## II.4 Data protection & security in every interaction

### II.4.1 Framework and lawful bases
*meta: doc=01-WOL | sec=II.4.1 | aud=back_office | type=legal | data=real*
Aldercrest is a **data controller** under **UK GDPR/DPA 2018** (ICO-regulated; **Data (Use and Access) Act 2025** commencing 2025–26 — follow current ICO guidance). Bases: **contract** (administration), **legal obligation** (AML, complaints, retention), **legitimate interests** (fraud prevention), **consent** (marketing only, freely revocable).

### II.4.2 Special-category health data
*meta: doc=01-WOL | sec=II.4.2 | aud=back_office | type=legal | data=real*
Health data is core to WoL at underwriting, increments, waiver, terminal-illness and death claims (Art 9). Conditions: **explicit consent** (underwriting) and **legal claims (Art 9(2)(f))** (claims). Strict minimisation, restricted access, appropriate policy document where a DPA 2018 Sch 1 condition applies.

### II.4.3 Minimisation, sharing and secure handling
*meta: doc=01-WOL | sec=II.4.3 | aud=back_office | type=procedure | data=mixed*
Only collect/disclose what the task needs (Art 5(1)(c)); disclose to third parties only within verified authority scope. Outbound personal data encrypted/secure-messaged only; post to the **registered** address; misdirection is a leading breach cause — double-check recipients (Art 32 controls).

### II.4.4 SARs, rectification, erasure
*meta: doc=01-WOL | sec=II.4.4 | aud=back_office | type=procedure | data=real*
SARs: any channel, verbal or written — log at once; respond **within one month** (extendable +2 if complex, telling the requester within month 1); clock-stop only to clarify bulk requests or verify ID; redact third-party data; usually no fee. Rectification promptly with evidence; erasure usually overridden by retention duties — explain why.

### II.4.5 Breaches — the 72-hour duty
*meta: doc=01-WOL | sec=II.4.5 | aud=back_office | type=procedure | data=real*
Log every suspected breach; DPO assesses; notify the **ICO within 72 hours** where the risk threshold is met (Art 33 — clock runs from reasonable certainty, no pause for weekends); tell individuals without undue delay if high risk (Art 34); phased reporting permitted.

### II.4.6 Retention schedule
*meta: doc=01-WOL | sec=II.4.6 | aud=back_office | type=table | data=fictional (lawful-basis anchored)*
Policy/servicing: 6 years after the policy ends. Claims: 6 years after settlement. AML/CDD: 5 years after the relationship ends (MLR 2017). Complaints: ≥3 years (DISP). DSAR logs: 3 years. Support-need flags: only as long as needed.

## II.5 Third-party authority
*meta: doc=01-WOL | sec=II.5 | aud=back_office | type=procedure | data=real*
Verify authority AND scope; otherwise refuse the instruction and explain the compliant route (no partial disclosure; log the refusal).
- **Adviser LOA:** on file/in date; FRN on the FCA Register; scope usually servicing/information — **never** receipt of proceeds or bank changes.
- **LPA (P&F):** valid only when **OPG-registered**. Verify via the "**Use a lasting power of attorney**" service (access code "V…" + reference), the **stamped paper LPA** (perforated OPG stamp on every page), or an **OPG100** search. Check not revoked; within scope; **jointly** vs **jointly and severally**. Health-and-welfare LPAs carry no financial authority.
- **EPA:** pre-Oct-2007 instrument; OPG-registered once capacity is lost; paper verification only.
- **CoP deputy:** order covers property & financial affairs and is current.
- **Executors/PRs:** **Grant of Probate** / **Letters of Administration** (England & Wales/NI); **Confirmation** in Scotland (§10). Trust-held policies: trustees claim instead.
- **Third-party mandate / one-off authority:** enforce written limits; one-off logged on `CN-` and expires immediately.

## II.6 Servicing procedures — one procedure per chunk

### II.6.1 Change of address
*meta: doc=01-WOL | sec=II.6.1 | aud=back_office | type=procedure | data=fictional*
Who: policyholder / attorney-deputy / adviser in scope. Need: SV; address validated. Steps: update; confirm to **both** old and new address; 30-day watch flag. Authority: front office. SLA: same day. Exception: +bank change/withdrawal within 30 days → EV + Financial Crime watch.

### II.6.2 Change of name
*meta: doc=01-WOL | sec=II.6.2 | aud=back_office | type=procedure | data=fictional*
Need: SV + evidence (marriage/civil-partnership certificate, deed poll, decree absolute + evidence). Back office; 3 business days.

### II.6.3 Change of bank / Direct Debit (HIGH RISK)
*meta: doc=01-WOL | sec=II.6.3 | aud=back_office | type=procedure | data=fictional*
Who: policyholder only (not adviser); attorney/deputy in scope. Need: **SV+EV**; account verification; hold before first collection; confirmation to registered contact. Back office; 2 business days. Exception: urgency/third-party account/mismatch → APP-fraud handling (§II.12).

### II.6.4 Correspondence preferences and marketing consent
*meta: doc=01-WOL | sec=II.6.4 | aud=back_office | type=procedure | data=mixed*
SV. Marketing rests on **consent** (UK GDPR + **PECR** for electronic channels — see Doc 4 A16); withdrawal as easy as giving; opt-out immediate, suppression ≤24h. Front office; same day.

### II.6.5 Premium amount/frequency change
*meta: doc=01-WOL | sec=II.6.5 | aud=back_office | type=procedure | data=fictional*
SV; confirm effect on cover/guarantees and any review impact (§3.8). Back office; 3 business days / next collection.

### II.6.6 Indexation add/remove
*meta: doc=01-WOL | sec=II.6.6 | aud=back_office | type=procedure | data=fictional*
SV; explain premium/benefit effect (Consumer Duty understanding). Back office; 3 business days.

### II.6.7 Beneficiary nomination / expression of wishes
*meta: doc=01-WOL | sec=II.6.7 | aud=back_office | type=procedure | data=fictional*
Personal right of the policyholder; an attorney generally cannot change it unless expressly authorised and in the donor's best interests → escalate. SV; signed form; trust-held policies follow the trust. Back office; 5 business days.

### II.6.8 Trust set-up / trustee change
*meta: doc=01-WOL | sec=II.6.8 | aud=back_office | type=procedure | data=fictional*
SV; executed trust deed / deed of appointment-and-retirement; ID for new trustees; Scots-law deed for Scottish settlors (§10). Senior case handler; 10 business days; escalate amended wording to legal.

### II.6.9 GIO exercise / sum-assured increment
*meta: doc=01-WOL | sec=II.6.9 | aud=back_office | type=procedure | data=fictional*
Check GIO event evidence and limits (§3.7) — if within limits, no medical evidence; otherwise route to underwriting. Authority: increases above £250,000 sum assured need senior-underwriter sign-off. SLA 5 business days from evidence.

### II.6.10 Reinstatement of a lapsed policy
*meta: doc=01-WOL | sec=II.6.10 | aud=back_office | type=procedure | data=fictional*
Within 12 months (§3.10): arrears + declaration of health (re-underwriting >6 months / large sums); new suicide-clause window. Back office; 5 business days from requirements.

### II.6.11 Assignment / assignation
*meta: doc=01-WOL | sec=II.6.11 | aud=back_office | type=procedure | data=mixed*
Verify the deed of assignment (England/Wales/NI) or **assignation with intimation** (Scotland §10); record the assignee's interest (e.g. lender). Legal check; 10 business days.

### II.6.12 Duplicate documents and vulnerability flags
*meta: doc=01-WOL | sec=II.6.12 | aud=back_office | type=procedure | data=fictional*
Duplicates: SV; registered contact/portal only; 3 business days. Vulnerability support flags: capture sensitively (special-category care §II.4.2); front office sets, ops reviews; same day.

### II.6.13 Trustee lifecycle events — death, incapacity, removal (edge cases)
*meta: doc=01-WOL | sec=II.6.13 | aud=back_office | type=procedure | data=real (law) / fictional (process)*
**Death of a trustee:** surviving trustees continue; on death of a **sole/last** trustee, their personal representatives may appoint. **Incapacity:** an LPA attorney **cannot step into the trustee role** — trusteeship is personal (only narrow land-related delegation exists); the incapable trustee is **replaced by deed** under **s.36 Trustee Act 1925**; if they hold a beneficial interest, Court of Protection consent may be needed. **Removal/retirement:** deed of removal/appointment; keep at least two trustees where the deed requires. **Unanimity:** instructions must come from **all** trustees unless the deed says otherwise. **Offshore trustee appointed:** EDD + tax-residence flags → refer. **Verification:** every incoming trustee is ID-verified; TRS proof where registrable (§12.3). Senior case handler; 10 business days.

## II.7 Putting money in — operational checks
*meta: doc=01-WOL | sec=II.7 | aud=back_office | type=procedure | data=mixed*
Increments (underwriting or GIO §3.7); indexation; unit-linked top-ups. **AML/source-of-funds (MLR 2017):** single ≥ £25,000, aggregate ≥ £50,000/12 months, or third-party/high-risk-jurisdiction source → SoF evidence; **EDD** for PEPs/high-risk. Back office 3 business days (5–10 EDD).

## II.8 Taking money out — universal controls
*meta: doc=01-WOL | sec=II.8 | aud=back_office | type=procedure | data=mixed*
Before any payment: **SV+EV**; authority + right to receive (registered account unless verified legal authority directs); **sanctions screening** of the payee against the **UK Sanctions List** — a confirmed match halts payment and is reported to **OFSI** (strict liability, not risk-based); tax flags; vulnerability and fraud checks. Unit-linked surrenders: value less charges; ≤£25,000 front-office band; SLA 5 business days after checks.

## II.9 Claims

### II.9.1 Death claim — end to end
*meta: doc=01-WOL | sec=II.9.1 | aud=back_office | type=claims | data=mixed*
1) **Notification** — anyone may notify (incl. via the **Death Notification Service / Tell Us Once**); open `CLM-`; Bereavement Team; vulnerability care; notification ≠ claim.
2) **Documents** — certified death certificate (always); estate-payable: **grant of probate / letters of administration** (E&W/NI) or **Confirmation** (Scotland §10); trust-held: trust deed + trustee IDs; claimant ID and authority.
3) **Claimant authority** — beneficiary, trustee, or PR with grant; competing claims → senior claims assessor.
4) **In-force + CIDRA review** — confirm premiums paid/not lapsed (grace rules §3.10); early-years claims reviewed under **CIDRA 2012**: duty to take reasonable care not to misrepresent; **deliberate/reckless** → avoid/refuse (retain premium where fair); **careless** → proportionate remedy. Evidence the original Q&A; Consumer Duty care throughout. Check the suicide clause window (§3.5) where applicable.
5) **Sanctions screening** before release (OFSI on a confirmed match).
6) **Payment** — trustees/beneficiaries (no probate usually needed) or the estate on the grant. IHT signpost §4.2–4.3; no tax advice.

### II.9.2 Terminal illness claim
*meta: doc=01-WOL | sec=II.9.2 | aud=back_office | type=claims | data=mixed*
Medical evidence of prognosis under 12 months (§3.4); SV; the life assured's **consent** for medical evidence (Art 9 §II.4.2); heightened vulnerability handling; payment extinguishes the death benefit.

### II.9.3 Claim timescales and authority
*meta: doc=01-WOL | sec=II.9.3 | aud=back_office | type=table | data=fictional*
Acknowledge 1 business day; requirements 3; assessment 5 from full documents; payment 5 from assessment. Authority: handler ≤£50,000; team manager £50,000–£250,000; **dual authorisation** >£250,000; Head of Claims >£1,000,000; declined/non-disclosure or disputed → senior claims + compliance regardless of value.

## II.10 Regulators and government/legal third parties
*meta: doc=01-WOL | sec=II.10 | aud=back_office | type=legal | data=real*
No front-line disclosure to FCA/HMRC/courts/police — capture, verify the requester, route (DPO / MLRO / Tax / Legal). Basis: **DPA 2018 Sch 2 para 2 crime-and-taxation exemption** — only **to the extent** compliance would prejudice crime prevention/detection or tax; case-by-case; necessary and proportionate; court orders compel. **No tipping off** where a SAR is contemplated (POCA s.333A).

## II.11 Complaints (DISP)
*meta: doc=01-WOL | sec=II.11 | aud=back_office | type=procedure | data=real*
Log every complaint (`CMP-`) with root cause. Summary resolution by day 3 (DISP 1.5); **final response by 8 weeks** (DISP 1.6) else written explanation + FOS rights; **FOS referral within 6 months** of the final response (DISP 2.8.2R) — the letter must say so. MI to ops; retain ≥3 years. Review letters (§3.8) and declined claims are the main WoL complaint drivers.

## II.12 Vulnerable customers & financial crime
*meta: doc=01-WOL | sec=II.12 | aud=back_office | type=procedure | data=mixed*
**Vulnerability (FG21/1 + Consumer Duty):** four drivers (health, life events, resilience, capability) — bereavement/terminal illness make WoL contacts frequently vulnerable; record support needs (not labels), minimise; reasonable adjustments; authorised helpers get the **same support** (PRIN 2A.6.5R); suspected financial abuse → pause and escalate. **Fraud:** impersonation and APP red flags (urgency, third-party account, address-then-bank). **Sanctions:** freeze + OFSI on confirmed match. **AML (POCA):** internal SAR to MLRO; DAML where needed (7-working-day notice; 31-day moratorium, court-extendable to 186 days); no tipping off.

## II.13 Authority levels matrix (atomic table)
*meta: doc=01-WOL | sec=II.13 | aud=back_office | type=table | data=fictional*

| Transaction | Front office | Back office | Team manager | Senior manager | Dual auth |
|---|---|---|---|---|---|
| Disclose after SV | ✅ | ✅ | — | — | — |
| Address / preferences | ✅ | ✅ | — | — | — |
| Name (evidence) | — | ✅ | — | — | — |
| Bank/DD (EV) | — | ✅ | first payment | — | — |
| Premium change | — | ✅ | — | — | — |
| Beneficiary / trust / trustee | — | ✅ | senior case handler | — | — |
| Increment / GIO | — | ✅ | — | >£250k SA senior UW | — |
| Unit-linked surrender >£100k | — | prepares | — | approves | ✅ >£250k |
| Death claim ≤£50k | — | ✅ | — | — | — |
| Death claim £50k–£250k | — | prepares | approves | — | — |
| Death claim >£250k | — | prepares | — | approves | ✅ |
| Death claim >£1m | — | prepares | — | Head of Claims | ✅ |
| Declined/non-disclosure claim | — | prepares | — | claims + compliance | — |
| Regulator/police disclosure | — | — | — | DPO/MLRO/Legal | — |

Row records (atomic): `authority: death_claim ≤50000 → back_office` · `authority: death_claim 50000–250000 → team_manager` · `authority: death_claim >250000 → senior_manager + dual` · `authority: death_claim >1000000 → head_of_claims + dual` · `authority: bank_change → back_office(EV) + manager_first_payment` · `authority: increment_SA >250000 → senior_underwriter`.

## II.14 SLA table (atomic)
*meta: doc=01-WOL | sec=II.14 | aud=ops | type=table | data=fictional*

| Transaction | SLA |
|---|---|
| Address / preferences / opt-out | Same day (suppression ≤24h) |
| Name change | 3 business days |
| Bank/DD change | 2 business days (+hold) |
| Premium change / indexation | 3 business days |
| Beneficiary / EoW | 5 business days |
| Trust / trustee / assignment | 10 business days |
| GIO / increment | 5 business days |
| Reinstatement | 5 business days |
| Unit-linked surrender | 5 business days |
| DSAR | 1 month (ext. to 3) |
| Breach → ICO | ≤72 hours (where reportable) |
| Complaint summary / final | Day 3 / 8 weeks |
| Death claim ack / reqs / assess / pay | 1 / 3 / 5 / 5 business days |

## II.15 Ops / oversight layer
*meta: doc=01-WOL | sec=II.15 | aud=ops | type=ops | data=mixed*
Queues by type/age/SLA; KPIs — SLA attainment, verification-failure rate, claim cycle time, review-letter complaint rate, upheld rate, DSAR on-time, breach count, sanctions hits; risk-based QA (bank changes, surrenders, claims, vulnerability) checking gates, minimisation, Consumer Duty outcomes, records (**SYSC 9**). Reporting: FCA complaints return (DISP 1.10; consolidated return first period **1 Jan–30 Jun 2027**, PS25/19) and publication (DISP 1.10A, 500+); ICO 72-hour breaches; OFSI/NCA. **FSCS: long-term insurance 100%, no cap.** AI monitoring: routing/gate accuracy; any AI disclosure error = potential data breach.

## II.16 Sources (real URLs — reference-only chunk)
*meta: doc=01-WOL | sec=II.16 | aud=all | type=sources | data=real*
- ICO right of access — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/right-of-access/what-should-we-consider-when-responding-to-a-request/
- ICO time limits — https://ico.org.uk/for-the-public/time-limits-for-responding-to-data-protection-rights-requests/
- ICO special category data — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/special-category-data/what-are-the-rules-on-special-category-data/
- ICO breaches (72h) — https://ico.org.uk/for-organisations/report-a-breach/personal-data-breach/personal-data-breaches-a-guide/
- ICO exemptions — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/exemptions/a-guide-to-the-data-protection-exemptions/
- UK GDPR Art 9 — https://www.legislation.gov.uk/eur/2016/679/article/9
- DPA 2018 Sch 2 — https://www.legislation.gov.uk/ukpga/2018/12/schedule/2/part/1/crossheading/crime-and-taxation-general
- CIDRA 2012 — https://www.legislation.gov.uk/ukpga/2012/6/contents
- FCA DISP 1.6 — https://handbook.fca.org.uk/handbook/disp1/disp1s6
- FCA DISP 2.8 — https://handbook.fca.org.uk/handbook/disp2/disp2s8
- FCA PS25/19 — https://www.fca.org.uk/publications/consultation-papers/ps25-19-improving-complaints-reporting-process
- FCA FG21/1 — https://www.fca.org.uk/publications/finalised-guidance/guidance-firms-fair-treatment-vulnerable-customers
- FCA SYSC 9 — https://handbook.fca.org.uk/handbook/sysc9/sysc9s1
- OPG100 — https://www.gov.uk/government/publications/find-out-if-someone-has-a-registered-attorney-or-deputy
- Use an LPA — https://www.gov.uk/use-lasting-power-of-attorney
- Tell Us Once — https://www.gov.uk/after-a-death/organisations-you-need-to-contact-and-tell-us-once
- Death Notification Service — https://www.deathnotificationservice.co.uk/
- Scottish Confirmation — https://www.mygov.scot/confirmation
- IHT (gov.uk) — https://www.gov.uk/inheritance-tax
- FOS CIDRA guidance — https://www.financial-ombudsman.org.uk/businesses/complaints-deal/insurance/misrep-and-non-disclosure
- OFSI guidance — https://www.gov.uk/government/publications/financial-sanctions-general-guidance/uk-financial-sanctions-general-guidance
- NCA SARs — https://www.nationalcrimeagency.gov.uk/what-we-do/crime-threats/money-laundering-and-illicit-finance/suspicious-activity-reports
- FSCS — https://www.fscs.org.uk/what-we-cover/

---

# PART III — RAG ASSETS (Lifelong Protection)

## III.1 Glossary
*meta: doc=01-WOL | sec=III.1 | aud=all | type=glossary | data=mixed*
**Sum assured** — the guaranteed lump sum payable on death. **Life assured** — the person whose death triggers payment. **Pure protection** — no surrender value; ICOBS applies. **Unit-linked** — premiums buy fund units; cover cost deducted monthly. **Reviewable premium** — premium re-tested at set anniversaries (§3.8). **GIO** — guaranteed insurability option (§3.7). **Waiver of premium** — rider paying premiums during incapacity (§3.6). **Suicide clause** — 12-month restriction (§3.5). **CLT** — chargeable lifetime transfer into a discretionary trust. **Relevant property regime** — 10-yearly/exit IHT charges on discretionary trusts. **NRB/RNRB** — £325,000 / up to £175,000 IHT bands. **CIDRA** — consumer misrepresentation law used in claim reviews. **Confirmation** — Scottish equivalent of probate. **Assignation** — Scottish transfer of a policy. **Grace period** — 30 days' cover after a missed premium. **PET** — potentially exempt transfer (bare-trust gift).

## III.2 FAQ — customer layer
*meta: doc=01-WOL | sec=III.2 | aud=customer | type=faq | data=mixed*
**Q: Will my family pay tax on the payout?** No income tax or CGT; IHT can apply if the policy isn't in trust and your estate exceeds the allowances (§4.2). Putting it in trust usually avoids this (§4.3).
**Q: I missed a premium — am I still covered?** Yes for 30 days (grace); a claim in that window is paid less the missed premium (§3.10).
**Q: Can I increase my cover after having a baby without new medicals?** Yes if your plan has the GIO — within 90 days, up to the limits (§3.7).
**Q: What happens at my premium review?** We test whether current premiums still support your cover; you can pay more, keep premiums and reduce cover, or let the plan run down (§3.8).
**Q: My mother has dementia — can I manage her policy?** Yes with a registered property-and-financial-affairs LPA; we verify it with the OPG first (§II.5).
**Q: How fast are death claims paid?** Typically within 5 working days of receiving all requirements (§II.9.3); trust-held policies avoid waiting for probate (§II.9.1).

## III.3 FAQ — back office / ops layer
*meta: doc=01-WOL | sec=III.3 | aud=back_office | type=faq | data=mixed*
**Q: Claim in month 9 of the policy — what applies?** Suicide-clause check (§3.5) and CIDRA early-years review (§II.9.1 step 4); declined outcomes need claims+compliance sign-off (§II.9.3).
**Q: Attorney wants to change the beneficiary — allowed?** Generally no unless the LPA expressly permits and it's in the donor's best interests — escalate (§II.6.7, §II.5).
**Q: Scottish policyholder died — what replaces probate?** Confirmation from the sheriff court; accept the Certificate of Confirmation (§10, §II.9.1).
**Q: Payee has a possible sanctions match — proceed?** No. Freeze, do not deal, report to OFSI; this is strict liability (§II.8, §II.12).
**Q: Which claims need dual authorisation?** Above £250,000 (two senior managers); above £1m add Head of Claims (§II.9.3, §II.13).

## III.4 Specimen policy record (SYNTHETIC — a reserved number, never a customer)
*meta: doc=01-WOL | sec=III.4 | aud=all | type=sample_record | data=fictional*
`policy_no: LP-20419876` · `product: Lifelong Protection (reviewable, unit-linked)` · `status: in force` · `holder: Theta Meridian 12` · `dob: 1954-02-11` · `address: 14 Lattice Way, Demoford (registered)` · `lives_assured: single life` · `sum_assured: £400,000` · `fund_value: £46,210` · `premium: £212.40/month, DD, next collection 01-08-2026` · `start_date: 2016-05-01` · `next_review: 2026-05-01 (year-10, in progress)` · `trust: discretionary, executed 2016-05-01` · `trustees: Theta Meridian 12; Delta Meridian 41 (ID verified)` · `GIO: not included` · `waiver: not included` · `indexation: declined 2024, 2025` · `adviser_LOA: Fairholm Financial Ltd, FRN 512345 (fictional), scope=servicing+information, expires 2027-03` · `bank_last4: 4471` · `vulnerability_flag: none` · `recent_transactions: 2026-06-14 address confirmed; 2026-05-02 review letter issued` · `open_cases: CW-300218754 (year-10 review response awaited)`.
**This is a specimen, not a customer.** It is a worked illustration of a completed Lifelong Protection record, printed here so procedures can be taught against a filled-in example. Its policy number comes from the block reserved for specimens — eight digits at or above 20,100,000 — which the book cannot issue to anybody, so no specimen can ever collide with a real policy. A live customer's record would never appear in a product manual; this one is safe to print precisely because there is nobody behind it.

## III.5 Worked case walkthrough — death claim on a trust policy
*meta: doc=01-WOL | sec=III.5 | aud=all | type=case_study | data=fictional (rules real)*
Delta Meridian 41 phones: Theta (LP-20419876) has died. Front office opens `CN-`, registers the death, routes to Bereavement, flags Delta as recently bereaved (FG21/1 support). Requirements issued in 3 days: certified death certificate; because the policy is **in trust**, trustee ID — **no probate needed** (§II.9.1). Back office confirms in force (premiums paid to July 2026), start 2016 → **no early-years CIDRA review needed**; suicide window long expired (§3.5). Sanctions screen of trustee payees: clear. Value £400,000 → band £250k–£1m → **senior manager + dual authorisation** (§II.9.3). Paid to trustees in 5 business days; IHT: proceeds outside the estate (§4.3). Cross-sources used: this doc §II.9/§4 + Doc 4 (FG21/1, DISP context) + Doc 5 §9/§14.

## III.6 Cross-source reasoning map (demo questions)
*meta: doc=01-WOL | sec=III.6 | aud=all | type=routing | data=mixed*
1. "Theta's son says she lacks capacity and he wants to stop indexation" → §II.5 (LPA/OPG) + §II.6.6 + Doc 5 §5.2. 2. "Claim on a 9-month-old policy where the application omitted a heart condition" → §3.5 + §II.9.1 (CIDRA) + Doc 4 (FOS/DISP). 3. "Scottish customer wants to transfer the policy to his wife" → §10 (assignation) + §II.6.11 + §4 (IHT spouse exemption context). 4. "Trustees ask what tax the trust pays at the 10-year point" → §4.3 worked example + Doc 4 (HMRC sources). Complexity tier: LOW–MEDIUM — use for single-hop and two-hop demo queries.

## III.7 Trust stress-test case — incapacitated trustee + ill-health anniversary valuation
*meta: doc=01-WOL | sec=III.7 | aud=all | type=case_study | data=fictional (rules real)*
Theta's discretionary trust (LP-20419876, §III.4) reaches its 10-year anniversary in 2026 while Theta — settlor, life assured **and** trustee — has advanced dementia. Delta (co-trustee, LPA attorney) calls "as attorney, on behalf of both trustees" to change the trust's correspondence and appoint his wife as trustee. Correct handling chain: (1) his **LPA gives no trustee authority** — Theta must be **replaced as trustee by deed (s.36)**, with CoP considerations since she's also settlor/beneficiary-adjacent (§II.6.13, §12.5); (2) the anniversary **periodic-charge valuation** cannot use "premiums paid" complacently — the life assured is in **severe ill-health**, so open-market value approaches the sum assured (£400,000), turning an expected nil charge into a potentially five-figure one (§12.2, §4.3) → trustees signposted to professional valuation; (3) TRS check: unit-linked policy → **registrable**, URN requested (§12.3); (4) vulnerability handling for Theta throughout (§II.12). A four-way reasoning chain (authority law + trust tax + AML/TRS + vulnerability) — the hardest single-product eval in this document.

---
*End of Document 1 v2.1. Firm-wide regulation: Document 4. Cross-product master procedures, data dictionary and intent routing: Document 5. Evals, observability and change management: Document 6.*
