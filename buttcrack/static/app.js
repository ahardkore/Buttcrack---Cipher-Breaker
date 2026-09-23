/* buttcrack — web interface
 *
 * Vanilla JS, no build step, no dependencies.  The page talks to four endpoints
 * on the same origin (/api/health, /api/ciphers, /api/identify, /api/transform)
 * plus a job pair for cracking (/api/crack -> /api/job/<id>), which it polls so
 * the search log streams while the engine works in a background thread.
 *
 * Everything the engine sends back is inserted with textContent: ciphertext and
 * "plaintext" are untrusted input by definition, and this page must never treat
 * them as markup.
 */
"use strict";

const $ = (id) => document.getElementById(id);

const state = {
  ciphers: [],
  byName: new Map(),
  health: null,
  job: null,
  poll: null,
  renderedLines: 0,
  lastReport: null,
  showRaw: false,
  operation: "encrypt",
};

const COST_LABEL = { 1: "cheap", 3: "moderate", 10: "expensive", 30: "brutal" };

const SAMPLES = [
  { label: "caesar", text: "Tlla aol jvbyply ilzpkl aol mvbuahpu ha uvvu huk iypun aol zljvuk luclsvwl dpao fvb." },
  { label: "atbash", text: "Nvvg gsv xlfirvi yvhrwv gsv ulfmgzrm zg mllm zmw yirmt gsv hvxlmw vmevolkv drgs blf." },
  {
    label: "vigenere",
    text:
      "Llg tsnfgkc sy Nipzgx zeu uivjigu xasx ccp fwveyegl zgjwxdw olwm hea klx fiy yektswi xtp fgwskw ipkikari klx deifsg, srf klx yykch hx qcimgwvu yel hvqkillif ks mzi ffkx ar yimmari.",
  },
  {
    label: "columnar",
    text:
      "CIEHCTLCVLTHHUBERHODUFNATDEITECVEEDARTESTWOXRETGNGOIHOEHEIHNFCDETENSUYEBAOTGAAEDRSRTTGRGTUOISEAMASMANRTFNNLNHLARPSOOWNOLNARHLHESPEAREEIEOTIMESETDNI",
  },
  {
    label: "morse",
    text:
      "- .... . / .-. .- .. .-.. .-- .- -.-- / ... - .- - .. --- -. / .- - / .- ... .... ..-. --- .-. -.. / .-- .- ... / .-. . -... ..- .. .-.. - / .- ..-. - . .-. / - .... . / .-- .- .-. .-.-.-",
  },
  { label: "base64(caesar)", text: "UGhodyB3a2ggZnJ4dWxodSBlaHZsZ2ggd2toIGlyeHF3ZGxxIGR3IHFycnEgZHFnIGV1bHFqIHdraCB2aGZycWcgaGF5aG9yc2ggemx3ayBicngu" },
  {
    label: "hex(xor)",
    text:
      "182928702f2e383e2f28217023276d06292f2433296125313f6129352f332835286139382d356d31202d6d3d29332e382d2f39703a243e23292d3e7021343e246c312c296c3525356c2f28276c292c222e2e38226c352c286c23283623332870292f39353e2823376c3525356c2d2c37232e237c6c2023346c3525356c26383920256d3f2a6120313e2823353e326d382d326d203e2e39353f3528346c35227038292870282e2a356c2823703b332424252f2a7e",
  },
];

/* ------------------------------------------------------------------ helpers */

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function make(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function fmtNumber(value, digits = 4) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (typeof value !== "number") return String(value);
  if (Number.isInteger(value)) return value.toLocaleString("en-US");
  return value.toFixed(digits);
}

