# DOCUMENT 3 — PERSONAL PENSION (PRODUCT MASTER) v2
*meta: doc=03-PEN | sec=frontmatter | aud=all | type=caveats | data=mixed*
## Aldercrest "Retirement Account"
*meta: doc=03-PEN | sec=frontmatter-title | aud=all | type=caveats | data=mixed*

**Fictional company:** Aldercrest Life Assurance plc ("Aldercrest Life"). Not a real FCA-authorised insurer.
**Grounding:** Regulators and all tax/regulatory figures are real (2025/26), verified against sources in Document 4 and §II.16. Aldercrest charges, limits, SLAs and thresholds are fictional but realistic. Knowledge-base date: **13 July 2026.** Finance Act 2026 items are flagged "legislated, not yet in force."
**RAG formatting convention:** split on headings — every `##`/`###` is one chunk (target 500–800 tokens; ~10% overlap for long prose only). Tables and Sources are **atomic**. `meta:` schema — `doc` | `sec` | `aud` | `type` | `data` (real/fictional/mixed).
**Complexity tier for RAG demo:** HIGH (interlocking allowances: AA/taper/MPAA/LSA/LSDBA, transitional protections, irreversible access decisions, Scottish-rate interaction).

---

# PART I — PRODUCT

## 1. What the product is and its purpose
*meta: doc=03-PEN | sec=1 | aud=all | type=overview | data=mixed*
A personal pension is a **defined-contribution (money purchase) registered pension scheme**: member and/or employer contribute, contributions receive **tax relief**, the fund grows tax-advantaged, and benefits are drawn from a minimum age. Regulated under **COBS**. The Aldercrest Retirement Account is a standard personal pension with a fund range and an optional wider self-invested (SIPP-style) tier.

## 2. Target market and eligibility
*meta: doc=03-PEN | sec=2 | aud=all | type=eligibility | data=mixed*
Target: individuals saving for retirement — employees, self-employed, and (limited) non-earners. Not for those needing access before minimum pension age or unwilling to lock money away. Age: from birth (parent/guardian can open for a child) to **75** for tax-relieved contributions. Tax relief needs **relevant UK earnings** above £3,600; **non-earners can contribute £3,600 gross (£2,880 net)** per year. Minimum contribution (fictional): £50/month or £1,000 single. Scotland/NI notes §12; non-residence §13.

## 3. Product rules, features, charges

### 3.1 Contributions
*meta: doc=03-PEN | sec=3.1 | aud=all | type=product_rule | data=mixed*
Regular and/or single; personal, employer, or third-party (e.g. parent/grandparent — relief follows the member). Employer contributions are paid gross and don't use the member's relief-at-source mechanics.

### 3.2 Fund options and default
*meta: doc=03-PEN | sec=3.2 | aud=all | type=product_rule | data=fictional*
Default lifestyle/target-date funds, risk-rated multi-asset, index trackers, ESG funds; SIPP tier adds a wider permitted range. Workplace/auto-enrolment use: the **default-fund charge cap of 0.75% p.a.** applies to qualifying schemes (real rule).

### 3.3 Charges
*meta: doc=03-PEN | sec=3.3 | aud=all | type=product_rule | data=fictional*
Annual product charge 0.30% p.a.; fund AMCs 0.10%–1.00%; SIPP tier admin fee £180 p.a.

### 3.4 Tax relief mechanics — relief at source, net pay, salary sacrifice
*meta: doc=03-PEN | sec=3.4 | aud=all | type=tax_rule | data=real*
The Retirement Account uses **relief at source (RAS)**: the member pays 80% and Aldercrest reclaims **20%** from HMRC (£80 net = £100 gross); **higher (40%) / additional (45%) rate** taxpayers claim the extra **20%/25%** via Self Assessment or tax code. Contrast (for transfers-in and adviser queries): **net pay** (common in occupational schemes) deducts contributions before tax — full relief automatic, but **non-taxpayers get no relief** (whereas RAS gives even non-taxpayers 20% on up to £3,600 gross). **Salary sacrifice**: the member gives up salary; the employer pays the amount as an **employer contribution** — saves employee and employer **National Insurance**, but reduces salary-linked benefits and cannot take pay below minimum wage. Scottish-rate interaction: §12.

## 4. Tax treatment (real UK rules)

### 4.1 Annual allowance and carry-forward
*meta: doc=03-PEN | sec=4.1 | aud=all | type=tax_rule | data=real*
**£60,000** gross per tax year across all pensions (or 100% of relevant UK earnings if lower). **Carry-forward** of unused allowance from the previous **three** tax years (must have been a scheme member; use the current year first). Exceeding it → **annual allowance charge** at marginal rate; "**scheme pays**" can settle it from the fund where conditions are met.

### 4.2 Tapered annual allowance
*meta: doc=03-PEN | sec=4.2 | aud=all | type=tax_rule | data=real*
For high earners: reduced **£1 for every £2** of **adjusted income** over **£260,000** (only if **threshold income** > £200,000), to a floor of **£10,000** at adjusted income ≥ £360,000.

### 4.3 Money Purchase Annual Allowance (MPAA)
*meta: doc=03-PEN | sec=4.3 | aud=all | type=tax_rule | data=real*
Once **taxable** pension income is flexibly accessed (FAD income or any UFPLS), future DC contributions are capped at **£10,000/yr**, with **no carry-forward**. Taking **only** PCLS with no taxable income does **not** trigger it; nor do **small-pot lump sums** (§9.5).

### 4.4 Tax-free growth
*meta: doc=03-PEN | sec=4.4 | aud=all | type=tax_rule | data=real*
The fund grows free of UK income tax and CGT.

### 4.5 Lump sum allowances (LSA / LSDBA)
*meta: doc=03-PEN | sec=4.5 | aud=all | type=tax_rule | data=real*
Tax-free lump sums are capped by the **Lump Sum Allowance (LSA) £268,275** and the **Lump Sum and Death Benefit Allowance (LSDBA) £1,073,100** (Finance Act 2024, from 6 April 2024).

