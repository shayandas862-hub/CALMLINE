"use strict";
/* CalmLine console — the BOARD CHAMBER: three lenses over /api/ops.

   The subject of this screen changed in v4 phase 5. It used to answer "how is
   the queue doing"; it now answers "is the AI behaving". Reuses api(), esc(),
   $(), slaText() from console.js.

   Three things here are honesty constraints rather than styling:

   1. A rate with no records behind it renders as "no data", never as 0%. The
      tile that reads perfectly on an empty store is the one that misleads
      hardest, so a no-data tile is visibly NOT REPORTING — dashed, dimmed, an
      em-dash where the number would be.
   2. The screen always says which model(s) its numbers describe. Two models
      averaged into one figure describe neither, so an unfiltered board holding
      both says so in warn tone.
   3. A zero is shown with the join that proves it. "gate bypass 0" on its own
      is a claim; "0, from 3 events examined, none offended" is evidence. */

let OPS = null, LENS = "safety", MODEL = null;

async function loadOps() {
  const q = MODEL ? "?model_id=" + encodeURIComponent(MODEL) : "";
  const r = await api("GET", "/api/ops" + q);
  if (!r.ok) { $("opsBody").innerHTML = `<div class="empty">Could not load the board.</div>`; return; }
  OPS = r.data; renderOps();
}
function setLens(l) { LENS = l; renderOps(); }

/* ── tiles ─────────────────────────────────────────────────────
   A metric arrives as {value, target, basis, tracked_never_targeted}. Which of
   the three states it is in is decided here, once, so no caller can render a
   null as a zero by accident. */
function metric(m, label, sub) {
  if (!m) return "";
  // A count of 0 over 0 records is a true number and a false reassurance. The
  // value still shows — it is the count — but the "at target" tick is withheld
  // until something was actually examined. "Nothing went wrong" and "nothing
  // was looked at" must never render the same, which is the whole reason every
  // metric carries its basis.
  const unexamined = !m.basis;
  const noData = m.value === null || m.value === undefined;
  const targeted = m.target !== null && m.target !== undefined;
  const met = targeted && !noData && !unexamined && m.value <= m.target;
  const missed = targeted && !noData && !met;
  const state = (noData || unexamined) ? "nodata" : (met ? "met" : missed ? "missed" : "");
  const tone = (noData || unexamined) ? "" : targeted ? (met ? "ok" : "bad") : "acc";

  let flag;
  if (noData) flag = `<span class="stat-flag nodata">◌ no data · nothing recorded</span>`;
  else if (unexamined)
    flag = `<span class="stat-flag nodata">◌ nothing examined yet</span>`;
  else if (met) flag = `<span class="stat-flag met">✓ at target (${esc(m.target)}) · ${esc(m.basis)} examined</span>`;
  else if (targeted) flag = `<span class="stat-flag missed">▲ target ${esc(m.target)}</span>`;
  else if (m.tracked_never_targeted)
    flag = `<span class="stat-flag untargeted">◇ tracked, never targeted</span>`;
  else flag = `<span class="stat-flag untargeted">· ${m.basis || 0} records</span>`;

  return `<div class="stat ${state}">
    <div class="stat-n ${tone}">${noData ? "—" : esc(fmt(m))}</div>
    <div class="stat-l">${esc(label)}</div>
    ${flag}
    ${sub ? `<div class="stat-sub">${esc(sub)}</div>` : ""}
  </div>`;
}

/* Counts stay counts; rates become percentages. The metric SAYS which it is —
   a rate of 0.0 and a count of 0 are the same number, and guessing between
   them renders "0" where it means "0%". */
function fmt(m) {
  return m.unit === "rate" ? Math.round(m.value * 100) + "%" : String(m.value);
}

function stat(n, label, tone, sub) {
  return `<div class="stat">
    <div class="stat-n ${tone || ""}">${esc(n)}</div>
    <div class="stat-l">${esc(label)}</div>
    ${sub ? `<div class="stat-sub">${esc(sub)}</div>` : ""}
  </div>`;
}

/* ── model attribution ─────────────────────────────────────────
   Always rendered. An unattributed number on a board where models get swapped
   is a number nobody can act on. */
