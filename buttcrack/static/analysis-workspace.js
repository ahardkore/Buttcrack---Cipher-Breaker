/* Bounded local diagnostics, independent of ranking/verification promotion. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const make = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const number = (value, digits = 4) => value === null || value === undefined ? "not measurable" : Number(value).toFixed(digits);
  let context = {ciphertext: "", candidates: [], language: "english"};
  let responseData = null;
  let controller = null;
  let revision = 0;
  const supported = ["vigenere", "beaufort", "variant_beaufort", "gronsfeld", "caesar"];
  const selected = () => context.candidates[Number($("workspace-candidate").value)] || null;

  function stop() {
    revision += 1;
    if (controller) controller.abort();
    controller = null;
  }
  function reset() {
    stop();
    responseData = null;
    context = {ciphertext: "", candidates: [], language: "english"};
    $("workspace-data").hidden = true;
    for (const id of ["workspace-metrics", "workspace-frequency", "workspace-repeats", "workspace-periods", "workspace-estimates", "workspace-alignment", "workspace-warnings"]) $(id).replaceChildren();
    for (const id of ["workspace-reported-key", "workspace-alignment-note", "workspace-normalization", "workspace-method", "workspace-caveat", "workspace-estimate-note"]) $(id).textContent = "";
    $("workspace-candidate").replaceChildren(make("option", "Ciphertext only — no candidate selected"));
    $("workspace-candidate").disabled = true;
    $("workspace-key").value = "";
    $("workspace-status").textContent = "Analyze the input now, or solve it to explore a returned candidate.";
  }
  function setupCandidate() {
    const candidate = selected();
    $("workspace-start").value = "0";
    $("workspace-key-offset").value = "0";
    $("workspace-alignment-model").value = "auto";
    let key = "";
    if (candidate && supported.includes(candidate.cipher) && !(candidate.steps || []).length) {
      const raw = candidate.key_data;
      if (typeof raw === "string" || typeof raw === "number") key = String(raw);
      else if (raw && typeof raw.key === "string") key = raw.key;
      else if (typeof candidate.key === "string" && /^[A-Za-z0-9]+$/.test(candidate.key)) key = candidate.key;
    }
    $("workspace-key").value = key.length <= 128 ? key : "";
    $("workspace-reported-key").textContent = candidate ? `Reported cipher: ${candidate.cipher}. Recovered / supplied key: ${candidate.key || "—"}.` : "No candidate selected; key equations require both ciphertext and plaintext.";
  }
  function intField(id) {
    const value = $(id).value;
    if (!value.trim() || !Number.isInteger(Number(value))) throw new Error("Analysis settings require whole numbers.");
    return Number(value);
  }
  async function analyze() {
    if (!context.ciphertext && !context.candidates.length) {
      $("workspace-status").textContent = "Analyze the current input first, or wait for a solver result.";
      return;
    }
    stop();
    const current = revision;
    const candidate = selected();
    const ciphertext = context.ciphertext;
    const plaintext = candidate ? candidate.plaintext || "" : "";
    $("workspace-data").hidden = true;
    $("workspace-status").textContent = "Computing bounded diagnostics on the local server…";
    try {
      const body = {
        ciphertext: ciphertext.slice(0, 16000), plaintext: plaintext.slice(0, 16000),
        ciphertext_truncated: ciphertext.length > 16000, plaintext_truncated: plaintext.length > 16000,
        max_period: intField("workspace-max-period"), language: context.language,
        cipher: candidate ? candidate.cipher : "none", steps: candidate ? candidate.steps || [] : [],
        key: $("workspace-key").value, key_offset: intField("workspace-key-offset"),
        alignment_start: intField("workspace-start"), alignment_count: 80,
        alignment_model: $("workspace-alignment-model").value,
      };
      controller = new AbortController();
      const response = await fetch("/api/analysis-workspace", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body), signal: controller.signal,
      });
      const result = await response.json();
      if (current !== revision) return;
      if (!response.ok) throw new Error(result.error || "Analysis unavailable");
      responseData = result;
      render();
      $("workspace-data").hidden = false;
      $("workspace-status").textContent = candidate ? `Analyzing candidate #${Number($("workspace-candidate").value) + 1} against the ciphertext captured for that solve. Diagnostics do not change its rank or verification status.` : "Ciphertext-only analysis. No plaintext or key has been recovered by this workspace.";
    } catch (error) {
      if (current !== revision || error.name === "AbortError") return;
      responseData = null;
      $("workspace-status").textContent = `Analysis unavailable: ${error.message}. Existing solver results remain unchanged.`;
    }
  }
  function renderMetrics() {
    $("workspace-metrics").replaceChildren();
    for (const [name, title] of [["ciphertext", "Ciphertext"], ["plaintext", "Selected candidate plaintext"]]) {
      const data = responseData[name];
      const card = make("div", undefined, "workspace-measurements");
      card.append(make("h3", title));
      const list = make("dl", undefined, "stats");
      for (const [label, value] of [
        ["A–Z letters measured", data.letters], ["Index of coincidence", number(data.ic, 5)],
        ["Entropy (bits / A–Z letter)", number(data.letter_entropy)],
        ["Entropy (bits / input character)", number(data.symbol_entropy)],
        ["Distinct letters", data.distinct_letters], ["Raw prefix characters examined", data.sample_chars],
      ]) list.append(make("dt", label), make("dd", String(value)));
      card.append(list);
      $("workspace-metrics").append(card);
    }
  }
  function renderFrequency() {
    const chart = $("workspace-frequency");
    chart.replaceChildren();
    const c = responseData.ciphertext.frequencies;
    const p = responseData.plaintext.frequencies;
    const scale = Math.max(...c.map(row => row.proportion), ...p.map(row => row.proportion), .01);
    for (let i = 0; i < 26; i += 1) {
      const row = make("div", undefined, "frequency-row");
      row.append(make("span", c[i].letter, "frequency-letter"));
      const bars = make("div", undefined, "frequency-bars");
      for (const [name, entry] of [["ciphertext", c[i]], ["plaintext", p[i]]]) {
        const track = make("div", undefined, "frequency-track");
        const bar = make("span", undefined, `frequency-bar ${name}`);
        bar.style.width = `${entry.proportion / scale * 100}%`;
        const label = `${name}: ${entry.count} ${(entry.proportion * 100).toFixed(2)}%`;
        track.setAttribute("aria-label", `${entry.letter} ${label}`);
        track.title = label;
        track.append(bar);
        bars.append(track);
      }
      row.append(bars, make("span", `C ${c[i].count} (${(c[i].proportion * 100).toFixed(1)}%) / P ${p[i].count} (${(p[i].proportion * 100).toFixed(1)}%)`, "frequency-count"));
      chart.append(row);
    }
  }
  function fillRows(id, rows, emptyText, columnCount) {
    const table = $(id);
    table.replaceChildren();
    if (!rows.length) {
      const cell = make("td", emptyText);
      cell.colSpan = columnCount;
      const row = make("tr");
      row.append(cell);
      table.append(row);
      return;
    }
    for (const values of rows) {
      const row = make("tr");
      for (const value of values) row.append(make("td", String(value)));
      table.append(row);
    }
  }
  function renderPeriods() {
    if (!responseData) return;
    const source = $("workspace-source").value;
    const data = responseData[source];
    fillRows("workspace-repeats", data.repeated_patterns.map(row => [row.pattern, `${row.occurrences}${row.positions_truncated ? " (positions capped)" : ""}`, row.positions.join(", "), row.adjacent_distances.join(", "), row.supporting_periods.join(", ") || "none"]), "No repeated 3–5-letter patterns in this bounded sample.", 5);
    fillRows("workspace-periods", data.periods.map(row => [row.period, number(row.weighted_column_ic, 5), number(row.mean_column_ic, 5), `${(row.lag_match_rate * 100).toFixed(2)}%`, `${row.lag_matches} / ${row.lag_comparisons}`, row.kasiski_votes]), "Too few letters to compare periods.", 6);
    fillRows("workspace-estimates", data.key_length_estimates.map(row => [row.period, number(row.support_score, 3), number(row.weighted_column_ic, 5), row.kasiski_votes, row.min_column_letters, [row.insufficient_sample ? "Short / unreliable sample" : "Not verified", row.related_shorter_periods.length ? `Also inspect divisor(s) ${row.related_shorter_periods.join(", ")}` : ""].filter(Boolean).join("; ")]), "No key-length estimate available for this sample.", 6);
    $("workspace-estimate-note").textContent = `Source: ${source}. Model: ${responseData.reference.language}; expected letter IC ≈ ${number(responseData.reference.expected_ic, 5)}, uniform random ≈ ${number(responseData.reference.uniform_random_ic, 5)}. Support* is a heuristic, not a probability or recovered key. Interpret Vigenère lengths using ciphertext at the correct input layer; plaintext periods are just diagnostics.`
      + (data.key_length_estimates.length && data.key_length_estimates.every(row => row.support_score === 0) ? " None of the tested lengths has positive support by this formula." : "");
  }
  function renderAlignment() {
    const data = responseData.alignment;
    const table = $("workspace-alignment");
    table.replaceChildren();
    for (let offset = 0; offset < data.rows.length; offset += 20) {
      const block = data.rows.slice(offset, offset + 20);
      const row = make("tr");
      row.append(make("td", `${block[0].position}–${block[block.length - 1].position}`));
      for (const field of ["ciphertext", "plaintext", "key"]) {
        const cell = make("td", undefined, "alignment-letters");
        for (const item of block) {
          const char = make("span", item[field] || "·", item.matches === false && field === "ciphertext" ? "alignment-mismatch" : "");
          char.title = `Letter ${item.position}${item.matches === null ? ": equation not checked" : item.matches ? ": chosen equation agrees (not proof)" : `: mismatch; predicted ${item.predicted_ciphertext}`}`;
          cell.append(char);
        }
        row.append(cell);
      }
      table.append(row);
    }
    if (!data.rows.length) fillRows("workspace-alignment", [], "No letters at this display offset.", 4);
    $("workspace-alignment-note").textContent = `${data.detail} Model: ${data.model}; key sequence period: ${data.key_period ?? "none"}; key phase: ${data.key_offset}. `
      + (data.positions_checked ? `${data.positions_checked} displayed equations checked; ${data.mismatches} mismatches. A match still does not prove the reading.` : "No equations checked (a key or supported direct cipher may be missing).")
      + (!data.lengths_match ? " The normalized text lengths differ; this is not a one-to-one full-message alignment." : "")
      + (data.explicit_hypothesis ? " You selected a manual convention, not a verified cipher attribution." : "");
  }
  function render() {
    $("workspace-normalization").textContent = responseData.normalization;
    $("workspace-warnings").replaceChildren();
    for (const name of ["ciphertext", "plaintext"]) for (const warning of responseData[name].warnings) $("workspace-warnings").append(make("li", `${name}: ${warning}`));
    $("workspace-method").textContent = responseData.method;
    $("workspace-caveat").textContent = responseData.caveat;
    renderMetrics(); renderFrequency(); renderPeriods(); renderAlignment();
  }
  window.addEventListener("buttcrack-workspace-reset", reset);
  window.addEventListener("buttcrack-report", event => {
    stop();
    const report = event.detail.report;
    context = {ciphertext: event.detail.ciphertext, candidates: report.candidates && report.candidates.length ? report.candidates : report.best ? [report.best] : [], language: report.language || "english"};
    const selector = $("workspace-candidate");
    selector.replaceChildren();
    context.candidates.forEach((candidate, index) => {
      const option = make("option", `#${index + 1} · ${candidate.cipher} · rank score ${Number(candidate.confidence || 0).toFixed(3)}`);
      option.value = String(index); selector.append(option);
    });
    selector.disabled = !context.candidates.length;
    if (!context.candidates.length) selector.append(make("option", "Ciphertext only — no candidate selected"));
    setupCandidate(); analyze();
  });
  window.addEventListener("buttcrack-analyze-candidate", event => {
    if (!context.candidates[event.detail.index]) return;
    $("workspace-candidate").value = String(event.detail.index);
    setupCandidate(); analyze();
  });
  $("workspace-analyze").addEventListener("click", () => {
    const text = $("input").value;
    if (!text.trim()) { $("workspace-status").textContent = "Paste ciphertext first."; return; }
    reset(); context.ciphertext = text; context.language = $("language").value || "english";
    setupCandidate(); analyze();
  });
  $("workspace-candidate").addEventListener("change", () => { setupCandidate(); analyze(); });
  $("workspace-source").addEventListener("change", renderPeriods);
  $("workspace-max-period").addEventListener("change", analyze);
  $("workspace-apply").addEventListener("click", analyze);
})();