### 4.6 LTA abolition and transitional protections
*meta: doc=03-PEN | sec=4.6 | aud=all | type=tax_rule | data=real*
The **lifetime allowance was abolished on 6 April 2024**. Protections still matter because they **raise** the LSA/LSDBA: **Fixed Protection 2016** → protected amounts based on £1.25m (LSA £312,500); **Individual Protection 2016** → personal amount = pension value at 5 April 2016 (max £1.25m; LSA = 25% of it). Members who took benefits **before 6 April 2024** can apply to any scheme for a **Transitional Tax-Free Amount Certificate (TTFAC)** — evidence-based substitution of actual tax-free amounts used instead of the standard 25% deduction; once used it applies to all future crystallisations and **cannot be revoked** — signpost advice. Back office must check protection certificates/TTFACs **before** paying any PCLS (§II.8.2).

### 4.7 Access age
*meta: doc=03-PEN | sec=4.7 | aud=all | type=tax_rule | data=real*
**Normal minimum pension age 55, rising to 57 on 6 April 2028** (transitional protections for some unqualified rights at 55). Earlier access only on **ill-health** (or serious ill-health — full commutation where life expectancy <12 months) or a protected pension age.

## 5. WORKED EXAMPLES — relief and allowance interplay
*meta: doc=03-PEN | sec=5 | aud=all | type=worked_example | data=real (figures fictional)*
**(a) Higher-rate relief:** member wants £10,000 gross → pays £8,000; Aldercrest reclaims £2,000 (RAS); member claims £2,000 via Self Assessment → net cost **£6,000**.
**(b) Taper:** adjusted income £320,000 → excess £60,000 → allowance reduced £30,000 → AA = **£30,000**.
**(c) MPAA trap:** member takes one £4,000 UFPLS in May, then tries to pay £15,000 in November → only £10,000 allowed (MPAA, no carry-forward); £5,000 excess → AA charge (§4.3).
**(d) Scottish intermediate-rate saver (see §12):** RAS still adds 20%; the Scottish 21% intermediate-rate member claims the extra **1%** via HMRC.

## 6. HOW TO BUY — new business journey
*meta: doc=03-PEN | sec=6 | aud=all | type=journey | data=mixed*
1. Advised (COBS 9A suitability) vs non-advised. **Safeguarded/DB transfers ≥ £30,000 require regulated advice** (COBS 19); Aldercrest verifies the advising firm's permissions. 2. Application: personal details, contributions, funds, target retirement age, expression of wishes. 3. KYC/AML (MLR 2017). 4. Money in: DD/transfer; RAS claimed; transfers-in verified with the ceding scheme + **scam due diligence** (§II.12). 5. Disclosure: Key Features/illustration; at decumulation — **risk warnings**, the **Pension Wise "nudge"** (COBS 19.7) and **investment pathways** for non-advised drawdown (§9.2). 6. Cancellation: **30 days** for the new contract and transfers (COBS 15). **Irreversibility warning:** taking a **PCLS or UFPLS is NOT cancellable** — LSA/LSDBA usage and the MPAA trigger cannot be reversed even if the money is returned (FCA/HMRC statement, 2025).

## 7. Policy servicing (summary)
*meta: doc=03-PEN | sec=7 | aud=customer | type=overview | data=fictional*
Change details; contribution amount/frequency; start/stop; fund switches; target retirement age; expression of wishes; consolidate/transfer in. Full procedures **§II.6**.

## 8. Putting more money in (summary)
*meta: doc=03-PEN | sec=8 | aud=customer | type=overview | data=mixed*
Increase regulars; single top-ups; employer contributions; transfers-in. Checks: AA/taper/MPAA headroom, relief eligibility, AML for large singles. Operational detail **§II.7**.

## 9. TAKING MONEY OUT — retirement options

### 9.1 Tax-free cash (PCLS)
*meta: doc=03-PEN | sec=9.1 | aud=all | type=tax_rule | data=real*
Normally **25%** of the amount crystallised, capped by the **LSA £268,275** (higher with protections/TTFAC §4.6). Taking PCLS alone (funds to drawdown, no income) does **not** trigger the MPAA.

### 9.2 Flexi-access drawdown and investment pathways
*meta: doc=03-PEN | sec=9.2 | aud=all | type=product_rule | data=real*
Take PCLS, keep the rest invested, draw taxable income flexibly (**first taxable income payment triggers the MPAA**). **Investment pathways (COBS 19.10, real):** non-advised members entering drawdown must be offered four ready-made options — **1** no plans to touch the money within 5 years; **2** plan to buy an annuity within 5 years; **3** plan to take long-term income within 5 years; **4** plan to take it all within 5 years — plus warnings on holding >50% cash. Aldercrest maps each pathway to a governed fund.

### 9.3 UFPLS
*meta: doc=03-PEN | sec=9.3 | aud=all | type=tax_rule | data=real*
Ad-hoc lump sums: **25% tax-free / 75% taxed** at marginal rate; **triggers the MPAA on the first payment**; each payment uses LSA on its tax-free element.

### 9.4 Annuity and the open market option
*meta: doc=03-PEN | sec=9.4 | aud=all | type=product_rule | data=real*
Lifetime annuity = guaranteed income, taxed as income; PCLS first if wanted. **Open market option (real):** members must be told they can **shop around** and buy from any provider — often materially better rates (especially enhanced/impaired annuities). Aldercrest quotes must present the OMO prominently.

### 9.5 Small pots and trivial commutation
*meta: doc=03-PEN | sec=9.5 | aud=all | type=tax_rule | data=real*
**Small-pot lump sums:** a personal-pension pot ≤ **£10,000** can be taken whole (25% tax-free / 75% taxed), up to **three times** for non-occupational pots — and **does not trigger the MPAA** or use LSA. **Trivial commutation (£30,000)** applies to **defined-benefit** rights (and some in-payment benefits), not to uncrystallised DC pots.

