# DOCUMENT 2 — ONSHORE INVESTMENT BOND (PRODUCT MASTER) v2
*meta: doc=02-BOND | sec=frontmatter | aud=all | type=caveats | data=mixed*
## Aldercrest "Horizon Bond"
*meta: doc=02-BOND | sec=frontmatter-title | aud=all | type=caveats | data=mixed*

**Fictional company:** Aldercrest Life Assurance plc ("Aldercrest Life"). Not a real FCA-authorised insurer.
**Grounding:** Regulators and all tax/regulatory figures are real (2025/26), verified against sources in Document 4 and §II.16. Aldercrest charges, limits, SLAs and thresholds are fictional but realistic. Knowledge-base date: **13 July 2026.** Finance Act 2026 items are flagged "legislated, not yet in force."
**RAG formatting convention:** split on headings — every `##`/`###` is one chunk (target 500–800 tokens; ~10% overlap for long prose only). Tables and Sources are **atomic**. `meta:` schema — `doc` | `sec` | `aud` | `type` | `data` (real/fictional/mixed).
**Complexity tier for RAG demo:** MEDIUM–HIGH (multi-step tax arithmetic: 5% allowance, chargeable events, top-slicing, reliefs).

---

# PART I — PRODUCT

## 1. What the product is and its purpose
*meta: doc=02-BOND | sec=1 | aud=all | type=overview | data=mixed*
An onshore investment bond is a **single-premium, non-qualifying whole of life insurance policy** whose primary purpose is **investment**. "Onshore" = issued by a UK life insurer: the insurer pays tax within its life fund and the policyholder is treated as having a **20% basic-rate tax credit**. It is designated investment business under **COBS** and carries a small life-cover element (typically 101% of value).

## 2. Target market and eligibility
*meta: doc=02-BOND | sec=2 | aud=all | type=eligibility | data=fictional*
Target: investors (often higher/additional-rate taxpayers, trustees, or those wanting tax-deferred withdrawals) seeking a **5+ year** lump-sum investment with tax deferral and estate-planning flexibility. Not for those needing full instant access without tax planning or who haven't used ISA/pension allowances. Entry age 18–89; individuals, joint, trustees, companies. Minimum £10,000; top-ups from £1,000. Lives assured up to two (last-survivor common). UK resident at application (Scotland/NI notes §11; non-residence tax §4.10).

## 3. Product rules, features, charges

### 3.1 Segmentation
*meta: doc=02-BOND | sec=3.1 | aud=all | type=product_rule | data=fictional*
Issued as identical mini-policies ("segments"; Aldercrest default **1,000**), enabling tax-efficient surrender of whole segments (§4.9).

### 3.2 Fund options
*meta: doc=02-BOND | sec=3.2 | aud=all | type=product_rule | data=fictional*
Risk-rated multi-asset/managed funds, a with-profits fund (§3.7), index trackers, insured funds across equities/bonds/property/cash; switches allowed (§II.6.5).

### 3.3 Charges
*meta: doc=02-BOND | sec=3.3 | aud=all | type=product_rule | data=fictional*
Product/administration 0.30% p.a.; fund AMCs 0.10%–1.00%; possible early-surrender charge in years 1–5 on some funds; no initial charge on the standard proposition.

### 3.4 Death benefit and surrender values
*meta: doc=02-BOND | sec=3.4 | aud=all | type=product_rule | data=fictional*
Death benefit typically **101%** of bond value on death of the last life assured. Full/partial surrender available; value = bid value of units less applicable charges.

### 3.5 Unit pricing and valuation
*meta: doc=02-BOND | sec=3.5 | aud=all | type=product_rule | data=fictional*
Single swinging price per fund; **daily valuation point 12:00**; **forward pricing** (instructions received before the point deal at that day's price; after it, the next day's). A **dilution adjustment** may apply on large flows to protect remaining investors. Instructions are placed, not priced, on receipt (§II.6.5).

### 3.6 With-profits, bonuses and MVR
*meta: doc=02-BOND | sec=3.6 | aud=all | type=product_rule | data=mixed*
The with-profits fund smooths returns via an **annual (reversionary) bonus** (added yearly, normally cannot be removed) and a possible **final (terminal) bonus** at exit. A **Market Value Reduction (MVR)** may reduce surrender/switch proceeds when markets have fallen, to protect remaining policyholders — **never applied on death** or at Aldercrest's fictional **no-MVR guarantee point (10th anniversary)**. Governance: FCA **COBS 20** (fair treatment, With-Profits Actuary, published **PPFM**) — see Document 4 B7.

### 3.7 Permitted assets and the Personal Portfolio Bond warning
*meta: doc=02-BOND | sec=3.7 | aud=all | type=tax_rule | data=real*
The Horizon Bond invests only in **permitted, insurer-pooled funds**, so it is **not** a **Personal Portfolio Bond (PPB)**. Real rule (ITTOIA 2005 ss.515–526): a bond whose benefits can be determined by personal/non-permitted property suffers a punitive **annual deemed gain of 15%** of the premium plus cumulative previous deemed gains, taxed yearly. Operational rule: never permit fund links outside the permitted list; any request → refuse and explain (§II.6.5).

## 4. Tax treatment (real UK rules)

### 4.1 Fund taxation and the 20% credit
*meta: doc=02-BOND | sec=4.1 | aud=all | type=tax_rule | data=real*
The insurer pays corporation tax within the life fund; the investor holds a **non-reclaimable 20% basic-rate credit**. No personal CGT; no further basic-rate income tax on gains.

