"""Public resident UI for Townlight Zoning."""

from __future__ import annotations


def render_public_lookup_page() -> str:
    """Render the browser-usable public Townlight Zoning lookup page."""

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>Townlight Zoning Resident Lookup</title>
<style>
  :root {
    --bg: #f6f7f2;
    --panel: #ffffff;
    --ink: #16201b;
    --muted: #58635d;
    --line: #cfd8d1;
    --field: #f9faf8;
    --primary: #1e684f;
    --primary-dark: #154836;
    --warn: #9b4e2e;
    --amber: #ad8127;
    --blue: #355f8a;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: "Segoe UI", Arial, sans-serif;
  }
  a { color: var(--primary-dark); }
  .skip-link {
    position: absolute;
    left: 1rem;
    top: -4rem;
    z-index: 10;
    background: var(--ink);
    color: #fff;
    padding: .7rem 1rem;
    border-radius: 8px;
  }
  .skip-link:focus { top: 1rem; }
  header, main, footer {
    width: min(1180px, calc(100% - 32px));
    margin: 0 auto;
  }
  header {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 1rem;
    align-items: end;
    padding: 28px 0 18px;
    border-bottom: 1px solid var(--line);
  }
  h1, h2, h3, p { margin-top: 0; }
  h1 {
    margin-bottom: .35rem;
    font-size: clamp(1.9rem, 4vw, 3.2rem);
    line-height: 1.05;
    letter-spacing: 0;
  }
  .lede {
    max-width: 840px;
    margin-bottom: 0;
    color: var(--muted);
    line-height: 1.55;
  }
  .badge {
    display: inline-flex;
    align-items: center;
    min-height: 2.1rem;
    padding: .35rem .65rem;
    border: 1px solid #a9c6b9;
    border-radius: 8px;
    background: #e9f3ee;
    color: var(--primary-dark);
    font-weight: 700;
    white-space: nowrap;
  }
  main {
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(320px, .95fr);
    gap: 18px;
    padding: 20px 0 36px;
  }
  section, aside {
    min-width: 0;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--panel);
  }
  .panel { padding: 18px; }
  .workspace {
    display: grid;
    gap: 16px;
  }
  form {
    display: grid;
    gap: 12px;
  }
  .field-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
  label {
    display: grid;
    gap: 6px;
    font-weight: 700;
  }
  input, textarea, button {
    font: inherit;
  }
  input, textarea {
    width: 100%;
    min-width: 0;
    border: 1px solid #b9c4bd;
    border-radius: 8px;
    background: var(--field);
    color: var(--ink);
    padding: .72rem .78rem;
  }
  textarea { min-height: 104px; resize: vertical; }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  button {
    border: 0;
    border-radius: 8px;
    background: var(--primary);
    color: #fff;
    padding: .7rem .95rem;
    font-weight: 800;
    cursor: pointer;
  }
  button.secondary { background: var(--blue); }
  button:disabled { opacity: .58; cursor: wait; }
  .result {
    min-height: 260px;
    border-top: 1px solid var(--line);
    padding-top: 16px;
  }
  .status-line {
    display: inline-flex;
    align-items: center;
    gap: .45rem;
    min-height: 2rem;
    padding: .25rem .55rem;
    border-radius: 8px;
    background: #eef5f1;
    color: var(--primary-dark);
    font-weight: 800;
  }
  .status-line.warn { background: #fff3eb; color: var(--warn); }
  .status-line.empty { background: #fff8e7; color: #7b570d; }
  dl {
    display: grid;
    grid-template-columns: 10rem minmax(0, 1fr);
    gap: 8px 12px;
    margin: 14px 0;
  }
  dt { color: var(--muted); font-weight: 800; }
  dd { margin: 0; overflow-wrap: anywhere; }
  ul { padding-left: 1.25rem; }
  li { margin: .35rem 0; }
  .boundary {
    border-left: 4px solid var(--warn);
    padding: 12px;
    border-radius: 8px;
    background: #fff6f0;
  }
  .state-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }
  .state-tile {
    min-height: 108px;
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 12px;
    background: #fbfcfb;
  }
  .state-tile strong { display: block; margin-bottom: 5px; }
  .muted { color: var(--muted); }
  footer { padding-bottom: 34px; color: var(--muted); }
  :focus-visible { outline: 4px solid #d9b04c; outline-offset: 3px; }
  @media (max-width: 820px) {
    header { grid-template-columns: 1fr; }
    main { grid-template-columns: 1fr; }
    .field-row, .state-grid, dl { grid-template-columns: 1fr; }
    .badge { width: fit-content; white-space: normal; }
  }
</style>
</head>
<body>
<a class="skip-link" href="#main">Skip to main content</a>
<header>
  <div>
    <h1>Townlight Zoning resident lookup</h1>
    <p class="lede">Parcel zoning context, cited use rules, dimensional standards, and escalation paths for residents. Townlight Zoning provides information only; planning staff make official determinations.</p>
  </div>
  <span class="badge">v0.2.2 corrective demotion state</span>
</header>
<main id="main" tabindex="-1">
  <section class="panel workspace" aria-labelledby="lookup-title">
    <div>
      <h2 id="lookup-title">Lookup and question</h2>
      <p class="muted">The sample city dataset includes parcel 100-200-300 at 123 Main St in R-2.</p>
    </div>
    <form id="zone-form">
      <div class="field-row">
        <label for="parcel">Parcel number
          <input id="parcel" name="parcel" value="100-200-300" autocomplete="off">
        </label>
        <label for="address">Address
          <input id="address" name="address" value="123 Main St" autocomplete="street-address">
        </label>
      </div>
      <label for="question">Question
        <textarea id="question" name="question">Can I build an ADU?</textarea>
      </label>
      <div class="actions">
        <button id="run" type="submit">Run lookup</button>
        <button class="secondary" id="empty" type="button">Check missing parcel</button>
        <button class="secondary" id="partial" type="button">Check planner review</button>
      </div>
    </form>
    <div class="result" id="result" role="status" aria-live="polite">
      <span class="status-line">Ready</span>
      <p>Submit the sample lookup to see parcel context, citations, and the non-determination boundary.</p>
    </div>
  </section>
  <section class="panel" aria-labelledby="process-title">
    <h2 id="process-title">Variance, conditional use and nonconformity</h2>
    <p>A <strong>variance</strong> asks to depart from one specific standard (for example a
    setback), because applying it here is unusually burdensome. A <strong>conditional use
    permit</strong> reviews a use the code already allows, subject to conditions. Both are
    discretionary: a body named in the code decides after review, and neither is granted or
    denied by this page.</p>
    <p>Dimensional standards and their code citations come from the loaded rule dataset.
    Where a stated condition does not meet a cited standard, this product raises a
    <strong>possible nonconformity review flag</strong>. It never declares a condition
    legally nonconforming: only staff can determine that from the parcel record and the
    code in effect when the condition was established.</p>
    <p class="boundary">If the loaded rules do not cover a standard, the answer is
    &ldquo;unavailable&rdquo; with the reason. No standard is estimated.</p>
  </section>
  <aside class="panel" aria-labelledby="states-title">
    <h2 id="states-title">Resident states</h2>
    <div class="state-grid">
      <div class="state-tile"><strong>Loading</strong>Lookup actions disable while Townlight Zoning checks the parcel and rules.</div>
      <div class="state-tile"><strong>Success</strong>Context appears with citations and official-decision boundaries.</div>
      <div class="state-tile"><strong>Empty</strong>Missing parcels explain which sample or local records to load.</div>
      <div class="state-tile"><strong>Error or partial</strong>Invalid input, stale data, missing citations, and determinations route to planning staff.</div>
    </div>
    <div class="boundary">
      <h3>Important boundary</h3>
      <p>Townlight Zoning does not provide legal advice, does not make a zoning determination, and does not replace your planning department.</p>
    </div>
    <p><a href="/civiczone/staff">Staff workspace</a> requires the trusted municipal staff access layer for API actions.</p>
  </aside>
</main>
<footer>
  <p>Townlight Zoning is part of Townlight. Configure local parcel and zoning-rule data before relying on city-specific answers.</p>
</footer>
<script>
const form = document.querySelector("#zone-form");
const run = document.querySelector("#run");
const result = document.querySelector("#result");
const parcel = document.querySelector("#parcel");
const address = document.querySelector("#address");
const question = document.querySelector("#question");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[char]));
}