### 9.6 Death benefits — current rules and the 2027 change
*meta: doc=03-PEN | sec=9.6 | aud=all | type=tax_rule | data=real*
Death **before 75**: benefits generally **income-tax-free** (if paid/designated within two years); **75+**: taxed at the **beneficiary's marginal rate**. Options: beneficiary drawdown, lump sum, dependant's annuity; LSDBA tests apply to lump sums. **Legislated, from 6 April 2027 (Finance Act 2026):** most **unused pension funds and death benefits fall within the estate for IHT**; spouse/civil-partner and charity exemptions continue; PRs report and pay (new Pensions Direct Payment Scheme). ~8% of estates expected to be affected annually.

### 9.7 Nominee and successor drawdown (cascading death benefits)
*meta: doc=03-PEN | sec=9.7 | aud=all | type=tax_rule | data=real*
Beneficiary categories: **dependant** (spouse/civil partner, child <23, financially dependent person), **nominee** (anyone the member nominates), **successor** (nominated by a beneficiary). Drawdown can **cascade**: member → nominee drawdown → successor drawdown, staying in the pension wrapper across generations; the income-tax position resets at each death by the **age at death of the last holder** (pre/post-75). Expression-of-wishes quality is therefore critical (§II.6.7).

### 9.8 Emergency tax on first payments and reclaims
*meta: doc=03-PEN | sec=9.8 | aud=all | type=tax_rule | data=real*
First flexible payments are often taxed on an **emergency month-1 code**, over-deducting. Reclaims: **P55** (partial withdrawal, not emptying the pot), **P53Z** (pot emptied, other income), **P50Z** (pot emptied, no other income) — or via Self Assessment/auto-reconciliation. The AI must warn before the first payment and signpost the correct form after (§II.8.2).

### 9.9 Process and timescales
*meta: doc=03-PEN | sec=9.9 | aud=customer | type=overview | data=fictional*
Retirement quote 5 business days; benefits set up 5–10 business days from full instructions; PAYE applied (emergency code possible §9.8).

## 10(a). CUSTOMER-FACING INFORMATION
*meta: doc=03-PEN | sec=10a | aud=customer | type=customer_info | data=mixed*
Plain language: tax relief tops up your savings; access normally from **55 (57 from April 2028)**; usually **25% tax-free**; options — drawdown, lump sums, annuity (shop around). You can: change contributions, switch funds, get quotes, take tax-free cash, set up drawdown/annuity, nominate beneficiaries. Free guidance: **Pension Wise** (50+) and **MoneyHelper**. Complaints → Aldercrest → **FOS** (6 months from final response); some occupational disputes → **The Pensions Ombudsman**. **FSCS:** insured personal pensions **100%, no cap** (SIPP-held assets/bad advice may cap at £85,000).

## 10(b). BACK OFFICE INFORMATION (summary — detail in Part II)
*meta: doc=03-PEN | sec=10b | aud=back_office | type=overview | data=fictional*
RAS application and AA/MPAA validation; protection/TTFAC checks before PCLS; MPAA trigger flags; pathway offer evidence; transfer scam due diligence and DB-advice verification; death-benefit discretion + LSDBA testing; PAYE codes; sanctions screening; value-banded authority.

## 10(c). OPS/OVERSIGHT INFORMATION (summary — detail in Part II)
*meta: doc=03-PEN | sec=10c | aud=ops | type=overview | data=fictional*
KPIs on contribution accuracy, quote/settlement timeliness, transfer turnaround, scam-flag rate; QA on PCLS/LSA/PAYE and risk-warning/nudge delivery; HMRC RAS/event reporting; TPR auto-enrolment touchpoints; Consumer Duty decumulation outcomes.

## 11. Pension sharing and divorce
*meta: doc=03-PEN | sec=11 | aud=all | type=legal | data=real*
On divorce/dissolution a court may make: a **pension sharing order** — a **pension debit** reduces the member's fund and a **pension credit** creates rights for the ex-spouse (transferable to their own scheme); implementation within **4 months** of the later of the order taking effect and receipt of required information; or an **attachment/earmarking order** — part of the member's benefits is paid to the ex-spouse when taken (older, less clean). **Scotland** differs: sharing is agreed in a **Minute of Agreement** or ordered on the **"relevant date"** valuation (separation date), and only pension built up **during the marriage** is normally shared. Aldercrest charges a fictional £350 implementation fee; orders are verified by Legal before implementation (§II.6.9).

## 12. Scotland and Northern Ireland notes
*meta: doc=03-PEN | sec=12 | aud=all | type=legal | data=real*
**Scottish income tax applies to pension income and earnings (non-savings income)** — so PAYE on drawdown/UFPLS/annuity uses Scottish rates/codes (S-prefix). **RAS always adds 20%**: Scottish **intermediate (21%) / higher (42%) / advanced (45%) / top (48%)** rate members claim the extra relief via HMRC; **starter-rate (19%)** members keep the full 20% (HMRC does not claw back the 1%). Divorce valuation differences: §11. **Confirmation** replaces probate for estate-payable death benefits (rare — discretion usually bypasses the estate, §9.6). NI mirrors England & Wales.

## 13. Non-UK residence
*meta: doc=03-PEN | sec=13 | aud=all | type=tax_rule | data=real*
Members who move abroad can usually keep contributing with relief for up to **five tax years** after leaving (if they were resident and a member when they joined), normally capped at **£3,600 gross** unless they retain relevant UK earnings. Overseas transfers (QROPS) carry an **Overseas Transfer Charge** in many cases — specialist referral; not processed in standard servicing. PAYE/NT codes and double-tax treaties govern income paid abroad — signpost advice.

## 14. SPOUSAL BYPASS TRUSTS & DEATH-BENEFIT TRUSTS

### 14.1 Structure and purpose
*meta: doc=03-PEN | sec=14.1 | aud=all | type=tax_rule | data=real (structure) / fictional (terms)*
A **spousal bypass trust** is a discretionary ("pilot") trust the member settles in lifetime (often with £10), then **nominates via the expression of wishes** to receive pension **lump-sum death benefits**. Purpose: proceeds bypass the survivor's estate (no second-death IHT aggregation), protect against remarriage/care-fee erosion, and keep trustee control for children — while the survivor can still benefit as a class member. Trade-off: funds leave the pension wrapper (no further tax-free growth or cascade drawdown, §9.7) and enter the **relevant property regime** (periodic/exit charges, Doc 1 §12.2).