function modelStrip(lens) {
  const models = lens.models || [];
  if (lens.model_id)
    return `<div class="model-strip"><span class="badge b-acc"><span class="dot"
      style="background:var(--accent)"></span>${esc(lens.model_id)}</span>
      <span>these numbers describe one model</span></div>`;
  if (models.length > 1)
    return `<div class="model-strip mixed">▲ mixed: ${esc(models.join(" + "))}
      — these numbers average ${models.length} models and describe none of them.
      Filter to one to read them.</div>`;
  if (models.length === 1)
    return `<div class="model-strip"><span class="mono">${esc(models[0])}</span>
      <span>every trace behind this board</span></div>`;
  return `<div class="model-strip none">no model has answered yet — the keyword
    path names none, by design</div>`;
}

function renderOps() {
  if (!OPS) { $("opsBody").innerHTML = `<div class="empty">No data.</div>`; return; }
  ["safety", "grounding", "operations"].forEach(l => {
    const t = $("tab-" + l); if (t) t.classList.toggle("active", l === LENS);
  });
  $("opsBody").innerHTML =
    LENS === "grounding" ? renderGrounding(OPS.grounding)
    : LENS === "operations" ? renderOperations(OPS.operations)
    : renderSafety(OPS.safety);
}

/* ── LENS 1 · safety & gates ───────────────────────────────── */
function renderSafety(s) {
  if (!s) return `<div class="empty">No safety data.</div>`;
  const g = s.gate_bypass || {};
  const types = Object.entries(s.guardrail_events_by_type || {});
  const chips = types.length
    ? types.map(([k, n]) => `<span class="pill">${esc(k)} · ${esc(n)}</span>`).join(" ")
    : `<span style="color:var(--text-3)">none recorded</span>`;

  return `${modelStrip(s)}
  <div class="ops-grid">
    ${metric(g, "gate bypass", "disclosures with no verification behind them")}
    ${metric(s.advice_boundary, "advice-boundary", "the agent staying out of advice")}
    ${pairedTile(s.abstention, s.correct_routing)}
    ${metric(s.containment, "containment", "share needing no handoff")}
    ${stat(s.queries, "queries traced", "acc", "every answer, both paths")}
  </div>
  <div class="card join-card">
    <h3>The join behind gate bypass</h3>
    ${offenders(g)}
    <p class="ops-note">A zero nobody can audit is a zero nobody should believe.
      Every gate event is walked in order; a pass recorded <em>after</em> a
      disclosure is counted as a bypass, not as cover for one.</p>
  </div>
  <div class="card" style="margin-top:14px">
    <h3>Guardrail events by type</h3>
    <div class="chiprow">${chips}</div>
    <p class="ops-note">Refusals and abstentions are the product working, not
      faults. They are counted here so the behaviour is visible, not so it can
      be driven down.</p>
  </div>`;
}

