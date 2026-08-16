"use strict";
/* CalmLine console — who may speak on a policy (05-OPS §5).
 *
 * Two cards. The first renders the standing the record already holds —
 * policyholder, recorded authorities, adviser LOA, trust — from the present
 * payload, so the handler sees who may speak before deciding anything. The
 * second is the interactive check for a third party's claim, which is the
 * enforcement path: authority verified AND request within scope, or refused.
 *
 * Split from console-verify.js at the 300-line rule. */

const AUTH_BADGE = {active: "b-ok", expired: "b-bad", revoked: "b-bad"};

function authoritiesCard() {
  if (!AUTHORITIES) return "";
  const a = AUTHORITIES;
  const rows = [`<div class="auth-row">
      <span class="badge b-acc"><span class="dot"></span>policyholder</span>
      <span class="auth-name">${esc(a.holder.name)}</span>
      <span class="auth-note mono">${esc(a.holder.party_id)}</span>
    </div>`];
  (a.records || []).forEach(rec => rows.push(`<div class="auth-row">
      <span class="badge ${AUTH_BADGE[rec.status] || "b-warn"}"><span class="dot"></span>${esc(rec.status)}</span>
      <span class="auth-name">${esc(rec.name)}</span>
      <span class="pill">${esc(rec.type)}</span>
      ${(rec.scope || []).map(s => `<span class="pill">${esc(s)}</span>`).join("")}
    </div>`));
  if (a.adviser) rows.push(`<div class="auth-row">
      <span class="badge b-acc"><span class="dot"></span>adviser LOA</span>
      <span class="auth-name">${esc(a.adviser.firm)}</span>
      <span class="auth-note mono">FRN ${esc(a.adviser.frn)} · to ${esc(a.adviser.expiry)}</span>
      ${(a.adviser.scope || []).map(s => `<span class="pill">${esc(s)}</span>`).join("")}
    </div>`);
  if (a.trust) rows.push(`<div class="auth-row">
      <span class="badge b-acc"><span class="dot"></span>in trust</span>
      <span class="auth-name">${esc((a.trust.trustees || []).join(", ") || "no trustees recorded")}</span>
      <span class="pill">${esc(a.trust.kind)}</span>
    </div>`);
  const alone = !(a.records || []).length && !a.adviser && !a.trust;
  return `<section class="card" style="margin-top:14px" aria-labelledby="auth-h">
    <h3 id="auth-h">Who may speak on this policy <span class="clause">05-OPS:5.0</span></h3>
    <div class="auth-list">${rows.join("")}</div>
    ${alone ? `<p class="auth-note" style="margin:10px 0 0">Nobody but the policyholder holds authority on this record.</p>` : ""}
  </section>`;
}

/* ── the third-party path (05-OPS §5) ─────────────────────────────────── */
const THIRD_PARTY_TYPES = [
  ["LOA", "Financial adviser (Letter of Authority)"],
  ["LPA", "Attorney (Lasting Power of Attorney)"],
  ["EPA", "Attorney (Enduring Power of Attorney)"],
  ["deputy", "Court of Protection deputy"],
  ["PR", "Executor / personal representative"],
  ["trustee", "Trustee"],
  ["mandate", "Third-party mandate"],
];
const THIRD_PARTY_ACTIONS = [
  ["information", "Disclose information"],
  ["servicing", "Servicing change"],
  ["switches", "Fund switch"],
  ["withdrawals", "Withdrawal"],
  ["bank_change", "Change bank details"],
  ["claim_proceeds", "Receive proceeds"],
  ["trustee_change", "Change a trustee"],
];

function thirdPartyPanel(policyNo) {
  return `<details class="card third-party">
    <summary>The caller is not the policyholder <span class="clause">05-OPS:5.0</span></summary>
    <p class="gate-intro">Authority must be <b>verified</b> and the request must fall
      <b>within its scope</b>. Fail either and that instruction is refused.</p>
    <div class="tp-grid">
      <div class="gate-field">
        <label for="tpType">Claimed relationship</label>
        <select id="tpType">
          ${THIRD_PARTY_TYPES.map(([v, l]) =>
            `<option value="${v}">${esc(l)}</option>`).join("")}
        </select>
      </div>
      <div class="gate-field">
        <label for="tpAction">What are they asking for?</label>
        <select id="tpAction">
          ${THIRD_PARTY_ACTIONS.map(([v, l]) =>
            `<option value="${v}">${esc(l)}</option>`).join("")}
        </select>
      </div>
      <div class="gate-field">
        <label for="tpFirm">Firm (advisers)</label>
        <input id="tpFirm" autocomplete="off" placeholder="firm name as held">
      </div>
      <div class="gate-field">
        <label for="tpFrn">FRN / party id</label>
        <input id="tpFrn" autocomplete="off" placeholder="checked on the FCA Register">
      </div>
    </div>
    <div class="gate-actions">
      <button class="btn" onclick="checkAuthority('${esc(policyNo)}')">Check authority →</button>
    </div>
    <div id="tpResult" aria-live="polite"></div>
  </details>`;
}

async function checkAuthority(policyNo) {
  const claimed = $("tpType").value, action = $("tpAction").value;
  const frn = ($("tpFrn").value || "").trim();
  const r = await api("POST", "/api/authority/check", {
    cn_ref: CN_REF, policy_no: policyNo, claimed, action,
    firm: ($("tpFirm").value || "").trim(), frn, party_id: frn});
  if (!r.ok) { $("tpResult").innerHTML = ""; return; }
  const d = r.data;
  const sources = (d.sources || []).map(s => `<span class="clause">${esc(s)}</span>`).join(" ");
  $("tpResult").innerHTML = `<div class="verdict ${d.allowed ? "ok" : "warn"}">
    <span class="badge ${d.allowed ? "b-ok" : "b-bad"}"><span class="dot"></span>${
      d.allowed ? "Within authority" : "Refused"}</span>
    <p class="tp-reason">${esc(d.reason)}</p>
    ${d.remedy ? `<p class="tp-remedy"><b>What would make it acceptable:</b> ${esc(d.remedy)}</p>` : ""}
    ${d.customer_direct_route ? `<p class="tp-remedy">Offer the customer-direct route.</p>` : ""}
    <div class="chiprow">${sources}</div>
  </div>`;
}