### 14.2 Tax mechanics — pre/post-75 and trust charges
*meta: doc=03-PEN | sec=14.2 | aud=all | type=tax_rule | data=real*
Death **before 75**: lump sum to the bypass trust is income-tax-free if paid within two years (LSDBA-tested, §4.5). Death **at/after 75**: a lump sum to a trust bears the **45% special lump sum death benefits charge**; when trustees later distribute, the beneficiary receives a **reclaimable credit** against their own liability. Inside the trust: relevant property regime — 10-year/periodic and exit charges (Doc 1 §12.2), with the pension-derived fund as trust property. **TRS:** a pilot trust may be outside registration while dormant/nominal, but becomes **registrable once funded** (90-day window) — URN collected at claim (Doc 2 §12.6 logic).

### 14.3 The April 2027 IHT change — does a bypass trust still work?
*meta: doc=03-PEN | sec=14.3 | aud=all | type=tax_rule | data=real (not yet in force)*
From **6 April 2027** (Finance Act 2026), unused pension funds/death benefits fall within the **member's estate for IHT** — this charge lands **before** any payment route, so a bypass trust **does not avoid it** (spouse/charity exemptions still do, but paying to a bypass trust is **not** a spouse payment). Bypass trusts retain their **second-death, control and protection** benefits, at the cost of possible first-death IHT that a direct spouse payment would avoid. The AI must present this as a **changed-planning flag + advice signpost**, never a recommendation. EoW nominations made pre-2027 deserve a review prompt (§II.6.7).

### 14.4 Operational handling at claim
*meta: doc=03-PEN | sec=14.4 | aud=back_office | type=procedure | data=mixed*
On a death claim naming a bypass trust: verify the **trust deed** and all trustees (Doc 1 §II.6.13 lifecycle rules apply); scheme-administrator **discretion** still applies — the EoW nomination guides, it does not bind (§II.9); apply the pre/post-75 split and LSDBA test (§14.2); collect **TRS URN** once funded; sanctions-screen trustee payees; from April 2027, coordinate with PRs on the estate-IHT position (§9.6). Dual-authority bands per §II.13.

---

# PART II — OPERATIONS, SERVICING & CLAIMS (Retirement Account)
*meta: doc=03-PEN | sec=II.0 | aud=all | type=overview | data=mixed*

> Product-tailored operational layer; cross-product master = **Document 5**. Aldercrest specifics fictional; legal rules real (sources §II.16).

## II.1 RAG mapping and audience layers
*meta: doc=03-PEN | sec=II.1 | aud=all | type=routing | data=fictional*
Caller type (§II.2) → identity/authority gates (§II.3, §II.5) → layer (a)/(b)/(c). Most sensitive flows: **pension access** (irreversible), **transfers** (scam risk), **death benefits** (discretion). References: `RA-`+8; `CN-`+10; `CW-`+9; `CMP-`+8; `CLM-`+8.

## II.2 Inbound contact handling — who can contact us
*meta: doc=03-PEN | sec=II.2 | aud=back_office | type=procedure | data=mixed*
Channels/flow as Doc 1 §II.2. Caller types & capture: **member**; **adviser (LOA)** (DB-transfer advice permissions verified for safeguarded ≥£30,000); **LPA/EPA attorney** (OPG ref — common in ill-health); **CoP deputy**; **employer** (contribution matters only — minimum disclosure); **nominated beneficiary/dependant** (death benefits §II.9); **executor/PR** (estate-relevant only); **helper for a vulnerable customer**; **regulators/legal (incl. TPR)** → §II.10. Verify before disclosing anything.

## II.3 Identity verification & authentication (SV/EV)
*meta: doc=03-PEN | sec=II.3 | aud=back_office | type=procedure | data=mixed*
**SV** — three of four: `RA-`; name+DOB; registered address (or last-4 linked account); memorable item. **EV** — SV + OTP to registered contact + one further check; required for: bank changes; **any pension access**; **transfers out**; address change then bank/benefit request within 30 days; beneficiary/authority changes on high value. Extra step-up trigger: **scam indicators** (cold-contact origin, "guaranteed returns", overseas/unregulated investments, "loophole"/early-access claims, unregulated introducer) → §II.12. Failure handling as Doc 1 §II.3.

## II.4 Data protection & security

### II.4.1 Framework and lawful bases
*meta: doc=03-PEN | sec=II.4.1 | aud=back_office | type=legal | data=real*
Controller under UK GDPR/DPA 2018 (ICO; DUAA 2025 commencing). Bases: contract; legal obligation (**RAS/HMRC event reporting**, AML, complaints, retention); legitimate interests (fraud/scam prevention); consent (marketing only — PECR, Doc 4 A16).

### II.4.2 Special-category data
*meta: doc=03-PEN | sec=II.4.2 | aud=back_office | type=legal | data=real*
Arises on **ill-health/serious-ill-health access** and **death benefits**: explicit consent and/or Art 9(2)(f); minimise; restrict.

### II.4.3 Minimisation, sharing, secure handling
*meta: doc=03-PEN | sec=II.4.3 | aud=back_office | type=procedure | data=mixed*
Employers get contribution-relevant data only; advisers per LOA scope; helpers per consent. Encrypted/secure outbound; registered address; Art 32 controls.

### II.4.4 SARs, rectification, erasure
*meta: doc=03-PEN | sec=II.4.4 | aud=back_office | type=procedure | data=real*
One-month SAR (extendable +2); clock-stop only for clarification/ID; redact third parties; rectify with evidence; erasure usually overridden by retention.

### II.4.5 Breaches and retention
*meta: doc=03-PEN | sec=II.4.5 | aud=back_office | type=procedure | data=mixed*
Breach register; **ICO ≤72h** where reportable; individuals if high risk. Retention: pension records 6 years after benefits end (longer for protection/transfer history); AML 5 years; complaints ≥3 years.