function fmtKey(key) {
  if (key === null || key === undefined) return "—";
  if (typeof key === "string") return key;
  try {
    return JSON.stringify(key);
  } catch (_error) {
    return String(key);
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const text = await response.text();
  let payload;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch (_error) {
    throw new Error(`server sent ${response.status} and no JSON`);
  }
  if (!response.ok) throw new Error(payload.error || `${response.status} ${response.statusText}`);
  return payload;
}

function showError(message) {
  $("error-text").textContent = message;
  $("error-card").hidden = false;
}

function hideError() {
  $("error-card").hidden = true;
}

/* --------------------------------------------------------------------- boot */

async function boot() {
  wireTabs();
  wireBreak();
  wirePlayground();
  wireReference();
  renderSamples();

  try {
    const [health, ciphers] = await Promise.all([api("/api/health"), api("/api/ciphers")]);
    state.health = health;
    state.ciphers = ciphers;
    state.byName = new Map(ciphers.map((c) => [c.name, c]));
    renderHealth(health);
    renderWorkers(health.cpus || 1);
    populatePlayground(ciphers);
    renderReference(ciphers);
    if (health.model && health.model.quadgrams) {
      $("about-quadgrams").textContent = `${health.model.quadgrams.toLocaleString("en-US")} quadgram`;
    }
  } catch (error) {
    renderHealth({ error: String(error.message || error) });
    showError(`Could not reach the engine: ${error.message || error}`);
  }
}

function renderHealth(health) {
  const node = $("health");
  clear(node);
  if (health.error) {
    node.textContent = "engine unreachable";
    node.className = "health bad";
    return;
  }
  node.textContent = `v${health.version} · ${health.ciphers} ciphers · py ${health.python} · ${health.cpus} cpu`;
  node.className = "health ok";
  $("version").textContent = `v${health.version}`;
  $("footer-status").textContent = `buttcrack ${health.version} — ${health.ciphers} ciphers, ${health.layers.length} peelable layers`;
}

function renderWorkers(cpus) {
  const select = $("workers");
  clear(select);
  for (let n = 1; n <= Math.max(1, cpus); n += 1) {
    const option = make("option", null, n === 1 ? "1 (single process)" : `${n} processes`);
    option.value = String(n);
    if (n === cpus) option.selected = true;
    select.appendChild(option);
  }
}

function renderSamples() {
  const holder = $("samples");
  clear(holder);
  for (const sample of SAMPLES) {
    const chip = make("button", "chip", sample.label);
    chip.type = "button";
    chip.title = sample.text.slice(0, 90);
    chip.addEventListener("click", () => {
      $("input").value = sample.text;
      $("input").focus();
    });
    holder.appendChild(chip);
  }
}

/* --------------------------------------------------------------------- tabs */

function wireTabs() {
  const buttons = document.querySelectorAll(".tab-button");
  for (const button of buttons) {
    button.addEventListener("click", () => activateTab(button.dataset.tab));
  }
}

function activateTab(name) {
  for (const button of document.querySelectorAll(".tab-button")) {
    const active = button.dataset.tab === name;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", active ? "true" : "false");
  }
  for (const panel of document.querySelectorAll(".tab")) {
    panel.classList.toggle("active", panel.id === `tab-${name}`);
    panel.hidden = panel.id !== `tab-${name}`;
  }
}

/* -------------------------------------------------------------------- break */

function wireBreak() {
  $("crack").addEventListener("click", () => startCrack());
  $("identify").addEventListener("click", () => runIdentify());
  $("clear").addEventListener("click", () => {
    $("input").value = "";
    resetResult();
  });
  $("copy-plain").addEventListener("click", () => copyText(currentPlaintext()));
  $("toggle-formatted").addEventListener("click", () => {
    state.showRaw = !state.showRaw;
    $("toggle-formatted").textContent = state.showRaw ? "Show with layout" : "Show raw letters";
    renderPlaintext(state.lastReport);
  });
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      if (!$("tab-break").hidden) startCrack();
      else if (!$("tab-playground").hidden) runPlayground();
    }
  });
}

function currentPlaintext() {
  return $("plaintext").textContent || "";
}

function copyText(text) {
  if (!text) return;
  const done = () => {
    const button = $("copy-plain");
    const original = button.textContent;
    button.textContent = "Copied";
    setTimeout(() => {
      button.textContent = original;
    }, 1200);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done, () => fallbackCopy(text, done));
  } else {
    fallbackCopy(text, done);
  }
}

function fallbackCopy(text, done) {
  const area = document.createElement("textarea");
  area.value = text;
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  try {
    document.execCommand("copy");
    done();
  } catch (_error) {
    /* nothing else to try */
  }
  document.body.removeChild(area);
}

function collectHints() {
  const hints = {};
  const fields = { key: "hint-key", key_length: "hint-len", width: "hint-width", seed: "hint-seed", crib: "hint-crib" };
  for (const [name, id] of Object.entries(fields)) {
    const value = $(id).value.trim();
    if (value) hints[name] = value;
  }
  return Object.keys(hints).length ? hints : null;
}

