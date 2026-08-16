"use strict";
/* CalmLine console — the caller screen (v4 phase 3, reshaped by D-CL-114).
 *
 * Search-first: one box, policy number or policyholder name. The verification
 * panel then shows the handler what the record holds — the handler ASKS, the
 * caller states, the handler ticks what they got right. Three of four passes,
 * and the server enforces that threshold again on its side.
 *
 * The RECORD stays absent from the page until verification passes. Not
 * blurred, not greyed: the server returns 428, so there is nothing to blur.
 * What IS here pre-pass is the handler's own panel — held details and
 * authority holders — which is the point of the redesign: a handler who
 * cannot see the details cannot judge whether the caller's words match them.
 *
 * Split from console.js at the 300-line rule; the authority cards live in
 * console-authority.js for the same reason. */

let CN_REF = null, VERIFICATION_ID = null, CHECKS = [], AUTHORITIES = null;

const GATE_LABELS = {
  policy_no: "Policy number",
  name_dob: "Full name and date of birth",
  address_or_bank: "Registered address — or the last 4 digits of the account",
  memorable: "Memorable item",
};
const NEED = 3;   /* 05-OPS:3.2 — three of four; the server holds the same line */

/* ── find the policy: number or name ──────────────────────────────────── */
async function findPolicy(query) {
  $("foBody").innerHTML = `<div class="empty" aria-busy="true">Searching…</div>`;
  const r = await api("GET",
    "/api/policies/search?q=" + encodeURIComponent(query));
  if (!r.ok) {
    $("foBody").innerHTML = `<div class="empty"><b>Search failed.</b><br>Try again.</div>`;
    return;
  }
  const found = r.data.matches || [];
  if (!found.length) {
    $("foBody").innerHTML = `<div class="empty">
      <b>No policy or policyholder matching “${esc(query)}”.</b><br>
      A fragment is enough — part of the number, or part of the name.</div>`;
    return;
  }
  if (found.length === 1) { beginContact(found[0].policy_no); return; }
  renderMatches(query, r.data);
}

function renderMatches(query, data) {
  const rows = data.matches.map(m => `
    <button class="result-row" onclick="beginContact('${esc(m.policy_no)}')">
      <span class="mono">${esc(m.policy_no)}</span>
      <span class="result-holder">${esc(m.holder)}</span>
      <span class="pill">${esc(m.product)}</span>
      <span class="badge ${m.status === "in_force" ? "b-ok" : "b-warn"}"><span class="dot"></span>${esc(m.status)}</span>
    </button>`).join("");
  const dropped = data.total - data.matches.length;
  $("foBody").innerHTML = `
    <section class="card" aria-labelledby="match-h">
      <h3 id="match-h">${data.total} matches for “${esc(query)}” — pick the caller's policy</h3>
      <div class="result-list">${rows}</div>
      ${dropped > 0 ? `<p class="result-note">Showing ${data.matches.length} of ${data.total} — narrow the search to see the rest.</p>` : ""}
    </section>`;
}

/* ── a caller is on the line ──────────────────────────────────────────── */
async function beginContact(policyNo) {
  CN_REF = null; VERIFICATION_ID = null; CHECKS = []; AUTHORITIES = null;
  $("foBody").innerHTML = `<div class="empty" aria-busy="true">Opening the contact…</div>`;

  const opened = await api("POST", "/api/interaction/open", {policy_no: policyNo});
  if (!opened.ok) { gateError(policyNo); return; }
  CN_REF = opened.data.cn_ref;

  const presented = await api("POST", "/api/verify",
    {cn_ref: CN_REF, policy_no: policyNo});
  if (!presented.ok) { gateError(policyNo); return; }
  CHECKS = presented.data.checks || [];
  AUTHORITIES = presented.data.authorities || null;
  renderGate(policyNo);
}

function gateError(policyNo) {
  $("foBody").innerHTML = `<div class="empty"><b>No policy ${esc(policyNo)} on file.</b><br>
    Check the number and try again — nothing has been disclosed.</div>`;
}