## II.5 Third-party authority
*meta: doc=03-PEN | sec=II.5 | aud=back_office | type=procedure | data=real*
As Doc 1 §II.5 plus: an attorney generally **cannot** make/alter an **expression of wishes** or nomination unless expressly authorised and in the donor's best interests → escalate; deputies likewise. Advisers: verify **pension-transfer permissions** for safeguarded business. Beneficiaries/PRs: verified at claim (§II.9). Unverifiable → refuse, explain, log.

## II.6 Servicing procedures — one per chunk

### II.6.1 Change of address
*meta: doc=03-PEN | sec=II.6.1 | aud=back_office | type=procedure | data=fictional*
SV; confirm to old **and** new; 30-day watch. Front office; same day. Exception: +bank/benefit request in 30 days → EV + FC watch.

### II.6.2 Change of name
*meta: doc=03-PEN | sec=II.6.2 | aud=back_office | type=procedure | data=fictional*
SV + evidence. Back office; 3 business days.

### II.6.3 Change of bank (HIGH RISK)
*meta: doc=03-PEN | sec=II.6.3 | aud=back_office | type=procedure | data=fictional*
Member only; attorney/deputy in scope. **SV+EV**; verify account; hold before first payment; confirm to registered contact. 2 business days. Exception → APP-fraud handling (§II.12).

### II.6.4 Preferences / marketing consent
*meta: doc=03-PEN | sec=II.6.4 | aud=back_office | type=procedure | data=mixed*
SV; consent (UK GDPR + PECR); opt-out immediate; suppression ≤24h. Same day.

### II.6.5 Contribution change / start / stop
*meta: doc=03-PEN | sec=II.6.5 | aud=back_office | type=procedure | data=mixed*
Member/employer/adviser in scope. SV; validate **AA (£60,000)/taper/MPAA (£10,000)** headroom and relief eligibility; warn on over-contribution (scheme-pays route §4.1). 3 business days / next cycle.

### II.6.6 Fund switch and pathway review
*meta: doc=03-PEN | sec=II.6.6 | aud=back_office | type=procedure | data=mixed*
SV; permitted funds; if in drawdown non-advised, re-offer **investment pathways** at review points (§9.2). Placed ≤2 business days.

### II.6.7 Expression of wishes / beneficiary nomination
*meta: doc=03-PEN | sec=II.6.7 | aud=back_office | type=procedure | data=mixed*
Personal right of the member; attorneys → escalate (§II.5). SV; signed form; capture dependants/nominees clearly to support discretion and **cascade** planning (§9.7). 5 business days.

### II.6.8 Target retirement age change
*meta: doc=03-PEN | sec=II.6.8 | aud=back_office | type=procedure | data=mixed*
SV; check NMPA (55 → **57 from 6 April 2028**; protected ages honoured). 3 business days.

### II.6.9 Pension sharing order implementation
*meta: doc=03-PEN | sec=II.6.9 | aud=back_office | type=procedure | data=mixed*
Verify the sealed order + decree; Legal sign-off; implement the **debit/credit within 4 months** of the later of order effect and complete information (§11); fictional fee £350; Scottish Minute of Agreement variants → Legal. Senior case handler.

### II.6.10 Transfer in / consolidation
*meta: doc=03-PEN | sec=II.6.10 | aud=back_office | type=procedure | data=mixed*
SV; verify ceding scheme; **scam due diligence** (§II.12); safeguarded ≥£30,000 → evidence of regulated advice; no loss of protections unnoticed (§4.6 — transfers can void FP2016 if contributions restart elsewhere: warn + signpost). 10 business days + ceding timescales.

### II.6.11 Duplicates / quotes / vulnerability flags
*meta: doc=03-PEN | sec=II.6.11 | aud=back_office | type=procedure | data=fictional*
Duplicates: SV; 3 business days. Retirement quotes: 5 business days (OMO shown §9.4). Vulnerability flags: sensitive capture; same day.

## II.7 Putting money in — operational checks
*meta: doc=03-PEN | sec=II.7 | aud=back_office | type=procedure | data=mixed*
Apply RAS; validate AA/taper/MPAA; relief eligibility (relevant earnings; £3,600 non-earner route); employer contributions gross. **AML/SoF (MLR 2017):** single ≥£25,000, aggregate ≥£50,000/12m, or third-party/high-risk source → SoF evidence; EDD for PEPs/high-risk. 3 business days (5–10 EDD; transfers per §II.6.10).

## II.8 Taking money out

### II.8.1 Universal controls
*meta: doc=03-PEN | sec=II.8.1 | aud=back_office | type=procedure | data=mixed*
**SV+EV**; authority + right to receive (registered account unless verified legal authority); **sanctions screening** (confirmed match → freeze + OFSI); **scam checks**; vulnerability checks; tax flags + **Pension Wise nudge** (COBS 19.7).

### II.8.2 Access processing sequence
*meta: doc=03-PEN | sec=II.8.2 | aud=back_office | type=procedure | data=mixed*
1) Confirm **NMPA/ill-health** basis (§4.7). 2) Check **protections/TTFAC before PCLS** (§4.6) and LSA headroom (§4.5/§9.1). 3) Deliver **risk warnings**; non-advised drawdown → **pathways offer evidenced** (§9.2). 4) State **irreversibility** of PCLS/UFPLS and the **MPAA consequence** (§4.3, §6.6). 5) Set PAYE; warn on **emergency tax** and reclaim forms (§9.8). 6) Execute (disinvest → pay); SLA 5–10 business days. Authority bands §II.13.