function resetResult() {
  stopPolling();
  $("result-card").hidden = true;
  $("progress-card").hidden = true;
  hideError();
  clear($("log"));
  state.renderedLines = 0;
  state.lastReport = null;
  $("progress-bar").style.width = "0%";
  $("crack").disabled = false;
  $("identify").disabled = false;
}

async function startCrack() {
  const text = $("input").value;
  if (!text.trim()) {
    showError("Paste some ciphertext first — or click one of the samples.");
    return;
  }
  hideError();
  resetResult();
  $("progress-card").hidden = false;
  $("progress-state").textContent = "starting…";
  $("crack").disabled = true;
  $("identify").disabled = true;

  const body = {
    text,
    budget: parseFloat($("budget").value),
    workers: parseInt($("workers").value, 10),
    depth: parseInt($("depth").value, 10),
    exhaustive: $("exhaustive").checked,
    hints: collectHints(),
  };

  try {
    const started = await api("/api/crack", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    state.job = started.job;
    state.poll = setInterval(() => pollJob(started.job), 250);
    pollJob(started.job);
  } catch (error) {
    $("crack").disabled = false;
    $("identify").disabled = false;
    showError(error.message || String(error));
  }
}

function stopPolling() {
  if (state.poll) clearInterval(state.poll);
  state.poll = null;
}

async function pollJob(jobId) {
  let job;
  try {
    job = await api(`/api/job/${jobId}`);
  } catch (error) {
    stopPolling();
    $("crack").disabled = false;
    $("identify").disabled = false;
    showError(error.message || String(error));
    return;
  }
  renderProgress(job.progress || []);
  if (!job.done) return;

  stopPolling();
  $("crack").disabled = false;
  $("identify").disabled = false;
  if (job.error) {
    $("progress-state").textContent = "failed";
    showError(`${job.error}\n\n${job.traceback || ""}`.trim());
    return;
  }
  $("progress-state").textContent = "done";
  $("progress-bar").style.width = "100%";
  if (job.report) renderReport(job.report);
}

function renderProgress(lines) {
  const log = $("log");
  for (let i = state.renderedLines; i < lines.length; i += 1) {
    const line = lines[i];
    const item = make("li");
    const milestone = /solved|peeling|hypothesis|characterised|certain/i.test(line.message || "");
    if (milestone) item.className = "milestone";
    item.appendChild(make("span", "t", `${(line.at || 0).toFixed(2)}s`));
    item.appendChild(make("span", "m", line.message));
    log.appendChild(item);
    if (line.fraction && line.fraction > 0) {
      $("progress-bar").style.width = `${Math.min(100, line.fraction * 100).toFixed(1)}%`;
      $("progress-state").textContent = line.message;
    }
  }
  if (lines.length > state.renderedLines) {
    state.renderedLines = lines.length;
    log.scrollTop = log.scrollHeight;
  }
}

function renderReport(report) {
  state.lastReport = report;
  $("result-card").hidden = false;

  const best = report.best || {};
  const notes = best.notes || {};
  const confidence = report.confidence || 0;

  const verdict = $("verdict");
  verdict.textContent = report.solved ? "solved" : confidence >= 0.35 ? "probable" : "no answer";
  verdict.className = `verdict ${report.solved ? "solved" : confidence >= 0.35 ? "probable" : "failed"}`;

  const bar = $("confidence-bar");
  bar.style.width = `${Math.max(2, confidence * 100).toFixed(1)}%`;
  bar.className = `meter-fill ${report.solved ? "good" : confidence >= 0.35 ? "" : "bad"}`;
  $("confidence-value").textContent = confidence.toFixed(3);
  $("elapsed").textContent = `${report.elapsed.toFixed(2)}s of ${report.budget}s · ${report.workers} worker${report.workers === 1 ? "" : "s"}`;

  renderPlaintext(report);
  renderMeta(report, best, notes);
  renderHypotheses(report.hypotheses || [], report.stats || {});
  renderStats(report.stats || {});
  renderAlternatives(report.candidates || []);
  renderAttacks(report.attacks || []);
}

function renderPlaintext(report) {
  const node = $("plaintext");
  const best = (report && report.best) || {};
  const notes = best.notes || {};
  let text = "";
  if (state.showRaw) text = best.plaintext || "";
  else text = notes.formatted || notes.respaced || best.plaintext || "";
  node.textContent = text || "(nothing recovered)";
  node.classList.toggle("unsolved", !(report && report.solved));
  $("toggle-formatted").textContent = state.showRaw ? "Show with layout" : "Show raw letters";
  $("toggle-formatted").disabled = !(notes.formatted || notes.respaced);
}

function renderMeta(report, best, notes) {
  const meta = $("meta");
  clear(meta);
  const rows = [
    ["decode chain", notes.decode_chain || best.cipher || "none", true],
    ["cipher", best.cipher === "none" ? "plain / encoding layer" : best.cipher || "—", false],
    ["key", best.key || "—", true],
    ["also known as", notes.also_known_as || "", false],
    ["method", notes.method || "", false],
    ["evidence", notes.evidence || "", false],
    ["letters", report.stats ? report.stats.letters : "", false],
    ["index of coincidence", report.stats ? report.stats.index_of_coincidence : "", false],
  ];
  const extras = ["key_length", "key_hex", "period_quality", "column_ic", "printable_ratio", "input_encoding", "width", "rows"];
  for (const name of extras) {
    if (notes[name] !== undefined && notes[name] !== null && notes[name] !== "") {
      rows.push([name.replace(/_/g, " "), notes[name], false]);
    }
  }
  for (const [label, value, accent] of rows) {
    if (value === "" || value === null || value === undefined) continue;
    const wrap = make("div");
    wrap.appendChild(make("dt", null, label));
    wrap.appendChild(make("dd", accent ? "accent" : null, fmtKey(value)));
    meta.appendChild(wrap);
  }
}

function renderStats(stats) {
  const node = $("stats");
  clear(node);
  if (!stats || !stats.length) {
    node.appendChild(make("dt", null, "length"));
    node.appendChild(make("dd", null, "—"));
    return;
  }
  const rows = [
    ["length", stats.length],
    ["letters", stats.letters],
    ["digits", stats.digits],
    ["spaces", stats.spaces],
    ["punctuation", stats.punctuation],
    ["upper / lower", `${stats.upper} / ${stats.lower}`],
    ["unique chars", stats.unique_chars],
    ["entropy / char", fmtNumber(stats.entropy, 3)],
    ["index of coincidence", fmtNumber(stats.index_of_coincidence, 5)],
    ["chi² per char", fmtNumber(stats.chi_squared_per_char, 3)],
    ["quadgram fitness", fmtNumber(stats.quadgram_fitness, 2)],
  ];
  if (stats.is_letter_text !== undefined) rows.push(["letter text", stats.is_letter_text ? "yes" : "no"]);
  for (const [label, value] of rows) {
    node.appendChild(make("dt", null, label));
    node.appendChild(make("dd", null, value));
  }
}

function renderHypotheses(hypotheses, stats) {
  const node = $("hypotheses");
  clear(node);
  if (!hypotheses.length) {
    node.appendChild(make("li", "empty", "no structural or statistical evidence — the solver will try everything"));
    return;
  }
  for (const hypothesis of hypotheses) {
    const item = make("li");
    item.appendChild(make("span", "name", hypothesis.cipher));
    item.appendChild(make("span", "score", `${Math.round(hypothesis.likelihood * 100)}%`));
    const bar = make("span", "bar");
    const fill = make("span");
    fill.style.width = `${Math.max(2, hypothesis.likelihood * 100).toFixed(0)}%`;
    bar.appendChild(fill);
    item.appendChild(bar);
    if (hypothesis.reason) item.appendChild(make("span", "reason", hypothesis.reason));
    node.appendChild(item);
  }
  if (stats && Object.keys(stats).length) renderStats(stats);
}

function renderAlternatives(candidates) {
  const body = $("alternatives");
  clear(body);
  const rest = candidates.slice(1);
  $("alternatives-section").hidden = rest.length === 0;
  rest.forEach((candidate, index) => {
    const row = make("tr");
    row.appendChild(make("td", "num", index + 2));
    const conf = make("td", "num");
    const bar = make("span", "bar");
    bar.style.width = `${Math.max(2, candidate.confidence * 60).toFixed(0)}px`;
    conf.appendChild(bar);
    conf.appendChild(document.createTextNode(candidate.confidence.toFixed(3)));
    row.appendChild(conf);
    row.appendChild(make("td", "mono", candidate.steps && candidate.steps.length ? `${candidate.steps.join(" → ")} → ${candidate.cipher}` : candidate.cipher));
    row.appendChild(make("td", "mono", candidate.key || "—"));
    const text = make("td");
    const clip = make("span", "clip", (candidate.plaintext || "").slice(0, 90));
    clip.title = (candidate.plaintext || "").slice(0, 400);
    text.appendChild(clip);
    row.appendChild(text);
    body.appendChild(row);
  });
}

function renderAttacks(attacks) {
  const body = $("attacks");
  clear(body);
  $("attacks-section").hidden = attacks.length === 0;
  for (const attack of attacks) {
    const row = make("tr");
    row.appendChild(make("td", "mono", attack.cipher));
    row.appendChild(make("td", `mono status-${attack.status}`, attack.status));
    row.appendChild(make("td", "num", attack.tried));
    row.appendChild(make("td", "num", attack.best_confidence ? attack.best_confidence.toFixed(3) : "—"));
    row.appendChild(make("td", "num", `${attack.elapsed.toFixed(2)}s`));
    row.appendChild(make("td", null, attack.detail || ""));
    body.appendChild(row);
  }
}

/* ----------------------------------------------------------------- identify */

async function runIdentify() {
  const text = $("input").value;
  if (!text.trim()) {
    showError("Paste some ciphertext first.");
    return;
  }
  hideError();
  $("identify").disabled = true;
  try {
    const result = await api("/api/identify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    renderStats(result.stats || {});
    renderHypotheses(result.hypotheses || [], null);
    $("result-card").hidden = true;
  } catch (error) {
    showError(error.message || String(error));
  } finally {
    $("identify").disabled = false;
  }
}

/* --------------------------------------------------------------- playground */

function wirePlayground() {
  $("pg-run").addEventListener("click", () => runPlayground());
  $("pg-copy").addEventListener("click", () => copyText($("pg-output").value));
  $("pg-send").addEventListener("click", () => {
    const output = $("pg-output").value;
    if (!output.trim()) return;
    $("input").value = output;
    activateTab("break");
    resetResult();
  });
  for (const button of document.querySelectorAll(".segmented button")) {
    button.addEventListener("click", () => {
      state.operation = button.dataset.op;
      for (const other of document.querySelectorAll(".segmented button")) {
        other.classList.toggle("active", other === button);
      }
    });
  }
  $("pg-cipher").addEventListener("change", () => {
    const info = state.byName.get($("pg-cipher").value);
    if (info) showCipherInfo(info);
  });
}

function populatePlayground(ciphers) {
  const select = $("pg-cipher");
  clear(select);
  const families = new Map();
  for (const cipher of ciphers) {
    if (!families.has(cipher.family)) families.set(cipher.family, []);
    families.get(cipher.family).push(cipher);
  }
  for (const family of [...families.keys()].sort()) {
    const group = make("optgroup");
    group.label = family;
    for (const cipher of families.get(family).sort((a, b) => a.name.localeCompare(b.name))) {
      const option = make("option", null, cipher.title || cipher.name);
      option.value = cipher.name;
      group.appendChild(option);
    }
    select.appendChild(group);
  }
  const first = ciphers[0];
  if (first) showCipherInfo(first);
}

function showCipherInfo(info) {
  $("pg-title").textContent = info.title || info.name;
  $("pg-description").textContent = info.description || "";
  $("pg-key").value = info.example_key === null || info.example_key === undefined ? "" : fmtKey(info.example_key);
  $("pg-key").disabled = !info.keyed;
  const details = $("pg-details");
  clear(details);
  const rows = [
    ["name", info.name],
    ["family", info.family],
    ["aliases", (info.aliases || []).join(", ") || "—"],
    ["key type", info.keyed ? info.key_type : "none"],
    ["example key", fmtKey(info.example_key)],
    ["keyspace", info.keyspace ? info.keyspace.toLocaleString("en-US") : "—"],
    ["attack cost", COST_LABEL[info.cost] || info.cost],
    ["peelable layer", info.layer ? "yes" : "no"],
    ["min length", info.min_length],
    ["deterministic", info.deterministic ? "yes" : "no"],
  ];
  for (const [label, value] of rows) {
    details.appendChild(make("dt", null, label));
    details.appendChild(make("dd", null, value));
  }
  $("pg-note").textContent = info.keyed
    ? `Key format: ${info.key_type}. Numbers, words, {"a": 5, "b": 8} style objects and comma-separated lists are all understood.`
    : "This cipher takes no key.";
}

/** Mirror of the CLI's parse_key: use the example key as the type signature. */
function coerceKey(raw, example) {
  const text = (raw || "").trim();
  if (!text) return example === undefined ? null : example;
  if (text.startsWith("hex:") || text.startsWith("0x")) {
    const hex = text.replace(/^(hex:|0x)/, "").replace(/[\s:]/g, "");
    const bytes = [];
    for (let i = 0; i + 1 < hex.length; i += 2) bytes.push(parseInt(hex.slice(i, i + 2), 16));
    return bytes;
  }
  if (typeof example === "number") {
    const value = Number(text);
    return Number.isNaN(value) ? text : value;
  }
  if (Array.isArray(example)) {
    if (text.startsWith("[")) {
      try {
        return JSON.parse(text);
      } catch (_error) {
        /* fall through to comma splitting */
      }
    }
    return text.split(",").map((part) => {
      const trimmed = part.trim();
      const value = Number(trimmed);
      return trimmed !== "" && !Number.isNaN(value) ? value : trimmed;
    });
  }
  if (example && typeof example === "object") {
    if (text.startsWith("{")) {
      try {
        return JSON.parse(text);
      } catch (_error) {
        /* fall through to a=b parsing */
      }
    }
    const out = {};
    for (const part of text.split(/[,\s]+/)) {
      const [name, value] = part.split("=");
      if (!name || value === undefined) continue;
      const numeric = Number(value);
      out[name.trim()] = value !== "" && !Number.isNaN(numeric) ? numeric : value.trim();
    }
    return Object.keys(out).length ? out : text;
  }
  return text;
}

async function runPlayground() {
  const name = $("pg-cipher").value;
  const info = state.byName.get(name);
  const text = $("pg-input").value;
  if (!text.trim()) {
    $("pg-note").textContent = "Type something to transform first.";
    return;
  }
  const key = coerceKey($("pg-key").value, info ? info.example_key : null);
  $("pg-run").disabled = true;
  $("pg-output").value = "";
  try {
    const result = await api("/api/transform", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cipher: name, key, text, operation: state.operation }),
    });
    $("pg-output").value = result.output;
    $("pg-note").textContent = `${result.cipher} · ${result.operation} · key ${fmtKey(result.key)} · ${result.length} characters out`;
  } catch (error) {
    $("pg-note").textContent = `Error: ${error.message || error}`;
  } finally {
    $("pg-run").disabled = false;
  }
}