function offenders(g) {
  const rows = (g.offenders || []).map(o => `<tr>
      <td class="mono">${esc(o.seq)}</td><td class="mono">${esc(o.policy_no)}</td>
      <td class="mono">${esc(o.cn_ref || "—")}</td><td>${esc(o.actor)}</td>
      <td class="mono">${esc(o.at)}</td></tr>`).join("");
  if (!g.events_examined)
    // The vacuous audit: "none offended" out of nothing examined is not a
    // clean result, it is an absent one, and must not read as reassurance.
    return `<div class="empty">No gate events yet — nothing has been examined,
      so this is not yet evidence of anything.</div>`;
  if (!rows)
    return `<div class="join-clean"><span class="badge b-ok"><span class="dot"></span></span>
      ${esc(g.events_examined)} gate event(s) examined — none disclosed
      without a passed verification in scope.</div>`;
  return `<div class="tbl-wrap"><table><thead><tr><th>Seq</th><th>Policy</th>
    <th>Interaction</th><th>Actor</th><th>At</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

/* Abstention only means something beside routing — one tile, never two. */
function pairedTile(abst, routing) {
  if (!abst) return "";
  const pct = m => (m && m.value !== null && m.value !== undefined)
    ? Math.round(m.value * 100) + "%" : "—";
  const nod = !abst || abst.value === null || abst.value === undefined;
  return `<div class="stat paired ${nod ? "nodata" : ""}">
    <div class="paired-pair">
      <span class="stat-n ${nod ? "" : "acc"}">${esc(pct(abst))}</span>
      <span class="paired-join">abstained — of those,</span>
      <span class="stat-n ${nod ? "" : "ok"}">${esc(pct(routing))}</span>
      <span class="paired-join">routed correctly</span>
    </div>
    <div class="stat-l">abstention &amp; routing</div>
    <div class="stat-sub">Shown together because they are meaningless apart:
      abstaining is only good when the handoff was right.</div>
  </div>`;
}

/* ── LENS 2 · grounding & freshness ────────────────────────── */
function renderGrounding(g) {
  if (!g) return `<div class="empty">No grounding data.</div>`;
  const styles = Object.entries(g.citations_by_style || {});
  const chips = styles.length
    ? styles.map(([k, n]) => `<span class="clause">${esc(k)} · ${esc(n)}</span>`).join(" ")
    : `<span style="color:var(--text-3)">nothing cited yet</span>`;

  return `${modelStrip(g)}
  <div class="ops-grid">
    ${metric(g.stale_citations, "stale citations", "cited a version since superseded")}
    ${metric(g.filter_hit_rate, "filter hit rate", "queries that narrowed before ranking")}
    ${stat(g.citations_total, "citations made", "acc")}
    ${stat(g.corpus_clauses, "corpus clauses", "", "the retrievable knowledge base")}
  </div>
  <div class="card" style="margin-top:14px">
    <h3>Citations by provenance style</h3>
    <div class="chiprow">${chips}</div>
    <p class="ops-note">Style is read from the corpus, not from the model's
      output — the loop states what retrieval said, so this count cannot drift
      from the provenance rule it reports on.</p>
    <div class="rec-strip"><span>kb version
      <b style="color:var(--text)">${esc(g.kb_version || "—")}</b></span>
      <span>content hash of the corpus — it changes when the corpus does,
      and never when it does not</span></div>
  </div>`;
}

/* ── LENS 3 · operations & throughput (kept from v3) ───────── */
function renderOperations(o) {
  if (!o) return `<div class="empty">No operations data.</div>`;
  const bp = o.by_priority || {};
  const reconOk = o.ledgers_reconciled === o.ledgers_total;
  const rows = (o.queue || []).map(c => `<tr>
      <td class="prio-${esc(c.priority)}">${esc(c.priority)}</td>
      <td class="mono">${esc(c.case_id)}</td><td class="mono">${esc(c.policy_no)}</td>
      <td>${esc(c.request)}</td><td class="mono">${slaText(c.sla_seconds_left)}</td>
      <td>${c.recommendation === "proceed"
        ? '<span class="badge b-ok"><span class="dot"></span>proceed</span>'
        : '<span class="badge b-warn"><span class="dot"></span>do not proceed</span>'}</td>
    </tr>`).join("");
  return `<div class="ops-grid">
    ${stat(o.open, "open in queue", "acc")}
    ${stat(o.completed, "completed", "ok")}
    ${stat(o.overdue, "overdue", o.overdue ? "bad" : "")}
    ${stat(`${bp.high || 0} · ${bp.medium || 0} · ${bp.low || 0}`, "open by priority · H·M·L")}
    ${stat(o.human_approved, "human-approved commits", "ok", "money moves only by a human")}
    ${stat(o.funds_under_admin, "funds under administration", "ok", "Σ of every ledger")}
    ${stat(`${o.ledgers_reconciled} / ${o.ledgers_total}`, "ledgers reconciled",
           reconOk ? "ok" : "bad", "each balance recomputed from its own history")}
    ${stat(o.transactions_recorded, "transactions recorded")}
  </div>
  <div class="card" style="margin-top:14px"><h3>Open queue — most urgent first</h3>
    ${rows ? `<div class="tbl-wrap"><table><thead><tr><th>Priority</th><th>Case</th>
      <th>Policy</th><th>Request</th><th>SLA left</th><th>AI rec</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`
      : `<div class="empty">Queue is clear — nothing waiting.</div>`}
  </div>`;
}