## II.9 Claims — death benefits
*meta: doc=03-PEN | sec=II.9 | aud=back_office | type=claims | data=mixed*
1) Notification (anyone; Tell Us Once/DNS); `CLM-`; Bereavement Team; vulnerability care. 2) Establish **age at death** (pre/post-75 tax split §9.6). 3) Documents: death certificate; EoW; beneficiary IDs; grant/Confirmation only where estate-payable. 4) **Discretion**: scheme administrator decides guided by the EoW; capture dependants/nominees; consider **cascade** options (§9.7); disputes → senior assessor. 5) **LSDBA** test lump sums (§4.5). 6) Sanctions screen. 7) Pay/designate within two years to keep pre-75 tax-free status (§9.6). Timescales/authority: ack 1 / reqs 3 / assess 5 / pay 5 business days; handler ≤£50k; manager £50k–£250k; dual >£250k; Head of Claims >£1m. **From 6 April 2027:** support PRs with IHT valuations (Pensions Direct Payment Scheme) — legislated (§9.6).

## II.10 Regulators and legal third parties
*meta: doc=03-PEN | sec=II.10 | aud=back_office | type=legal | data=real*
No front-line disclosure; route to DPO/MLRO/Tax/Legal; **DPA 2018 Sch 2 para 2** applied case-by-case, necessary and proportionate; court orders compel; **no tipping off** (POCA s.333A). Routine HMRC RAS/event reporting and **TPR** auto-enrolment touchpoints are scheme-team business, not disclosure decisions.

## II.11 Complaints (DISP)
*meta: doc=03-PEN | sec=II.11 | aud=back_office | type=procedure | data=real*
Log all (`CMP-`); day-3 summary resolution; 8-week final response; FOS within 6 months (letter must say so). Jurisdiction note: contract-based personal pensions → **FOS**; some occupational/administration disputes → **The Pensions Ombudsman** — signpost correctly. Drivers: emergency tax (§9.8), transfer delays, MPAA surprises.

## II.12 Vulnerable customers, scams & financial crime
*meta: doc=03-PEN | sec=II.12 | aud=back_office | type=procedure | data=mixed*
FG21/1 + Consumer Duty (decumulation and ill-health = elevated vulnerability); authorised helpers get the same support (PRIN 2A.6.5R); suspected financial abuse → pause + escalate. **Pension scams:** apply transfer due diligence — regulated "**amber/red flag**" style checks (unregulated introducers, incentives, overseas investments, pressure) → pause, MoneyHelper safeguarding guidance referral, or refuse (red flags); signpost **FCA ScamSmart**. Sanctions: freeze + OFSI. AML/POCA: SAR → MLRO; DAML (7 working days; 31-day moratorium, extendable to 186); no tipping off.

## II.13 Authority levels matrix (atomic)
*meta: doc=03-PEN | sec=II.13 | aud=back_office | type=table | data=fictional*

| Transaction | Front office | Back office | Team manager | Senior manager | Dual auth |
|---|---|---|---|---|---|
| Disclose after SV | ✅ | ✅ | — | — | — |
| Address / preferences | ✅ | ✅ | — | — | — |
| Name (evidence) | — | ✅ | — | — | — |
| Bank change (EV) | — | ✅ | first payment | — | — |
| Contribution change | — | ✅ | — | — | — |
| Fund switch / TRA change | — | ✅ | — | — | — |
| EoW / nomination | — | ✅ | senior case handler | — | — |
| Contribution/top-up ≤£25k | — | ✅ | — | — | — |
| >£25k / EDD | — | prepares | — | approves | — |
| Transfer in | — | ✅ (post scam-DD) | approves | — | — |
| Transfer out / DB | — | prepares | — | approves (advice verified) | ✅ high value |
| Pension sharing order | — | prepares | senior case handler | Legal sign-off | — |
| Pension access ≤£50k | — | ✅ | — | — | — |
| £50k–£250k | — | prepares | approves | — | — |
| >£250k | — | prepares | — | approves | ✅ |
| Death benefit ≤£50k | — | ✅ | — | — | — |
| £50k–£250k | — | prepares | approves | — | — |
| >£250k / >£1m | — | prepares | — | approves / Head of Claims | ✅ |
| Regulator/police disclosure | — | — | — | DPO/MLRO/Legal | — |

Row records: `authority: pension_access ≤50000 → back_office` · `authority: pension_access 50000–250000 → team_manager` · `authority: pension_access >250000 → senior_manager + dual` · `authority: transfer_out_DB → senior_manager (advice verified) + dual high value` · `authority: pension_sharing → senior_case_handler + legal` · `authority: death_benefit >1000000 → head_of_claims + dual`.

## II.14 SLA table (atomic)
*meta: doc=03-PEN | sec=II.14 | aud=ops | type=table | data=fictional*

| Transaction | SLA |
|---|---|
| Address / preferences / opt-out | Same day (suppression ≤24h) |
| Name change | 3 business days |
| Bank change | 2 business days (+hold) |
| Contribution change | 3 business days / next cycle |
| Fund switch | Placed ≤2 business days |
| TRA change | 3 business days |
| EoW / nomination | 5 business days |
| Transfer in | 10 business days (+ceding) |
| Pension sharing implementation | ≤4 months (statutory) — Aldercrest target 6 weeks |
| Retirement quote | 5 business days |
| Pension access set-up | 5–10 business days |
| Top-up (standard / EDD) | 3 / 5–10 business days |
| DSAR | 1 month (ext. to 3) |
| Breach → ICO | ≤72 hours (where reportable) |
| Complaint summary / final | Day 3 / 8 weeks |
| Death benefit ack/reqs/assess/pay | 1 / 3 / 5 / 5 business days |

## II.15 Ops / oversight layer
*meta: doc=03-PEN | sec=II.15 | aud=ops | type=ops | data=mixed*
KPIs: contribution accuracy; quote/settlement timeliness; transfer turnaround; **scam-flag rate**; pathway-offer completion; emergency-tax reclaim signposting rate; DSAR on-time; breaches; sanctions hits. QA: PCLS/LSA/PAYE accuracy; protection/TTFAC checks; risk-warning + **Pension Wise nudge** delivery; Consumer Duty decumulation outcomes; SYSC 9 records. Reporting: DISP 1.10 (consolidated return first period 1 Jan–30 Jun 2027, PS25/19) + 1.10A; **HMRC RAS and event reporting**; FCA retirement income data; **TPR** AE touchpoints; ICO 72h; OFSI/NCA. FSCS: insured personal pensions 100% no cap. AI monitoring: routing/gate accuracy; disclosure error = potential breach.