### 4.2 The 5% tax-deferred withdrawal allowance
*meta: doc=02-BOND | sec=4.2 | aud=all | type=tax_rule | data=real*
Withdraw up to **5% of the amount invested per policy year** with no immediate tax; **cumulative** (unused carries forward) up to 100% of the amount invested. A **deferral, not an exemption** — withdrawals re-enter the final gain calculation. Each top-up starts its own 5% clock (§7).

### 4.3 Chargeable events
*meta: doc=02-BOND | sec=4.3 | aud=all | type=tax_rule | data=real*
Tax is assessed on: full surrender; surrender of whole segments; a partial withdrawal exceeding the cumulative 5% allowance (tested at policy-year end); death of the last life assured; **assignment for money's worth**; maturity. Gains are **savings income** in the event year. Aldercrest issues a **chargeable event certificate** and reports to HMRC where thresholds are met.

### 4.4 Top-slicing relief
*meta: doc=02-BOND | sec=4.4 | aud=all | type=tax_rule | data=real*
Relief for a multi-year gain taxed in one year: slice = gain ÷ complete policy years (or years since the last excess event for excess gains). Onshore effect: basic/nil-rate slices → no further tax; higher-rate slices → **20%** (40%−20% credit); additional-rate → **25%** (45%−20%). The **full gain** (not the slice) still counts for the personal-allowance taper (£100,000–£125,140) and the personal savings allowance.

### 4.5 Income tax bands (2025/26)
*meta: doc=02-BOND | sec=4.5 | aud=all | type=tax_rule | data=real*
Personal allowance **£12,570**; basic **20%** to £50,270; higher **40%** to £125,140; additional **45%** above. Frozen to 5 April 2031. **Scottish taxpayers:** bond gains are **savings income**, so **UK-wide savings rates apply** even to Scottish residents (Scottish rates cover non-savings income only) — a key cross-source nuance (§11).

### 4.6 Legislated future change — savings rates from 6 April 2027
*meta: doc=02-BOND | sec=4.6 | aud=all | type=tax_rule | data=real (not yet in force)*
**Finance Act 2026** (Royal Assent 18 March 2026; Autumn Budget 26 November 2025) raises savings-income rates from **6 April 2027** to **22% / 42% / 47%**; the onshore notional credit rises to **22%**. Applies from 2027/28 — flag, don't apply, at the current knowledge date.

### 4.7 Assignment
*meta: doc=02-BOND | sec=4.7 | aud=all | type=tax_rule | data=real*
Assignment **by way of gift** is not a chargeable event and moves future gains to the assignee (often a lower-rate taxpayer or adult child before surrender). Assignment **for money's worth** IS a chargeable event (§4.3). Scotland: effected by **assignation with intimation** (§11).

### 4.8 Trustee-held bonds
*meta: doc=02-BOND | sec=4.8 | aud=all | type=tax_rule | data=real*
Popular trustee asset (no income to report annually). **Trustees cannot use top-slicing relief**; gains on trustee-held bonds are typically taxed at the **45% trust rate less the 20% credit = 25%** (where the settlor is dead/non-UK; settlor-interested trusts assess the settlor). Bare trusts assess the beneficiary.

### 4.9 Part surrender vs segment surrender vs part assignment — and the s.507A safety valve
*meta: doc=02-BOND | sec=4.9 | aud=all | type=tax_rule | data=real*
Three routes to the same cash, very different tax: (a) **partial withdrawal across all segments** — taxed only on the excess over the cumulative 5% allowance, but a large withdrawal early on can create an **artificially huge gain** unrelated to real growth; (b) **full surrender of whole segments** — gain per segment = proceeds − premium share, usually tracking real growth; (c) **part assignment** — can transfer segments instead of encashing. The AI must surface the comparison before processing (§II.8.2). Real safety valve: **ITTOIA s.507A** (post-*Lobler*, FA 2017) — a policyholder may apply to HMRC to have a **"wholly disproportionate"** part-surrender gain recalculated on a just-and-reasonable basis. This is remedial, not planning — get the method right first.

### 4.10 Time-apportionment relief (non-UK residence)
*meta: doc=02-BOND | sec=4.10 | aud=all | type=tax_rule | data=real*
Where the policyholder was **non-UK resident** during the policy period, the chargeable gain is reduced by the proportion of **foreign days**: gain × (UK-resident days ÷ total policy days) remains taxable (ITTOIA s.528). Claimed through Self Assessment; Aldercrest certificates show the full gain — signpost the relief, don't apply it.

### 4.11 Deficiency relief
*meta: doc=02-BOND | sec=4.11 | aud=all | type=tax_rule | data=real*
If final surrender shows a **deficiency** (earlier excess-withdrawal gains exceeded the true overall gain), **deficiency relief** can reduce tax on income otherwise taxable at the higher rate, up to the earlier gains. Higher-rate taxpayers only benefit; claimed via Self Assessment; signpost only.

## 5. WORKED EXAMPLE — chargeable event gain with top-slicing
*meta: doc=02-BOND | sec=5 | aud=all | type=worked_example | data=real (figures fictional)*
£100,000 invested (1,000 segments). After **10 complete years**, full surrender for £150,000, no withdrawals. **Gain £50,000.** Other income £40,000 (£10,270 of basic band left). **Slice £5,000/yr** keeps the taxpayer in basic rate → top-slicing + 20% credit → **no further income tax**. Always run the full HMRC method: the whole £50,000 still counts for the PSA and personal-allowance taper. *Contrast (why §4.9 matters):* the same customer taking a £50,000 **partial withdrawal across all segments** in year 2 would trigger tax on £40,000 of "excess" (£50,000 − 2×5% allowance) regardless of real growth — segment surrender would have produced a far smaller gain.

