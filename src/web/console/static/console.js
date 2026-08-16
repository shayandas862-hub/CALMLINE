"use strict";
/* CalmLine console — front + back office, wired to the offline API. */

let ROLE = null, POLICY = null, CASE_ID = null, CHAT = [];

async function api(method, path, body) {
  const r = await fetch(path, {
    method, credentials: "same-origin",
    headers: body ? {"Content-Type": "application/json"} : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null; try { data = await r.json(); } catch (e) {}
  return {ok: r.ok, status: r.status, data};
}
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c =>
  ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const $ = id => document.getElementById(id);
function toast(msg) { const t = $("toast"); t.textContent = msg; t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2200); }

function show(view) {
  ["login", "fo", "bo", "ops"].forEach(v => $("view-" + v).classList.toggle("hidden", v !== view));
  $("topbar").classList.toggle("hidden", view === "login");
}

async function login(role) {
  const r = await api("POST", "/api/login", {role});
  if (!r.ok) return toast("Login failed");
  ROLE = role;
  $("roleChip").textContent = role.replace("_", " ");
  if (role === "front_office") { show("fo"); }
  else if (role === "ops") { show("ops"); loadOps(); }
  else { show("bo"); loadQueue(); }
}
function logout() { ROLE = null; POLICY = null; CASE_ID = null; CHAT = [];
  CN_REF = null; VERIFICATION_ID = null; CHECKS = []; AUTHORITIES = null;
  show("login"); }

/* ── FRONT OFFICE ─────────────────────────────────────────── */
async function lookup() {
  const q = $("polInput").value.trim();
  if (!q) return;
  // The record is never fetched first. Search finds the policy, a contact
  // opens, the caller is verified — only then does the record reach the page.
  findPolicy(q);
}

function renderFrontOffice(rec, entries) {
  const p = rec.policy, h = rec.holder;
  const ledger = entries.length ? entries.map(e => `<tr>
      <td>${esc(e.at.slice(0, 10))}</td><td>${esc(e.kind)}</td>
      <td class="${e.signed_pence < 0 ? "neg" : "pos"}">${esc(e.amount)}</td>
      <td><b>${esc(e.balance_after)}</b></td><td style="color:var(--text-3)">${esc(e.reason)}</td>
    </tr>`).join("") : `<tr><td colspan="5" style="color:var(--text-3)">No cash movements — this product has no cash value.</td></tr>`;

  $("foBody").innerHTML = verifiedStrip() + `<div class="fo-grid">
    <div>
      <div class="card">
        <h3>Policy record <span class="badge b-ok" style="margin-left:6px"><span class="dot"></span>${esc(p.status)}</span></h3>
        <dl class="fields">
          <div class="f"><dt>Policyholder</dt><dd>${esc(h ? h.name : "—")}<span class="tag-syn">synthetic</span></dd></div>
          <div class="f"><dt>Policy no</dt><dd class="mono">${esc(POLICY)}</dd></div>
          <div class="f"><dt>Product</dt><dd>${esc(p.product)}</dd></div>
          <div class="f"><dt>Date of birth</dt><dd class="mono">${esc(h ? h.dob : "—")}</dd></div>
          <div class="f"><dt>Sum assured</dt><dd><b>${esc(p.sum_assured)}</b></dd></div>
          <div class="f"><dt>Current value</dt><dd class="val">${esc(rec.current_value)}</dd></div>
          <div class="f"><dt>Premium</dt><dd><b>${esc(p.premium)}</b></dd></div>
        </dl>
      </div>
      ${authoritiesCard()}
      <div class="card" style="margin-top:14px"><h3>Transaction history — the ledger</h3>
        <div class="tbl-wrap"><table><thead><tr><th>Date</th><th>Type</th><th>Amount</th><th>Balance</th><th>Reason</th></tr></thead>
        <tbody>${ledger}</tbody></table></div>
      </div>
      ${p.can_pay_cash_out ? `<div class="card" style="margin-top:14px;border-color:rgba(232,180,76,.3)">
        <h3>Raise a case</h3>
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <span style="color:var(--text-2);font-size:12.5px">Caller wants a partial surrender of</span>
          <input class="pol" id="raiseAmt" value="£5,000" style="width:100px">
          <button class="btn btn-primary" onclick="raiseCase()">Raise case →</button>
        </div>
        <p style="color:var(--text-3);font-size:11.5px;margin:10px 0 0">Nothing moves here — it runs a compliance pre-check and lands in the back office for a human.</p>
      </div>` : ""}
    </div>
    <div class="card" style="background:var(--surface-2)">
      <h3>CalmLine agent — ask in plain English</h3>
      <div class="chat" id="chat"></div>
      <div class="chat-input">
        <input id="chatInput" placeholder="e.g. how do they claim?" onkeydown="if(event.key==='Enter')askAgent()">
        <button class="btn btn-primary" onclick="askAgent()">Send</button>
      </div>
    </div>
  </div>`;
  renderChat();
}

function renderChat() {
  const el = $("chat"); if (!el) return;
  el.innerHTML = CHAT.map(m => m.role === "u"
    ? `<div class="msg u"><span class="who">Handler</span>${esc(m.text)}</div>`
    : `<div class="msg a"><span class="who">CalmLine</span>${m.html}</div>`).join("");
  el.scrollTop = el.scrollHeight;
}

async function askAgent() {
  if (!POLICY) return toast("Look up a policy first.");
  const inp = $("chatInput"), msg = inp.value.trim(); if (!msg) return;
  inp.value = ""; CHAT.push({role: "u", text: msg}); renderChat();
  const r = await api("POST", "/api/agent",
    {policy_no: POLICY, message: msg, cn_ref: CN_REF});
  CHAT.push({role: "a", html: agentReply(r.data)}); renderChat();
}

// How a citation must be attributed, by the style retrieval gave it. A style we
// don't recognise is labelled unknown rather than guessed — the same stance the
// provenance parser takes (AD-CL-027).
const CITE_LABELS = {
  cite_source: "cites source",
  aldercrest_standard: "operating standard",
  mixed_explain: "mixed — explain",
  effective_date_required: "not yet in force",
};

// Which path answered, said plainly. A keyword answer shown as the agent would
// misrepresent the product in the one direction that flatters it.
function modeChip(out) {
  const live = out.mode === "live";
  const label = live ? `agent · ${esc(out.model || "")}` : "offline fallback";
  return `<span class="badge ${live ? "b-ok" : "b-warn"}"><span class="dot"></span>${label}</span>`;
}

function citationChip(c) {
  const label = CITE_LABELS[c.citation_style] || "style unknown";
  const note = c.effective_note ? ` — ${esc(c.effective_note)}` : "";
  return `<span class="clause">${esc(c.chunk_id)}</span>` +
         `<span class="pill">${esc(label)}${note}</span>`;
}

function liveReply(out) {
  const r = out.reply || {};
  const pill = t => `<span class="pill">${esc(t)}</span>`;
  // An abstention is a success state: the agent declining to answer from
  // nowhere is the product working, not an error to apologise for.
  const body = r.abstained
    ? `<span class="badge b-ok"><span class="dot"></span>Declined — ${esc(r.abstention_reason)}</span>`
    : esc(r.answer_text);
  const chips = [
    ...(r.citations || []).map(citationChip),
    ...(r.tools_used || []).map(t => pill(`used: ${t}`)),
    ...(r.guardrail_events || []).map(pill),
    modeChip(out),
  ].join(" ");
  return `${body}<div class="usedtool chiprow">${chips}</div>`;
}

function agentReply(out) {
  if (!out) return "Something went wrong.";
  if (out.mode === "live") return liveReply(out);
  const used = `<div class="usedtool chiprow"><span class="pill">used: ${esc(out.tool)}</span>${modeChip(out)}</div>`;
  const res = out.result || {};
  if (out.tool === "retrieve_clause") {
    if (!res.found || !res.clauses.length) return "I can't answer that from the policy wordings — I'd refuse and escalate rather than guess." + used;
    const c = res.clauses[0];
    return `${esc(c.text)} <div class="usedtool chiprow">` +
           citationChip({chunk_id: c.chunk_id, citation_style: c.citation_style}) +
           `<span class="pill">used: retrieve_clause</span>${modeChip(out)}</div>`;
  }
  if (out.tool === "get_transaction_history")
    return `Value as at ${esc(res.as_at)} is <b>${esc(res.value)}</b>, across ${res.entries ? res.entries.length : 0} recorded movement(s).` + used;
  if (out.tool === "lookup_policy_record")
    return `${esc(res.holder ? res.holder.name : "")} — current value <b>${esc(res.current_value)}</b>.` + used;
  if (out.tool === "raise_case")
    return `Case <b>${esc(res.case_id || "")}</b> raised to the back office.` + used;
  return JSON.stringify(res) + used;
}

async function raiseCase() {
  if (!POLICY) return toast("Look up a policy first.");
  const raw = ($("raiseAmt").value || "").replace(/[^0-9.]/g, "");
  const amount_pence = Math.round((parseFloat(raw) || 5000) * 100);
  const r = await api("POST", "/api/cases/raise",
    {policy_no: POLICY, request: "partial surrender", priority: "high",
     amount_pence, cn_ref: CN_REF});
  if (r.ok) toast(`Case ${r.data.case_id} raised — switch to the Back office to review it.`);
  else toast("Could not raise the case.");
}

/* ── BACK OFFICE ──────────────────────────────────────────── */
function slaText(secs) {
  if (secs == null) return "—";
  if (secs < 0) return "overdue";
  const h = Math.floor(secs / 3600), m = Math.floor((secs % 3600) / 60);
  return h >= 24 ? Math.floor(h / 24) + "d " + (h % 24) + "h" : h + "h " + m + "m";
}
async function loadQueue() {
  const r = await api("GET", "/api/cases");
  const cases = r.data || [];
  const el = $("queueBody");
  if (!cases.length) { el.innerHTML = `<div class="empty">No cases yet — raise one from the front office.</div>`; return; }
  el.innerHTML = `<div class="tbl-wrap"><table>
    <thead><tr><th>Priority</th><th>Case</th><th>Policy</th><th>Request</th><th>SLA left</th><th>AI rec</th></tr></thead>
    <tbody>${cases.map(c => `<tr class="rowbtn" aria-selected="${c.case_id === CASE_ID}" onclick="openCase('${c.case_id}')">
      <td class="prio-${esc(c.priority)}">${esc(c.priority)}</td>
      <td class="mono">${esc(c.case_id)}</td><td class="mono">${esc(c.policy_no)}</td>
      <td>${esc(c.request)}</td><td class="mono">${slaText(c.sla_seconds_left)}</td>
      <td>${c.recommendation === "proceed"
        ? '<span class="badge b-ok"><span class="dot"></span>proceed</span>'
        : '<span class="badge b-warn"><span class="dot"></span>do not proceed</span>'}</td>
    </tr>`).join("")}</tbody></table></div>`;
}

async function openCase(id) {
  CASE_ID = id; loadQueue();
  const r = await api("GET", "/api/cases/" + id);
  renderCaseDetail(r.data);
}

function renderCaseDetail(d) {
  if (!d) return;
  const checks = d.checklist.map(it => `<div class="check">
    <span class="ci ${it.verdict === "pass" ? "pass" : "fail"}">${it.verdict === "pass" ? "✓" : "✕"}</span>
    <div>${esc(it.requirement)}</div><span class="clause">${esc(it.clause_ref)}</span></div>`).join("");
  const proceed = d.recommendation === "proceed", done = d.status === "completed";
  const banner = proceed
    ? `<div class="verdict ok"><b>AI recommendation: proceed</b><br>Every requirement is evidenced and cited. The release still needs your click — the AI never moves money.</div>`
    : `<div class="verdict warn"><b>AI recommendation: do not proceed</b><br>A requirement is not met. This case can't be approved until it is — that block is the safety behaviour working.</div>`;
  const btn = done ? `<button class="btn" disabled>Released ✓</button>`
    : proceed ? `<button class="btn btn-ok" onclick="approve('${d.case_id}')">Approve &amp; release (mock) →</button>`
    : `<button class="btn" disabled>Approve — blocked</button>`;
  const audit = (d.audit && d.audit.length) ? `<div class="card" style="margin-top:14px"><h3>Audit chain</h3>
    <ul class="timeline">${d.audit.map(a => `<li><span class="ev">●</span> ${esc(a.event)} — ${esc(a.actor)} @ ${esc(a.at.slice(11, 16))}</li>`).join("")}</ul>
    <div class="rec-strip"><span>policy <b style="color:var(--text)">${esc(d.policy_no)}</b></span>
      <span>current value <b class="val">${esc(d.record.current_value)}</b></span></div></div>` : "";

  $("caseBody").innerHTML = `<div class="card">
    <h3>Case review <span class="clause">${esc(d.case_id)}</span></h3>
    <p style="margin:0 0 3px"><b>${esc(d.request)}</b> · ${esc(d.policy_no)} · ${esc(d.record.holder ? d.record.holder.name : "")}</p>
    <p style="color:var(--text-2);margin:0 0 12px">Current value <span class="val">${esc(d.record.current_value)}</span></p>
    <div class="section-label" style="margin:6px 0 4px">Compliance pre-check — every line cites a clause</div>
    ${checks}${banner}
    <div style="margin-top:14px;display:flex;gap:12px;align-items:center">${btn}
      <span style="color:var(--text-3);font-size:11.5px">Accountability stays with the named reviewer.</span></div>
  </div>${audit}`;
}

async function approve(id) {
  const r = await api("POST", "/api/cases/" + id + "/approve");
  if (r.ok) { toast("Approved — payment released (mock), ledger updated."); renderCaseDetail(r.data); loadQueue(); }
  else if (r.status === 409) toast("Blocked: this case can't be approved.");
  else toast("Approval failed.");
}