## II.16 Sources (reference-only chunk)
*meta: doc=03-PEN | sec=II.16 | aud=all | type=sources | data=real*
- HMRC annual allowance — https://www.gov.uk/tax-on-your-private-pension/annual-allowance
- HMRC tax on your private pension — https://www.gov.uk/tax-on-your-private-pension
- HMRC lump sum allowances (abolition of LTA) — https://www.gov.uk/government/publications/lifetime-allowance-guidance-newsletter-march-2024
- HMRC Pensions Tax Manual (protections, TTFAC, MPAA, small pots) — https://www.gov.uk/hmrc-internal-manuals/pensions-tax-manual
- HMRC IHT on pensions (6 April 2027) — https://www.gov.uk/government/publications/inheritance-tax-on-pensions
- Emergency tax reclaims P55/P53Z/P50Z — https://www.gov.uk/claim-tax-refund/you-get-a-pension
- Pension sharing on divorce — https://www.gov.uk/money-property-when-relationship-ends
- FCA COBS 19 (transfers, nudge, pathways 19.10) — https://handbook.fca.org.uk/handbook/COBS/19/
- FCA investment pathways — https://www.fca.org.uk/consumers/investment-pathways
- Pension Wise (MoneyHelper) — https://www.moneyhelper.org.uk/en/pensions-and-retirement/pension-wise
- MoneyHelper pension scams — https://www.moneyhelper.org.uk/en/money-troubles/scams/how-to-spot-a-pension-scam
- FCA ScamSmart — https://www.fca.org.uk/scamsmart
- The Pensions Regulator — https://www.thepensionsregulator.gov.uk/
- The Pensions Ombudsman — https://www.pensions-ombudsman.org.uk/
- Scottish income tax — https://www.gov.uk/scottish-income-tax
- ICO right of access / breaches — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/right-of-access/what-should-we-consider-when-responding-to-a-request/ · https://ico.org.uk/for-organisations/report-a-breach/personal-data-breach/personal-data-breaches-a-guide/
- DPA 2018 Sch 2 — https://www.legislation.gov.uk/ukpga/2018/12/schedule/2/part/1/crossheading/crime-and-taxation-general
- FCA DISP 1.6 / 2.8 / PS25/19 — https://handbook.fca.org.uk/handbook/disp1/disp1s6 · https://handbook.fca.org.uk/handbook/disp2/disp2s8 · https://www.fca.org.uk/publications/consultation-papers/ps25-19-improving-complaints-reporting-process
- FCA FG21/1 — https://www.fca.org.uk/publications/finalised-guidance/guidance-firms-fair-treatment-vulnerable-customers
- OPG100 / Use an LPA — https://www.gov.uk/government/publications/find-out-if-someone-has-a-registered-attorney-or-deputy · https://www.gov.uk/use-lasting-power-of-attorney
- Tell Us Once / DNS — https://www.gov.uk/after-a-death/organisations-you-need-to-contact-and-tell-us-once · https://www.deathnotificationservice.co.uk/
- OFSI / NCA SARs — https://www.gov.uk/government/publications/financial-sanctions-general-guidance/uk-financial-sanctions-general-guidance · https://www.nationalcrimeagency.gov.uk/what-we-do/crime-threats/money-laundering-and-illicit-finance/suspicious-activity-reports
- FSCS pensions — https://www.fscs.org.uk/what-we-cover/pensions/

---

# PART III — RAG ASSETS (Retirement Account)

## III.1 Glossary
*meta: doc=03-PEN | sec=III.1 | aud=all | type=glossary | data=mixed*
**RAS** — relief at source (80% paid, 20% reclaimed). **Net pay** — pre-tax deduction method (occupational). **Salary sacrifice** — employer pays the given-up salary as a contribution (NI saving). **AA** — annual allowance £60,000. **Taper** — AA reduction for high earners (£260k/£360k). **MPAA** — £10,000 cap after flexible access. **Carry-forward** — three prior years' unused AA. **PCLS** — tax-free lump sum (≤25%, LSA-capped). **LSA/LSDBA** — £268,275 / £1,073,100 caps. **FP2016/IP2016** — transitional protections raising the caps. **TTFAC** — transitional tax-free amount certificate (irrevocable). **FAD** — flexi-access drawdown. **UFPLS** — 25/75 lump sum, MPAA trigger. **Investment pathways** — four non-advised drawdown options (COBS 19.10). **OMO** — open market option (shop around for annuities). **Small pot** — ≤£10,000, ×3, no MPAA trigger. **NMPA** — 55, 57 from 2028. **Nominee/successor** — cascade drawdown beneficiaries. **EoW** — expression of wishes. **Scheme pays** — AA charge settled from the fund.

## III.2 FAQ — customer layer
*meta: doc=03-PEN | sec=III.2 | aud=customer | type=faq | data=mixed*
**Q: I paid £8,000 — why does my account show £10,000?** RAS: we reclaim 20% from HMRC; higher-rate taxpayers claim more via Self Assessment (§3.4).
**Q: Can I take some cash at 55 and keep paying in?** Yes — PCLS-only doesn't cap contributions, but any taxable income (drawdown income or UFPLS) triggers the £10,000 MPAA (§4.3, §9.1–9.3).
**Q: Why was my first withdrawal taxed so heavily?** Emergency month-1 code; reclaim via P55/P53Z/P50Z or wait for HMRC reconciliation (§9.8).
**Q: I live in Scotland — different tax?** Yes on pension income (Scottish rates/PAYE); RAS still adds 20%, and intermediate-rate savers claim an extra 1% (§12).
**Q: Do I have to buy my annuity from you?** No — the open market option lets you shop around; enhanced rates may pay more (§9.4).
**Q: What happens to my pension when I die?** Before 75: usually tax-free to beneficiaries; 75+: taxed as their income; from April 2027 unused funds count for IHT (spouse/charity exempt) (§9.6–9.7).