## 6. HOW TO INVEST — new business journey
*meta: doc=02-BOND | sec=6 | aud=all | type=journey | data=mixed*
1. Advised vs non-advised under COBS — suitability **COBS 9A** / appropriateness **COBS 10A**. 2. Application: investor details, amount, funds, lives assured, trust. 3. KYC/AML: identity + **source of funds/wealth** for larger premiums (MLR 2017); EDD for PEPs/high-risk countries. 4. Money in: cleared funds; units at the next valuation point (§3.5). 5. Disclosure: **KID** / Key Features + illustration (PRIIPs→**CCI** transition, Doc 4 B3). 6. Cancellation: **30 calendar days** (COBS 15); a **market-loss (shortfall) adjustment** may reduce the refund on a single premium if unit values fell before cancellation.

## 7. Putting more money in (summary)
*meta: doc=02-BOND | sec=7 | aud=customer | type=overview | data=fictional*
Top-ups from £1,000; each starts its **own 5% allowance clock** and issues **new segments**. Checks: AML/source of funds for large amounts; suitability if advised. Operational detail **§II.7**.

## 8. Taking money out (summary)
*meta: doc=02-BOND | sec=8 | aud=customer | type=overview | data=mixed*
Regular/partial withdrawals (within or above the 5% allowance), segment surrender, full surrender, death claim (101%). Route choice matters for tax (§4.9); certificates issued on gains. Operational detail **§II.8**; timescales: withdrawals 5 business days, full surrender 10.

## 9(a). CUSTOMER-FACING INFORMATION
*meta: doc=02-BOND | sec=9a | aud=customer | type=customer_info | data=mixed*
Plain language on the 5% allowance, tax deferral, and that a chargeable event can create a tax bill **even where the bond has not grown** (§4.9). You can ask for: withdrawals, switches, valuations, chargeable event certificates. Rights: complaints → FOS within 6 months of the final response; **FSCS 100%, no cap** (long-term insurance).

## 9(b). BACK OFFICE INFORMATION (summary — detail in Part II)
*meta: doc=02-BOND | sec=9b | aud=back_office | type=overview | data=fictional*
Withdrawal method check (segment vs partial) against the 5% allowance; chargeable event certificates + HMRC reporting; switch execution at valuation points; top-up AML; authority bands; exceptions — disproportionate-gain warnings, assignments (legal check), trustee instructions (verify all trustees).

## 9(c). OPS/OVERSIGHT INFORMATION (summary — detail in Part II)
*meta: doc=02-BOND | sec=9c | aud=ops | type=overview | data=fictional*
KPIs on withdrawals/switches/surrenders and **certificate accuracy/timeliness**; QA on chargeable-event calculations; PROD 4 / price-and-value; DISP escalation; HMRC reporting touchpoints.

## 10. Trust and estate interaction (signpost)
*meta: doc=02-BOND | sec=10 | aud=all | type=tax_rule | data=real*
Bonds in trust follow the WoL trust logic (Doc 1 §4.3): discretionary = relevant property regime; the bond's value at 10-year points is its surrender value. On death of the last life assured, trust-held proceeds pay to trustees (no probate); estate-held bonds need the grant/Confirmation (§11).

## 11. Scotland and Northern Ireland notes
*meta: doc=02-BOND | sec=11 | aud=all | type=legal | data=real*
**Scotland:** transfers by **assignation with intimation**; death claims paid to executors on **Confirmation** (certificate accepted); trust deeds in Scots-law form; **bond gains are savings income → UK rates apply even to Scottish taxpayers** (§4.5). **NI:** mirrors England & Wales; grants from the NI Probate Office.

## 12. ESTATE-PLANNING TRUST WRAPPERS FOR BONDS

### 12.1 Gift trust (bond)
*meta: doc=02-BOND | sec=12.1 | aud=all | type=product_rule | data=mixed*
The settlor gifts the bond (or cash to buy it) into trust outright. Discretionary version = **CLT** (relevant property regime, Doc 1 §12.2); bare version = **PET**. Settlor is **excluded from benefit** (else gift with reservation). Simplest wrapper; full value leaves the estate after 7 years.

### 12.2 Loan trust (access without gifting)
*meta: doc=02-BOND | sec=12.2 | aud=all | type=tax_rule | data=real (structure) / fictional (terms)*
The settlor **lends** (interest-free, repayable on demand) to trustees, who invest in a Horizon Bond. **No transfer of value** → no 7-year clock. **Growth accrues outside** the estate; the **outstanding loan remains inside** it. Repayments are typically funded by the bond's 5% withdrawals paid to the settlor (spend them — retained repayments re-enter the estate). The settlor may **waive** part/all of the loan later by deed — the waiver is a CLT/PET **at that date**. Death: the outstanding loan is an estate asset the trustees must repay/settle.

### 12.3 Discounted gift trust (DGT)
*meta: doc=02-BOND | sec=12.3 | aud=all | type=tax_rule | data=real (structure) / fictional (terms)*
The settlor gifts a bond into trust but **carves out** a right to fixed regular payments (e.g. 5% p.a.) for life. The IHT transfer = amount invested **minus the actuarial value ("discount") of the retained payments** — the discount depends on age/health, so **medical underwriting** evidences it. The discounted portion leaves the estate **immediately**; only the discounted gift is tested on death within 7 years. Discretionary DGT = CLT of the discounted amount; bare DGT = PET. **10-year valuations** reflect the settlor's retained rights (lower while the settlor lives). Payments **cannot be varied** once set — unsuitable if flexibility is needed. Aldercrest requires the DGT underwriting pack before issue.