/* ---------------------------------------------------------------- reference */

function wireReference() {
  $("ref-search").addEventListener("input", () => renderReference(state.ciphers, $("ref-search").value));
}

function renderReference(ciphers, filter = "") {
  const holder = $("reference");
  clear(holder);
  const needle = filter.trim().toLowerCase();
  const matches = ciphers.filter((cipher) => {
    if (!needle) return true;
    const haystack = [cipher.name, cipher.title, cipher.family, cipher.description, ...(cipher.aliases || [])]
      .join(" ")
      .toLowerCase();
    return haystack.includes(needle);
  });
  if (!matches.length) {
    holder.appendChild(make("p", "hint", `Nothing matches “${filter}”.`));
    return;
  }
  const families = new Map();
  for (const cipher of matches) {
    if (!families.has(cipher.family)) families.set(cipher.family, []);
    families.get(cipher.family).push(cipher);
  }
  for (const family of [...families.keys()].sort()) {
    const section = make("div", "family");
    section.appendChild(make("h3", null, `${family} (${families.get(family).length})`));
    for (const cipher of families.get(family).sort((a, b) => a.name.localeCompare(b.name))) {
      const row = make("div", "cipher-row");
      row.appendChild(make("span", "name", cipher.name));
      row.appendChild(make("span", "desc", cipher.description || cipher.title));
      const tags = make("span", "tags");
      if (cipher.layer) tags.appendChild(make("span", "tag layer", "layer"));
      if (cipher.keyed) tags.appendChild(make("span", "tag keyed", cipher.key_type));
      if (cipher.keyspace) tags.appendChild(make("span", "tag", `${cipher.keyspace.toLocaleString("en-US")} keys`));
      tags.appendChild(make("span", "tag", COST_LABEL[cipher.cost] || `cost ${cipher.cost}`));
      row.appendChild(tags);
      row.title = `Try it: Playground → ${cipher.name}`;
      row.addEventListener("click", () => {
        activateTab("playground");
        $("pg-cipher").value = cipher.name;
        showCipherInfo(cipher);
      });
      section.appendChild(row);
    }
    holder.appendChild(section);
  }
}

document.addEventListener("DOMContentLoaded", boot);