## III.3 FAQ — back office / ops layer
*meta: doc=03-PEN | sec=III.3 | aud=back_office | type=faq | data=mixed*
**Q: Member with FP2016 wants to restart contributions here — impact?** Contributions after 5 April 2016 void FP2016 — warn and signpost advice before accepting (§4.6, §II.6.10).
**Q: £45,000 DB transfer-in with no advice evidence?** ≥£30,000 safeguarded requires regulated advice — do not proceed without it (§6, §II.6.10).
**Q: Cold-called member insists on transferring to an overseas "high-return" scheme?** Red-flag pattern → pause, safeguarding referral, potential refusal; document everything (§II.12).
**Q: Which death-benefit route keeps funds in the wrapper for grandchildren?** Nominee then successor drawdown — cascade rules and EoW quality (§9.7, §II.9).
**Q: PCLS request where prior benefits were taken in 2019?** Check for a TTFAC / apply the standard transitional deduction before paying (§4.6, §II.8.2).

## III.4 Specimen policy record (SYNTHETIC — a reserved number, never a customer)
*meta: doc=03-PEN | sec=III.4 | aud=all | type=sample_record | data=fictional*
`policy_no: RA-77103428` · `product: Retirement Account (core tier)` · `status: in force, accumulating` · `member: Kappa Quasar 58` · `dob: 1971-06-18` · `address: 22 Gnomon Rise, Fixture Vale (registered)` · `scottish_taxpayer: yes (S-code)` · `fund_value: £212,400` · `contributions: member £600/mo net + employer £300/mo gross` · `funds: 70% Target-Date 2036, 30% Global Index (AMC 0.22%)` · `MPAA: not triggered` · `protections: none; TTFAC: n/a` · `target_retirement_age: 60` · `EoW: spouse Vector Quasar 61 100% (signed 2024-02-10)` · `transfers_in: 2024-08 £58,000 from a workplace scheme (scam-DD passed; no safeguarded benefits)` · `adviser_LOA: none` · `bank_last4: 8830` · `vulnerability_flag: none` · `recent: 2026-06-30 contribution increase to £600; 2026-04-06 annual statement issued` · `open_cases: none`.
**This is a specimen, not a customer.** It is a worked illustration of a completed Retirement Account record, printed here so the benefit-route and annual-allowance mechanics can be taught against a filled-in example. Its policy number comes from the block reserved for specimens — eight digits at or above 20,100,000 — which the book cannot issue to anybody, so no specimen can ever collide with a real policy. A live customer's record would never appear in a product manual; this one is safe to print precisely because there is nobody behind it.

## III.5 Worked case walkthrough — first UFPLS with emergency tax, then a scam-flagged transfer attempt
*meta: doc=03-PEN | sec=III.5 | aud=all | type=case_study | data=fictional (rules real)*
Kappa (RA-77103428), now 55, requests a **£20,000 UFPLS**. EV forced (pension access, §II.3). Sequence (§II.8.2): NMPA met; no protections/TTFAC; risk warnings + **Pension Wise nudge** delivered and logged; **irreversibility + MPAA warning** given — she proceeds. £5,000 tax-free; £15,000 taxed under an emergency S-code (Scottish rates §12) — agent signposts **P55** (§9.8). MPAA flag set (£10,000 future cap) — her £900/mo total contributions (£10,800/yr) now **breach the MPAA**: case raised, options letter sent (reduce contributions or scheme-pays the charge, §4.1/§4.3). Three weeks later an "adviser" cold-calls instructing a transfer to an overseas scheme promising 12% returns: unregistered firm + overseas investment + cold origin = **red flags** → transfer paused, safeguarding referral, member warned via ScamSmart script, `FC-` referral logged (§II.12). Cross-sources: this doc §4/§9/§II.8/§II.12 + Doc 4 (COBS 19, Consumer Duty) + Doc 5 §13/§20.

## III.6 Cross-source reasoning map (demo questions)
*meta: doc=03-PEN | sec=III.6 | aud=all | type=routing | data=mixed*
1. "Scottish member takes drawdown income — which rates hit the income and which relief applies to ongoing saving?" → §12 + §3.4 + §9.8 (three-hop). 2. "Can Kappa's husband keep the fund invested if she dies at 73, and what if he then dies at 79?" → §9.6 + §9.7 cascade (two-death reasoning). 3. "Member with IP2016 asks their maximum tax-free cash" → §4.5 + §4.6. 4. "£40,000 single contribution from a client with £250,000 income" → §4.1 + §4.2 taper + §II.7 AML. 5. "Transfer out to an unregulated overseas scheme" → §II.6.10 + §II.12 + §13 (OTC) + Doc 4 B6. Complexity tier: HIGH — use for multi-constraint reasoning demos.

## III.7 Trust stress-test case — bypass trust death claim straddling the 2027 rules
*meta: doc=03-PEN | sec=III.7 | aud=all | type=case_study | data=fictional (rules real)*
Kappa (RA-77103428, §III.4) updates her EoW in 2026 to nominate the **Quasar Family Bypass Trust** (pilot trust, £10, trustees Vector + her brother). Eval scenario A — **she dies in January 2027, aged 55**: pre-75 and pre-6-April-2027 → lump sum to the trust **income-tax-free** within two years, LSDBA-tested; **no** pension-IHT charge (old rules); trust becomes **registrable on funding** (TRS URN within 90 days); relevant-property clock starts (§14.2). Eval scenario B — **she dies in June 2027**: identical facts, but the fund now sits **in her estate for IHT first** (§14.3); paying to the bypass trust is **not** spouse-exempt, whereas a direct payment to Vector would be → the AI must surface the changed trade-off, the PR/IHT coordination duty, and an advice signpost — not a recommendation. Same question, two dates, two different correct answers: the sharpest **temporal-reasoning eval** in the knowledge base, testing date-awareness, `data=real (not yet in force)` flags, and guardrail behaviour together.

---
*End of Document 3 v2.1. Firm-wide regulation: Document 4. Cross-product master procedures, data dictionary and intent routing: Document 5. Evals, observability and change management: Document 6.*