### 12.4 Chargeable-gain attribution ladder for trust-held bonds
*meta: doc=02-BOND | sec=12.4 | aud=all | type=tax_rule | data=real*
Who pays tax on a trustee-held bond's chargeable event gain: **(1) Settlor** — if UK-resident and alive in the tax year of the event (including the year of death): gain assessed on the settlor, **with top-slicing**. **(2) UK trustees** — if the settlor died in an earlier tax year or is non-UK resident: **45% trust rate less the 20% credit = 25%**, **no top-slicing** (§4.8). **(3) UK beneficiaries** — if the trustees are non-UK resident: beneficiaries can be taxed on benefits received. **Bare trusts:** the beneficiary is taxed; where a **parent** settled for their **minor** child, parental-settlement rules attribute the gain to the parent. This ladder is the single most-missed rule in trustee servicing — the AI must identify **who** is assessable before quoting any rate.

### 12.5 Appointing/assigning out of trust to a beneficiary
*meta: doc=02-BOND | sec=12.5 | aud=all | type=tax_rule | data=real*
Trustees may **appoint/assign segments to an adult beneficiary** (deed of appointment/assignment — not for money's worth, so **not a chargeable event**). The beneficiary then surrenders using **their own** allowances, rates and **top-slicing** — routinely far better than a 25% trustee charge (§12.4). Operational: verify the deed, beneficiary ID, and (Scotland) intimation (§11); IHT exit-charge check on the appointment (Doc 1 §12.2).

### 12.6 TRS — bond trusts are registrable
*meta: doc=02-BOND | sec=12.6 | aud=all | type=legal | data=real*
Bonds have **surrender values**, so trusts holding them do **not** qualify for the protection-policy TRS exclusion (contrast Doc 1 §12.3): gift trusts, loan trusts and DGTs holding a Horizon Bond must **register on HMRC's TRS**, keep records current (90-day change window), and provide Aldercrest with **proof of registration (URN)** — which Aldercrest, as a relevant person, must collect and discrepancy-report where wrong.

---

# PART II — OPERATIONS, SERVICING & CLAIMS (Horizon Bond)
*meta: doc=02-BOND | sec=II.0 | aud=all | type=overview | data=mixed*

> Product-tailored operational layer; cross-product master = **Document 5**. Aldercrest specifics fictional; legal rules real (sources §II.16).

## II.1 RAG mapping and audience layers
*meta: doc=02-BOND | sec=II.1 | aud=all | type=routing | data=fictional*
Caller type (§II.2) → identity/authority gates (§II.3, §II.5) → layer (a) customer / (b) back office / (c) ops. Highest-frequency flows: **withdrawals/surrenders** (chargeable events) and **fund switches**. References: `HB-`+8; `CN-`+10; `CW-`+9; `CMP-`+8; `CLM-`+8. Segmentation (default 1,000) drives §II.8.

## II.2 Inbound contact handling — who can contact us
*meta: doc=02-BOND | sec=II.2 | aud=back_office | type=procedure | data=mixed*
Channels and master flow as Doc 1 §II.2. Caller types & capture: **bondholder** (name, `HB-`, DOB, address); **adviser (LOA)** (firm, FRN, scope — advisers commonly instruct switches/withdrawals within scope); **LPA/EPA attorney** (OPG ref); **CoP deputy** (order ref); **trustee** (deed + IDs; trustees can't top-slice §4.8); **assignee** (verified deed/assignation); **executor/PR** (grant/Confirmation status); **helper for a vulnerable customer**; **regulators/legal** → §II.10. Verify before disclosing anything.

## II.3 Identity verification & authentication (SV/EV)
*meta: doc=02-BOND | sec=II.3 | aud=back_office | type=procedure | data=mixed*
**SV** — three of four: `HB-`; name+DOB; registered address (or last-4 linked account); memorable item. **EV** — SV + OTP to registered contact + one further check; required for: bank changes; withdrawals/surrenders above the front-office band; address change then bank/withdrawal within 30 days; assignment; trust/trustee changes on high value. Step-up triggers and failure handling as Doc 1 §II.3 (disclose nothing; secure route; log; Financial Crime referral without tipping off).

## II.4 Data protection & security

### II.4.1 Framework and lawful bases
*meta: doc=02-BOND | sec=II.4.1 | aud=back_office | type=legal | data=real*
Controller under UK GDPR/DPA 2018 (ICO; DUAA 2025 commencing). Bases: contract; legal obligation (AML, **HMRC chargeable-event reporting**, complaints, retention); legitimate interests (fraud); consent (marketing only — PECR for electronic channels, Doc 4 A16).

### II.4.2 Special-category data
*meta: doc=02-BOND | sec=II.4.2 | aud=back_office | type=legal | data=real*
Bonds involve little health data (minimal underwriting); it arises incidentally (vulnerability disclosures, ill-health context) — Art 9 conditions, minimisation, restricted access.

### II.4.3 Minimisation, sharing, secure handling
*meta: doc=02-BOND | sec=II.4.3 | aud=back_office | type=procedure | data=mixed*
Disclose only within verified authority scope (an "information only" LOA ≠ surrender authority). Encrypted/secure outbound only; registered address; Art 32 controls.

### II.4.4 SARs, rectification, erasure
*meta: doc=02-BOND | sec=II.4.4 | aud=back_office | type=procedure | data=real*
One-month SAR deadline (extendable +2, reasons within month 1); clock-stop only for clarification/ID; redact third-party data; rectification with evidence; erasure usually overridden by retention duties.

### II.4.5 Breaches and retention
*meta: doc=02-BOND | sec=II.4.5 | aud=back_office | type=procedure | data=mixed*
Breach register; **ICO within 72 hours** where reportable; individuals if high risk. Retention: policy/servicing 6 years after the bond ends; AML/CDD 5 years; complaints ≥3 years; chargeable-event records kept to support HMRC reporting.

## II.5 Third-party authority
*meta: doc=02-BOND | sec=II.5 | aud=back_office | type=procedure | data=real*
As Doc 1 §II.5 plus bond-specifics: **assignee** — verify the deed of assignment (or **assignation + intimation**, Scotland §11) before recognising ownership; remember assignment for money's worth is a chargeable event (§4.3/4.7). **Trustees** — all trustees verified; instructions per the deed (unanimous unless it says otherwise). Unverifiable authority → refuse, explain, log.

## II.6 Servicing procedures — one per chunk

### II.6.1 Change of address
*meta: doc=02-BOND | sec=II.6.1 | aud=back_office | type=procedure | data=fictional*
SV; confirm to old **and** new address; 30-day watch. Front office; same day. Exception: +bank/withdrawal in 30 days → EV + FC watch.

### II.6.2 Change of name
*meta: doc=02-BOND | sec=II.6.2 | aud=back_office | type=procedure | data=fictional*
SV + evidence. Back office; 3 business days.

### II.6.3 Change of bank (HIGH RISK)
*meta: doc=02-BOND | sec=II.6.3 | aud=back_office | type=procedure | data=fictional*
Bondholder only; attorney/deputy in scope. **SV+EV**; account verification; hold before first payment; confirm to registered contact. Back office; 2 business days. Exception → APP-fraud handling (§II.12).

### II.6.4 Preferences / marketing consent
*meta: doc=02-BOND | sec=II.6.4 | aud=back_office | type=procedure | data=mixed*
SV; consent-based (UK GDPR + PECR); opt-out immediate; suppression ≤24h. Front office; same day.

### II.6.5 Fund switch (incl. permitted-asset guard)
*meta: doc=02-BOND | sec=II.6.5 | aud=back_office | type=procedure | data=mixed*
Bondholder / adviser in scope. SV; target funds on the **permitted list only** (PPB guard §3.7); note MVR if leaving with-profits off a guarantee date (§3.6). Placed ≤2 business days; priced forward at the next valuation point (§3.5).

### II.6.6 Regular-withdrawal instruction change
*meta: doc=02-BOND | sec=II.6.6 | aud=back_office | type=procedure | data=mixed*
SV; test against the cumulative **5% allowance**; warn where the new level creates an annual excess (§4.2–4.3). Back office; 3 business days.

### II.6.7 Trust set-up / trustee change
*meta: doc=02-BOND | sec=II.6.7 | aud=back_office | type=procedure | data=fictional*
SV; executed deed / appointment-and-retirement; trustee IDs; Scots-law deed where applicable. Senior case handler; 10 business days.

### II.6.8 Assignment / assignation
*meta: doc=02-BOND | sec=II.6.8 | aud=back_office | type=procedure | data=mixed*
SV; verified deed (intimation in Scotland); classify **gift vs money's worth** — the latter triggers a chargeable event and certificate (§4.3/4.7). Legal check; 10 business days.

### II.6.9 Expression of wishes / duplicates / valuations / vulnerability flags
*meta: doc=02-BOND | sec=II.6.9 | aud=back_office | type=procedure | data=fictional*
EoW: SV, signed form, 5 business days. Duplicates/valuations: SV, registered contact/portal, 3 business days. Vulnerability flags: sensitive capture, same day.

### II.6.10 Trustee transactions — operational gates
*meta: doc=02-BOND | sec=II.6.10 | aud=back_office | type=procedure | data=mixed*
Before any trustee instruction: all trustees ID-verified; instruction signed by **all** trustees (unless the deed permits otherwise); **TRS URN/proof** on file for registrable trusts (§12.6, discrepancy-report if wrong); classify the trust (gift/loan/DGT) because it changes what's allowed — **DGT retained payments cannot be varied** (§12.3); **loan-trust repayments** go to the settlor as loan repayment, not distribution (§12.2). Before a surrender: run the **attribution ladder** (§12.4) and surface the **appoint-out-first** alternative (§12.5). Trustee lifecycle events (death/incapacity/removal — attorney cannot act as trustee): apply Doc 1 §II.6.13 mechanics. Senior case handler for deeds; 10 business days.

## II.7 Putting money in — operational checks
*meta: doc=02-BOND | sec=II.7 | aud=back_office | type=procedure | data=mixed*
Top-ups = new segments + new 5% clock (§4.2). **AML/SoF (MLR 2017):** single ≥£25,000, aggregate ≥£50,000/12m, or third-party/high-risk source → SoF evidence; EDD for PEPs/high-risk. Suitability if advised. Back office 3 business days (5–10 EDD).

## II.8 Taking money out

### II.8.1 Universal controls
*meta: doc=02-BOND | sec=II.8.1 | aud=back_office | type=procedure | data=mixed*
**SV+EV**; authority + right to receive (registered account unless verified legal authority); **sanctions screening** (confirmed match → freeze + OFSI, strict liability); tax flags (no advice — signpost); vulnerability/fraud checks.

### II.8.2 Method selection and processing
*meta: doc=02-BOND | sec=II.8.2 | aud=back_office | type=procedure | data=mixed*
The AI/agent must surface the **three-route comparison** before processing: partial across all segments vs whole-segment surrender vs (part) assignment (§4.9) — and flag disproportionate-gain risk (s.507A is remedial only). Within-5% withdrawals: no immediate tax. Excess: certificate at policy-year end. Segment/full surrender: compute gain, issue certificate, note top-slicing years. SLA: withdrawals 5 business days after checks; full surrender 10. Authority bands §II.13.

## II.9 Claims — death of the last life assured
*meta: doc=02-BOND | sec=II.9 | aud=back_office | type=claims | data=mixed*
1) Notification (anyone; Tell Us Once/DNS accepted); `CLM-`; Bereavement Team; last-survivor bonds continue after a first death and pay on the **second**. 2) Documents: death certificate; estate → grant (E&W/NI) or **Confirmation** (Scotland §11); trust → deed + trustee IDs. 3) Verify claimant; disputes → senior assessor. 4) Value: typically **101%**; calculate the final **chargeable event gain** and issue the certificate (estate gains usually fall to the deceased's final return / estate — signpost). 5) Sanctions screen. 6) Pay trustees (no probate) or PRs on the grant. Timescales/authority: ack 1 / reqs 3 / assess 5 / pay 5 business days; handler ≤£50k; manager £50k–£250k; dual >£250k; Head of Claims >£1m.

## II.10 Regulators and legal third parties
*meta: doc=02-BOND | sec=II.10 | aud=back_office | type=legal | data=real*
No front-line disclosure; route to DPO/MLRO/Tax/Legal; **DPA 2018 Sch 2 para 2** crime-and-taxation exemption applied case-by-case, necessary and proportionate; court orders compel; **no tipping off** (POCA s.333A). Routine HMRC chargeable-event reporting is a Tax/Finance touchpoint, not a disclosure decision.

## II.11 Complaints (DISP)
*meta: doc=02-BOND | sec=II.11 | aud=back_office | type=procedure | data=real*
Log all (`CMP-`); summary resolution by day 3; final response by 8 weeks; FOS within 6 months of the final response (letter must say so). Bond-specific drivers: unexpected chargeable-event tax after large partial withdrawals (§4.9), MVR application (§3.6). Root cause → ops MI.

## II.12 Vulnerable customers & financial crime
*meta: doc=02-BOND | sec=II.12 | aud=back_office | type=procedure | data=mixed*
FG21/1 + Consumer Duty as Doc 1 §II.12; bond-specific abuse pattern: pressure on an older bondholder to surrender to a third-party account → **pause + escalate**. Sanctions: freeze + OFSI. AML: internal SAR → MLRO; DAML (7 working days; 31-day moratorium, extendable to 186); no tipping off; SoF scrutiny is central to large single-premium business.

## II.13 Authority levels matrix (atomic)
*meta: doc=02-BOND | sec=II.13 | aud=back_office | type=table | data=fictional*

| Transaction | Front office | Back office | Team manager | Senior manager | Dual auth |
|---|---|---|---|---|---|
| Disclose after SV | ✅ | ✅ | — | — | — |
| Address / preferences | ✅ | ✅ | — | — | — |
| Name (evidence) | — | ✅ | — | — | — |
| Bank change (EV) | — | ✅ | first payment | — | — |
| Fund switch | — | ✅ | — | — | — |
| Trust / trustee / assignment | — | ✅ | senior case handler | — | — |
| Top-up ≤£25k | — | ✅ | — | — | — |
| Top-up >£25k / EDD | — | prepares | — | approves | — |
| Withdrawal/surrender ≤£25k | — | ✅ | — | — | — |
| £25k–£100k | — | prepares | approves | — | — |
| >£100k | — | prepares | — | approves | ✅ >£250k |
| Death claim ≤£50k | — | ✅ | — | — | — |
| £50k–£250k | — | prepares | approves | — | — |
| >£250k | — | prepares | — | approves | ✅ |
| Regulator/police disclosure | — | — | — | DPO/MLRO/Legal | — |

Row records: `authority: withdrawal ≤25000 → back_office` · `authority: withdrawal 25000–100000 → team_manager` · `authority: withdrawal >100000 → senior_manager (dual >250000)` · `authority: assignment → senior_case_handler + legal` · `authority: death_claim >250000 → senior_manager + dual`.

## II.14 SLA table (atomic)
*meta: doc=02-BOND | sec=II.14 | aud=ops | type=table | data=fictional*

| Transaction | SLA |
|---|---|
| Address / preferences / opt-out | Same day (suppression ≤24h) |
| Name change | 3 business days |
| Bank change | 2 business days (+hold) |
| Fund switch | Placed ≤2 business days |
| Withdrawal-instruction change | 3 business days |
| Trust / trustee / assignment | 10 business days |
| EoW | 5 business days |
| Top-up (standard / EDD) | 3 / 5–10 business days |
| Partial withdrawal / full surrender | 5 / 10 business days |
| DSAR | 1 month (ext. to 3) |
| Breach → ICO | ≤72 hours (where reportable) |
| Complaint summary / final | Day 3 / 8 weeks |
| Death claim ack/reqs/assess/pay | 1 / 3 / 5 / 5 business days |

## II.15 Ops / oversight layer
*meta: doc=02-BOND | sec=II.15 | aud=ops | type=ops | data=mixed*
KPIs: SLA attainment; verification failures; **chargeable-event certificate accuracy/timeliness**; withdrawal/surrender cycle time; MVR-complaint rate; DSAR on-time; breaches; sanctions hits. QA: chargeable-event calculations; method-comparison evidence (§II.8.2); PROD 4 price-and-value; SYSC 9 records. Reporting: DISP 1.10 return (consolidated, first period 1 Jan–30 Jun 2027, PS25/19) + DISP 1.10A publication; HMRC chargeable-event reporting; ICO 72h; OFSI/NCA. FSCS: long-term insurance 100%, no cap. AI monitoring: routing/gate accuracy; disclosure error = potential breach.

## II.16 Sources (reference-only chunk)
*meta: doc=02-BOND | sec=II.16 | aud=all | type=sources | data=real*
- HMRC Insurance Policyholder Taxation Manual (chargeable events, s.507A, time apportionment, deficiency relief, PPB) — https://www.gov.uk/hmrc-internal-manuals/insurance-policyholder-taxation-manual
- HMRC: Gains on UK life insurance policies (HS320) — https://www.gov.uk/government/publications/gains-on-uk-life-insurance-policies-hs320-self-assessment-helpsheet
- ITTOIA 2005 (ss.461–546 incl. 507A, 515–526, 528) — https://www.legislation.gov.uk/ukpga/2005/5/contents
- Income tax rates — https://www.gov.uk/income-tax-rates
- FCA COBS 20 (with-profits) — https://handbook.fca.org.uk/handbook/COBS/20/
- FCA COBS 15 — https://handbook.fca.org.uk/handbook/cobs15
- ICO right of access — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/right-of-access/what-should-we-consider-when-responding-to-a-request/
- ICO breaches — https://ico.org.uk/for-organisations/report-a-breach/personal-data-breach/personal-data-breaches-a-guide/
- DPA 2018 Sch 2 — https://www.legislation.gov.uk/ukpga/2018/12/schedule/2/part/1/crossheading/crime-and-taxation-general
- FCA DISP 1.6 / 2.8 — https://handbook.fca.org.uk/handbook/disp1/disp1s6 · https://handbook.fca.org.uk/handbook/disp2/disp2s8
- FCA PS25/19 — https://www.fca.org.uk/publications/consultation-papers/ps25-19-improving-complaints-reporting-process
- FCA FG21/1 — https://www.fca.org.uk/publications/finalised-guidance/guidance-firms-fair-treatment-vulnerable-customers
- OPG100 / Use an LPA — https://www.gov.uk/government/publications/find-out-if-someone-has-a-registered-attorney-or-deputy · https://www.gov.uk/use-lasting-power-of-attorney
- Scottish Confirmation — https://www.mygov.scot/confirmation
- OFSI — https://www.gov.uk/government/publications/financial-sanctions-general-guidance/uk-financial-sanctions-general-guidance
- NCA SARs — https://www.nationalcrimeagency.gov.uk/what-we-do/crime-threats/money-laundering-and-illicit-finance/suspicious-activity-reports
- FSCS — https://www.fscs.org.uk/what-we-cover/

---

# PART III — RAG ASSETS (Horizon Bond)

## III.1 Glossary
*meta: doc=02-BOND | sec=III.1 | aud=all | type=glossary | data=mixed*
**Segment** — one of the identical mini-policies making up the bond. **Chargeable event** — trigger for income-tax assessment (§4.3). **5% allowance** — cumulative tax-deferred annual withdrawal (§4.2). **Excess gain** — partial withdrawal above the cumulative allowance. **Top-slicing** — spreading a gain over policy years for rate purposes (§4.4). **20% credit** — non-reclaimable onshore basic-rate credit. **PPB** — personal portfolio bond; punitive 15% deemed-gain regime (§3.7). **s.507A** — HMRC recalculation of wholly disproportionate gains (§4.9). **Time-apportionment relief** — gain reduction for non-resident days (§4.10). **Deficiency relief** — relief where earlier gains exceeded the true gain (§4.11). **MVR** — market value reduction on with-profits exits (§3.6). **Reversionary/terminal bonus** — annual/final with-profits bonuses. **Forward pricing** — deals priced at the next valuation point (§3.5). **Assignation** — Scottish assignment (§11). **Chargeable event certificate** — Aldercrest's gain statement to the customer/HMRC.

## III.2 FAQ — customer layer
*meta: doc=02-BOND | sec=III.2 | aud=customer | type=faq | data=mixed*
**Q: How much can I take out each year without tax now?** 5% of what you invested, cumulative if unused (§4.2) — it defers tax, it doesn't cancel it.
**Q: I need £50,000 — does it matter how I take it?** Hugely: cashing whole segments usually tracks real growth; a big partial withdrawal across all segments can create an artificial taxable gain (§4.9, §5).
**Q: Will you tell HMRC about my gain?** Yes — you'll get a chargeable event certificate and we report where required (§4.3).
**Q: I live in Scotland — do Scottish tax rates apply to my bond gain?** No: bond gains are savings income, taxed at UK-wide rates (§4.5, §11).
**Q: What's an MVR?** A reduction that can apply if you leave the with-profits fund after markets fall — never on death, and not at your 10th-anniversary guarantee point (§3.6).
**Q: Can I give the bond to my daughter?** Yes — a gift assignment isn't a chargeable event, and future gains are taxed as hers (§4.7).

## III.3 FAQ — back office / ops layer
*meta: doc=02-BOND | sec=III.3 | aud=back_office | type=faq | data=mixed*
**Q: Customer instructs a £60,000 partial withdrawal in year 3 of a £100,000 bond — action?** Warn: cumulative allowance is £15,000 → £45,000 excess gain; present segment-surrender comparison before processing (§4.9, §II.8.2).
**Q: Trustees surrender a trust bond — top-slicing?** No — trustees cannot top-slice; typical charge 25% after the credit (§4.8).
**Q: Adviser requests a switch into a customer's own share portfolio?** Refuse — non-permitted assets would create a PPB (§3.7, §II.6.5).
**Q: Assignment "in consideration of £80,000" — treatment?** Money's-worth assignment = chargeable event; calculate the gain and issue a certificate (§4.3, §II.6.8).
**Q: Who approves a £300,000 full surrender?** Senior manager plus dual authorisation (>£250k) (§II.13).

## III.4 Specimen policy record (SYNTHETIC — a reserved number, never a customer)
*meta: doc=02-BOND | sec=III.4 | aud=all | type=sample_record | data=fictional*
`policy_no: HB-40582213` · `product: Horizon Bond (onshore)` · `status: in force` · `holder: Argon Basalt 27` · `dob: 1962-09-30` · `address: 8 Cornice Row, Sampleton (registered)` · `lives_assured: Argon Basalt 27; Lumen Basalt 33 (last survivor)` · `invested: £120,000 on 2019-03-01 (1,000 segments)` · `top_ups: none` · `current_value: £151,240` · `funds: 60% Managed Growth (AMC 0.65%), 40% With-Profits (§3.6)` · `withdrawals: £6,000/yr (5%) since 2020-03; cumulative allowance used £36,000 of £42,000` · `adviser_LOA: Brightwater IFA LLP, FRN 618902 (fictional), scope=information+switches+withdrawals, expires 2026-11` · `trust: none` · `bank_last4: 2209` · `vulnerability_flag: none` · `recent: 2026-05-20 switch 10% WP→Managed (no MVR, post-anniversary); 2026-04-02 valuation issued` · `open_cases: none`.
**This is a specimen, not a customer.** It is a worked illustration of a completed Horizon Bond record, printed here so the segment and 5% allowance mechanics can be taught against a filled-in example. Its policy number comes from the block reserved for specimens — eight digits at or above 20,100,000 — which the book cannot issue to anybody, so no specimen can ever collide with a real policy. A live customer's record would never appear in a product manual; this one is safe to print precisely because there is nobody behind it.

## III.5 Worked case walkthrough — excess withdrawal, certificate, complaint
*meta: doc=02-BOND | sec=III.5 | aud=all | type=case_study | data=fictional (rules real)*
Argon (HB-40582213) requests £40,000 "urgently" to a **new** bank account. EV forced (new payee + urgency, §II.3); passes. Agent surfaces the method comparison (§II.8.2): a £40,000 partial withdrawal now exceeds his remaining cumulative allowance (£6,000 this year + £6,000 unused = £12,000) → **£28,000 excess gain**; surrendering ~264 whole segments instead crystallises gain ≈ real growth (~£6,900). Argon chooses partial anyway; back office processes (band £25k–£100k → team-manager approval, §II.13), issues the certificate at policy-year end (§4.3), sanctions screen clear. Argon later complains about the tax: DISP flow (§II.11) — final response inside 8 weeks explains the pre-transaction warning was given and logged; FOS rights included. Cross-sources: this doc §4.9/§5/§II.8 + Doc 4 (DISP/Consumer Duty understanding) + Doc 5 §11/§14.

## III.6 Cross-source reasoning map (demo questions)
*meta: doc=02-BOND | sec=III.6 | aud=all | type=routing | data=mixed*
1. "Scottish higher-rate taxpayer surrenders after 8 years — what rate applies to the slice?" → §4.4 + §4.5/§11 (UK savings rates) — two-hop tax reasoning. 2. "Customer moved to Dubai for 4 of the 10 policy years" → §4.10 time apportionment + §II.8 signposting. 3. "Trustee bond surrender vs assigning segments to the adult beneficiary first" → §4.7 + §4.8 — planning comparison, signpost advice. 4. "Was the MVR applied correctly?" → §3.6 + Doc 4 B7 (COBS 20/PPFM) + §II.11 complaints. Complexity tier: MEDIUM–HIGH — use for multi-step tax-arithmetic demos.

## III.7 Trust stress-test case — DGT surrender vs appointment out (attribution ladder)
*meta: doc=02-BOND | sec=III.7 | aud=all | type=case_study | data=fictional (rules real)*
Synthetic record: `HB-51230944` held by the **Elm Grove Discounted Gift Trust** (discretionary DGT, settlor Ruth Calder, dob 1948, settled 2015 with £300,000; underwritten discount £128,000 → CLT £172,000; retained payments £15,000/yr; current value £342,000; trustees: Ruth's two sons; TRS URN on file). Ruth died in March 2025. The sons call in July 2026: "surrender the bond and split it". Correct chain: (1) trust classification — DGT retained payments **ceased on Ruth's death**; her carve-out dies with her (§12.3); (2) **attribution ladder** — settlor died in an **earlier tax year** → a trustee surrender is taxed at **25% net, no top-slicing** (§12.4); (3) better route — **appoint segments out** to each adult son first, then they surrender with personal rates + top-slicing (§12.5), subject to an **exit-charge** check quarters since the 2025 anniversary (Doc 1 §12.2); (4) operational gates — both trustees sign, IDs verified, TRS current, sanctions screen, method comparison logged (§II.6.10, §II.8.2); (5) signpost advice — Aldercrest flags, never advises. Failure modes this case catches in evals: quoting settlor-rate/top-slicing after settlor death; ignoring the exit charge; processing on one trustee's instruction.

---
*End of Document 2 v2.1. Firm-wide regulation: Document 4. Cross-product master procedures, data dictionary and intent routing: Document 5. Evals, observability and change management: Document 6.*