function setLoading() {
  run.disabled = true;
  result.innerHTML = '<span class="status-line">Loading</span><p>Checking parcel, use rules, and cited answer boundaries.</p>';
}

function renderFailure(title, detail, mode = "warn") {
  const message = detail?.message || title;
  const fix = detail?.fix || "Check the address, parcel number, and question, then retry.";
  result.innerHTML = `<span class="status-line ${mode}">${escapeHtml(title)}</span><h3>${escapeHtml(message)}</h3><p>${escapeHtml(fix)}</p>`;
}

function renderSuccess(parcelPayload, answerPayload) {
  const answerStatus = answerPayload.status === "answered" ? "Success" : "Planner review";
  const mode = answerPayload.status === "answered" ? "" : "warn";
  const citations = (answerPayload.citations || []).map((citation) => `<li>${escapeHtml(citation)}</li>`).join("") || "<li>No citation available; route to planning staff.</li>";
  result.innerHTML = `
    <span class="status-line ${mode}">${answerStatus}</span>
    <dl>
      <dt>Parcel</dt><dd>${escapeHtml(parcelPayload.parcel_number)}</dd>
      <dt>Address</dt><dd>${escapeHtml(parcelPayload.address)}</dd>
      <dt>Zone</dt><dd>${escapeHtml(parcelPayload.zone.code)} - ${escapeHtml(parcelPayload.zone.name)}</dd>
      <dt>Overlays</dt><dd>${escapeHtml((parcelPayload.overlays || []).join(", ") || "None listed")}</dd>
      <dt>Constraints</dt><dd>${escapeHtml((parcelPayload.constraints || []).join("; ") || "None listed")}</dd>
      <dt>Answer</dt><dd>${escapeHtml(answerPayload.answer)}</dd>
      <dt>Next step</dt><dd>${escapeHtml(answerPayload.next_step)}</dd>
    </dl>
    <h3>Citations</h3>
    <ul>${citations}</ul>
    <p class="boundary">${escapeHtml(answerPayload.disclaimer || parcelPayload.disclaimer)}</p>
  `;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body)
  });
  const payload = await response.json();
  if (!response.ok) {
    throw payload;
  }
  return payload;
}

async function runLookup(event) {
  event.preventDefault();
  setLoading();
  try {
    const parcelPayload = await postJson("/api/v1/civiczone/parcels/lookup", {
      parcel_number: parcel.value.trim() || null,
      address: address.value.trim() || null
    });
    const answerPayload = await postJson("/api/v1/civiczone/questions/answer", {
      zone_code: parcelPayload.zone.code,
      question: question.value.trim()
    });
    renderSuccess(parcelPayload, answerPayload);
  } catch (error) {
    renderFailure("Needs attention", error.detail || error, error.status === "refused" ? "empty" : "warn");
  } finally {
    run.disabled = false;
  }
}

form.addEventListener("submit", runLookup);
document.querySelector("#empty").addEventListener("click", () => {
  parcel.value = "not-a-real-parcel";
  address.value = "";
  question.value = "Can I build an ADU?";
  form.requestSubmit();
});
document.querySelector("#partial").addEventListener("click", () => {
  parcel.value = "100-200-300";
  address.value = "123 Main St";
  question.value = "Will the city approve my variance?";
  form.requestSubmit();
});
</script>
</body>
</html>
"""