/* ── the verification panel: pre-filled, tick what the caller gets right ── */
function renderGate(policyNo, banner) {
  const rows = CHECKS.map(chk => `
    <li class="gate-q">
      <label class="gate-row">
        <input type="checkbox" class="gate-tick" data-kind="${esc(chk.kind)}"
               onchange="onGateTick()">
        <div class="gate-body">
          <div class="gate-q-head">
            <span class="gate-label">${esc(GATE_LABELS[chk.kind] || chk.kind)}</span>
            ${chk.held.some(f => f.ask_only)
              ? `<span class="badge b-warn"><span class="dot"></span>ask — never read out</span>` : ""}
            <span class="clause">${esc(chk.source)}</span>
          </div>
          <p class="gate-prompt">“${esc(chk.prompt)}”</p>
          <div class="held-grid">
            ${chk.held.map(f => `<span class="held-field">
              <span class="held-label">${esc(f.label)}</span>
              <span class="held-value${f.mono ? " mono" : ""}">${esc(f.value)}</span>
            </span>`).join("")}
          </div>
        </div>
      </label>
    </li>`).join("");

  $("foBody").innerHTML = `
    <section class="card gate" aria-labelledby="gate-h">
      <h3 id="gate-h">Verify the caller <span class="clause">05-OPS:3.2</span></h3>
      <p class="gate-intro">
        The record's details are below — the caller must state them.
        <b>Ask</b> each question, then tick what they get right:
        <b>${NEED} of ${CHECKS.length}</b> passes. The full record opens only
        after that. Contact <span class="mono">${esc(CN_REF)}</span>.
      </p>
      ${banner || ""}
      <ol class="gate-list">${rows}</ol>
      <div class="gate-actions">
        <button class="btn btn-primary" id="gateConfirm" onclick="confirmGate('${esc(policyNo)}')" disabled>
          Confirm verification →
        </button>
        <button class="btn" id="gateRefuse" onclick="confirmGate('${esc(policyNo)}')">
          Cannot verify — record it
        </button>
        <span class="gate-count" id="gateCount" aria-live="polite"></span>
      </div>
      <p class="gate-foot">You confirm; the system records — every tick lands in the
        audit under your name. A failed attempt is recorded too: refusing correctly
        is the product working.</p>
    </section>
    ${authoritiesCard()}
    ${thirdPartyPanel(policyNo)}`;
  onGateTick();
}

function onGateTick() {
  const ticked = collectTicks().length;
  const btn = $("gateConfirm");
  if (btn) btn.disabled = ticked < NEED;
  // The failure path must stay reachable: a caller who cannot answer is
  // RECORDED as failed (05-OPS:3.5), not abandoned by a stuck button.
  const refuse = $("gateRefuse");
  if (refuse) refuse.disabled = ticked >= NEED;
  const count = $("gateCount");
  if (count) count.textContent = ticked >= NEED
    ? `${ticked} of ${CHECKS.length} confirmed — ready`
    : `${ticked} of ${CHECKS.length} confirmed — ${NEED} needed to pass`;
}

function collectTicks() {
  return Array.from(document.querySelectorAll(".gate-tick:checked"))
    .map(el => el.dataset.kind);
}

async function confirmGate(policyNo) {
  const btn = $("gateConfirm");
  btn.disabled = true; $("gateRefuse").disabled = true;
  btn.textContent = "Recording…";
  const r = await api("POST", "/api/verify",
    {cn_ref: CN_REF, policy_no: policyNo, confirmed: collectTicks()});
  if (!r.ok) { btn.textContent = "Confirm verification →"; onGateTick(); return; }

  if (r.data.outcome === "passed") {
    VERIFICATION_ID = r.data.verification_id;
    openRecord(policyNo);
    return;
  }
  renderGate(policyNo, cannotVerifyBanner(r.data.route));
  toast("Not verified — nothing disclosed to the caller.");
}

/* 05-OPS:3.5 — say nothing about WHICH check failed. Correction is itself
   disclosure, so the panel repeats the server's route verbatim. */
function cannotVerifyBanner(route) {
  if (!route) return "";
  const alts = (route.alternatives || []).map(a => `<li>${esc(a)}</li>`).join("");
  return `<div class="verdict warn gate-fail" role="status">
    <b>Not verified — disclose nothing.</b>
    <p class="gate-say">“${esc(route.say)}”</p>
    <p class="gate-alt-head">Offer the secure route:</p>
    <ul class="gate-alts">${alts}</ul>
    <span class="clause">${esc(route.source)}</span>
  </div>`;
}

/* ── the record, once the gate has opened ─────────────────────────────── */
async function openRecord(policyNo) {
  $("foBody").innerHTML = `<div class="empty" aria-busy="true">Opening the record…</div>`;
  const q = "?cn_ref=" + encodeURIComponent(CN_REF);
  const [rec, hist] = await Promise.all([
    api("GET", "/api/policy/" + policyNo + q),
    api("GET", "/api/policy/" + policyNo + "/history" + q)]);
  if (!rec.ok || !rec.data || rec.data.found === false) { gateError(policyNo); return; }
  POLICY = policyNo; CHAT = [];
  renderFrontOffice(rec.data, (hist.data && hist.data.entries) || []);
}

/* The strip that says WHICH verification unlocked this page. */
function verifiedStrip() {
  return `<div class="verified-strip" role="status">
    <span class="badge b-ok"><span class="dot"></span>Verified</span>
    <span>unlocked by <b class="mono">${esc(VERIFICATION_ID || "—")}</b></span>
    <span>on contact <b class="mono">${esc(CN_REF || "—")}</b></span>
    <button class="linkbtn" onclick="endContact()">End contact</button>
  </div>`;
}

function endContact() {
  CN_REF = null; VERIFICATION_ID = null; POLICY = null; CHAT = [];
  CHECKS = []; AUTHORITIES = null;
  $("foBody").innerHTML = `<div class="empty"><b>Contact closed.</b><br>
    The verification expired with it — the next caller starts again.</div>`;
  toast("Contact closed; verification expired.");
}
