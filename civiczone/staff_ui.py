"""Staff workflow UI shell for CivicZone."""

from __future__ import annotations


def render_staff_workspace_page() -> str:
    """Render a browser-usable staff shell that calls staff APIs through trusted headers."""

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>Townlight Zoning Staff Workspace</title>
<style>
  :root {
    --bg: #f4f6f8;
    --panel: #ffffff;
    --ink: #17212b;
    --muted: #5e6874;
    --line: #cbd5df;
    --primary: #285f7f;
    --primary-dark: #1d465e;
    --warn: #9b4e2e;
    --ok: #1e684f;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: "Segoe UI", Arial, sans-serif;
  }
  header, main, footer {
    width: min(1180px, calc(100% - 32px));
    margin: 0 auto;
  }
  header {
    padding: 28px 0 18px;
    border-bottom: 1px solid var(--line);
  }
  h1 { margin: 0 0 .4rem; font-size: clamp(1.85rem, 4vw, 3rem); letter-spacing: 0; }
  h2, h3, p { margin-top: 0; }
  .muted { color: var(--muted); }
  main {
    display: grid;
    grid-template-columns: minmax(280px, .42fr) minmax(0, .58fr);
    gap: 18px;
    padding: 20px 0 36px;
  }
  section {
    min-width: 0;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--panel);
    padding: 18px;
  }
  form { display: grid; gap: 12px; }
  label { display: grid; gap: 6px; font-weight: 700; }
  input, textarea, button {
    font: inherit;
  }
  input, textarea {
    width: 100%;
    border: 1px solid #b7c3ce;
    border-radius: 8px;
    padding: .72rem .78rem;
  }
  textarea { min-height: 96px; resize: vertical; }
  button {
    width: fit-content;
    border: 0;
    border-radius: 8px;
    background: var(--primary);
    color: #fff;
    padding: .7rem .95rem;
    font-weight: 800;
    cursor: pointer;
  }
  button.secondary { background: var(--ok); }
  button:disabled { opacity: .6; cursor: wait; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .result {
    min-height: 320px;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: #fbfcfd;
    padding: 14px;
    overflow-wrap: anywhere;
  }
  .status {
    display: inline-flex;
    margin-bottom: 12px;
    border-radius: 8px;
    padding: .35rem .6rem;
    background: #eaf2f6;
    color: var(--primary-dark);
    font-weight: 800;
  }
  .status.warn { background: #fff3eb; color: var(--warn); }
  pre {
    white-space: pre-wrap;
    margin: 0;
    font: .9rem/1.5 "Cascadia Mono", Consolas, monospace;
  }
  .boundary {
    border-left: 4px solid var(--warn);
    padding: 12px;
    border-radius: 8px;
    background: #fff7f2;
  }
  :focus-visible { outline: 4px solid #d9b04c; outline-offset: 3px; }
  @media (max-width: 860px) {
    main, .grid { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<header>
  <h1>Townlight Zoning staff workspace</h1>
  <p class="muted">Planner Q&amp;A, ambiguity review queue, analytics, report outlines, and flagged-answer improvement. Staff API calls require trusted municipal access headers from an approved proxy.</p>
</header>
<main>
  <section aria-labelledby="staff-form-title">
    <h2 id="staff-form-title">Staff action</h2>
    <form id="staff-form">
      <div class="grid">
        <label for="principal">Staff principal
          <input id="principal" value="planner@example.gov" autocomplete="email">
        </label>
        <label for="role">Role
          <input id="role" value="planner" autocomplete="off">
        </label>
      </div>
      <label for="zone">Zone
        <input id="zone" value="R-2" autocomplete="off">
      </label>
      <label for="question">Question
        <textarea id="question">What is the front setback?</textarea>
      </label>
      <div class="grid">
        <button id="answer" type="submit">Answer</button>
        <button class="secondary" id="queue" type="button">Create review item</button>
        <button class="secondary" id="analytics" type="button">Analytics</button>
        <button class="secondary" id="outline" type="button">Report outline</button>
      </div>
    </form>
    <div class="boundary">
      <p><strong>Staff-only boundary:</strong> this page does not embed staff data. The API rejects missing identity headers, unauthorized roles, or headers not received through a trusted proxy/source.</p>
    </div>
  </section>
  <section aria-labelledby="staff-result-title">
    <h2 id="staff-result-title">Result</h2>
    <div class="result" id="result" role="status" aria-live="polite">
      <span class="status">Ready</span>
      <p>Run a staff action through the configured access layer.</p>
    </div>
  </section>
</main>
<footer>
  <p>Townlight Zoning staff outputs are review support only. Planning staff remain responsible for official determinations.</p>
</footer>
<script>
const form = document.querySelector("#staff-form");
const result = document.querySelector("#result");
const principal = document.querySelector("#principal");
const role = document.querySelector("#role");
const zone = document.querySelector("#zone");
const question = document.querySelector("#question");
let lastQuestionId = null;
let lastQueueId = null;

function headers() {
  return {
    "Content-Type": "application/json",
    "X-CivicZone-Principal": principal.value.trim(),
    "X-CivicZone-Role": role.value.trim()
  };
}

function show(status, payload, warn = false) {
  result.innerHTML = `<span class="status ${warn ? "warn" : ""}">${status}</span><pre>${JSON.stringify(payload, null, 2)}</pre>`;
}

async function callApi(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {...headers(), ...(options.headers || {})}
  });
  const payload = await response.json();
  if (!response.ok) {
    throw payload;
  }
  return payload;
}

async function staffAnswer(event) {
  event.preventDefault();
  show("Loading", {message: "Submitting planner question."});
  try {
    const payload = await callApi("/api/v1/civiczone/staff/questions/answer", {
      method: "POST",
      body: JSON.stringify({zone_code: zone.value.trim(), question: question.value.trim()})
    });
    lastQuestionId = payload.id;
    show("Answered", payload);
  } catch (error) {
    show("Needs attention", error.detail || error, true);
  }
}

async function createQueue() {
  show("Loading", {message: "Creating ambiguity review."});
  try {
    const payload = await callApi("/api/v1/civiczone/staff/ambiguity-reviews", {
      method: "POST",
      body: JSON.stringify({
        zone_code: zone.value.trim(),
        question: question.value.trim(),
        reason: "Staff review requested from the workspace."
      })
    });
    lastQueueId = payload.id;
    show("Queued", payload);
  } catch (error) {
    show("Needs attention", error.detail || error, true);
  }
}

async function analytics() {
  show("Loading", {message: "Loading high-volume analytics."});
  try {
    show("Analytics", await callApi("/api/v1/civiczone/staff/questions/analytics?high_volume_threshold=1"));
  } catch (error) {
    show("Needs attention", error.detail || error, true);
  }
}

async function outline() {
  show("Loading", {message: "Drafting staff report outline."});
  try {
    const payload = await callApi("/api/v1/civiczone/staff/reports/outline", {
      method: "POST",
      body: JSON.stringify({
        title: "Zoning staff review",
        question_ids: lastQuestionId ? [lastQuestionId] : [],
        queue_item_ids: lastQueueId ? [lastQueueId] : []
      })
    });
    show("Outline", payload);
  } catch (error) {
    show("Needs attention", error.detail || error, true);
  }
}

form.addEventListener("submit", staffAnswer);
document.querySelector("#queue").addEventListener("click", createQueue);
document.querySelector("#analytics").addEventListener("click", analytics);
document.querySelector("#outline").addEventListener("click", outline);
</script>
</body>
</html>
"""
