// Kryptos Cryptanalytic Suite Application Engine

let currentCipherId = "PK8";

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initCipherExplorer();
  initWorkbench();
  initBookReader();
  initUnsolvedArchive();
  selectCipher("PK8");
  const worksheet = document.getElementById("print-symbol-worksheet");
  if (worksheet) worksheet.addEventListener("click", () => window.print());
  const demo = document.getElementById("run-demo");
  const scoreRun = document.getElementById("score-run");
  if (scoreRun) scoreRun.addEventListener("click", () => {
    const text = document.getElementById("score-input").value.toUpperCase().replace(/[^A-Z]/g, "");
    const out = document.getElementById("score-output");
    if (!text) { out.textContent = "Enter candidate text first."; return; }
    const counts = {}; Array.from(text).forEach(ch => counts[ch] = (counts[ch] || 0) + 1);
    const n = text.length;
    const ioc = n > 1 ? Object.values(counts).reduce((sum, v) => sum + v*(v-1), 0)/(n*(n-1)) : 0;
    const entropy = -Object.values(counts).reduce((sum, v) => { const p=v/n; return sum+p*Math.log2(p); }, 0);
    const common = ["THE","AND","ING","ION","THAT","THIS","WITH"].filter(x => text.includes(x)).length;
    const cards = [["Letters", n], ["Monogram IoC", ioc.toFixed(4)], ["Entropy", entropy.toFixed(3)], ["Common n-grams", `${common}/7`], ["Random baseline", "not calibrated" ]];
    out.innerHTML = cards.map(([label, value]) => `<article><strong>${label}</strong><span>${value}</span></article>`).join("");
  });

  const verifyRun = document.getElementById("verify-run");
  if (verifyRun) verifyRun.addEventListener("click", () => {
    const expected = document.getElementById("verify-expected").value.replace(/\\s/g, "");
    const produced = document.getElementById("verify-produced").value.replace(/\\s/g, "");
    const limit = Math.min(expected.length, produced.length);
    let mismatch = -1;
    for (let i = 0; i < limit; i++) if (expected[i] !== produced[i]) { mismatch = i; break; }
    if (mismatch < 0 && expected.length === produced.length) document.getElementById("verify-output").textContent = "VERIFIED: exact normalized round trip.";
    else if (mismatch < 0) document.getElementById("verify-output").textContent = `FAIL: length mismatch at ${limit}; expected ${expected.length}, produced ${produced.length}.`;
    else document.getElementById("verify-output").textContent = `FAIL: first mismatch at position ${mismatch}; expected ${expected[mismatch]}, produced ${produced[mismatch]}.`;
  });
  const cribRun = document.getElementById("crib-run");
  if (cribRun) cribRun.addEventListener("click", () => {
    const c = document.getElementById("crib-cipher").value.toUpperCase().replace(/[^A-Z]/g, "");
    const p = document.getElementById("crib-text").value.toUpperCase().replace(/[^A-Z]/g, "");
    const offset = Math.max(0, Number(document.getElementById("crib-offset").value) || 0);
    const shifts = Array.from(p, (ch, i) => c[offset+i] ? (c.charCodeAt(offset+i)-ch.charCodeAt(0)+26)%26 : null);
    document.getElementById("crib-output").textContent = shifts.includes(null) ? "Placement exceeds ciphertext length." : `implied shifts: ${shifts.join(", ")}\nperiod check: worksheet only — inspect repeated residues before accepting.`;
  });
  function simpleTranspose(text, key, decrypt) {
    const order = Array.from(key.toUpperCase()).map((ch, i) => [ch, i]).sort((a,b) => a[0].localeCompare(b[0]) || a[1]-b[1]).map(x => x[1]);
    const cols = key.length; if (!cols || text.length % cols) throw new Error("text length must fill the keyword grid");
    const rows = text.length / cols, grid = Array.from({length: rows}, () => Array(cols).fill("")); let q = 0;
    if (!decrypt) return order.map(c => Array.from({length: rows}, (_, r) => text[r*cols+c])).flat().join("");
    for (const c of order) for (let r=0; r<rows; r++) grid[r][c] = text[q++];
    return grid.flat().join("");
  }
  ["transpose-enc", "transpose-dec"].forEach(id => { const button = document.getElementById(id); if (button) button.addEventListener("click", () => { try { document.getElementById("transpose-output").textContent = simpleTranspose(document.getElementById("transpose-text").value.replace(/\\s/g, ""), document.getElementById("transpose-key").value, id.endsWith("dec")); } catch (e) { document.getElementById("transpose-output").textContent = `Input error: ${e.message}`; } }); });

  const assistantRun = document.getElementById("assistant-run");
  const assistantSave = document.getElementById("assistant-save");
  let assistantProject = null;
  const assistantLoad = document.getElementById("assistant-load");
  if (assistantLoad) assistantLoad.addEventListener("change", () => {
    const file = assistantLoad.files && assistantLoad.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const loaded = JSON.parse(reader.result);
        if (!loaded || typeof loaded.ciphertext !== "string") throw new Error("missing ciphertext");
        document.getElementById("assistant-input").value = loaded.ciphertext;
        assistantProject = loaded;
        document.getElementById("assistant-save").disabled = false;
        document.getElementById("assistant-output").textContent = "Session loaded. Run analysis again to refresh recommendations.";
      } catch (_) {
        document.getElementById("assistant-output").textContent = "Could not load that session JSON.";
      }
    };
    reader.readAsText(file);
  });
  if (assistantSave) assistantSave.addEventListener("click", () => {
    if (!assistantProject) return;
    const blob = new Blob([JSON.stringify(assistantProject, null, 2)], {type: "application/json"});
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "buttcrack-analysis.kryptos-project.json";
    link.click();
    URL.revokeObjectURL(link.href);
  });
  if (assistantRun) assistantRun.addEventListener("click", () => {
    const raw = document.getElementById("assistant-input").value.toUpperCase();
    const text = raw.replace(/[^A-Z]/g, "");
    const output = document.getElementById("assistant-output");
    if (!text) { output.textContent = "Enter ciphertext first. No text leaves this browser."; return; }
    const ioc = calculateIoC(text);
    const hints = [];
    if (text.length < 20) hints.push("Short sample: use hand cribs and repeated-symbol review; statistics are underdetermined.");
    else if (ioc >= 0.06) hints.push(`IoC ${ioc.toFixed(4)}: compare substitution-family candidates.`);
    else hints.push(`IoC ${ioc.toFixed(4)}: screen periodic and polyalphabetic models.`);
    if (text.length >= 50) hints.push("Length supports a bounded transposition comparison.");
    hints.push("Status: recommendations only. Require exact round-trip verification.");
    assistantProject = {schema: "buttcrack-project/web-v1", ciphertext: raw, normalization: "A-Z only", statistics: {letters: text.length, ioc: ioc}, recommendations: hints, status: "recommendations_only"};
    if (assistantSave) assistantSave.disabled = false;
    output.textContent = `LOCAL, OFFLINE ANALYSIS\nletters=${text.length}\n` + hints.map((h, i) => `${i + 1}. ${h}`).join("\n");
  });
  if (demo) demo.addEventListener("click", () => {
    const raw = document.getElementById("demo-text").value.toUpperCase().replace(/[^A-Z]/g, "");
    const shift = ((Number(document.getElementById("demo-shift").value) || 0) % 26 + 26) % 26;
    const steps = Array.from(raw, ch => `${ch} → ${String.fromCharCode((ch.charCodeAt(0) - 65 + shift) % 26 + 65)}`);
    document.getElementById("demo-output").textContent = steps.length ? steps.join("    ") : "Enter A–Z letters to see the transformation.";
  });
});

// Navigation Tab Management
function initNavigation() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

      tab.classList.add("active");
      const targetPane = document.getElementById(tab.dataset.target);
      if (targetPane) targetPane.classList.add("active");
    });
  });
}

// Cipher Explorer Setup
function initCipherExplorer() {
  const sidebar = document.getElementById("cipher-sidebar-list");
  if (!sidebar) return;

  sidebar.innerHTML = "";

  // 1. Paradigm Kryptos Section
  const pkTitle = document.createElement("div");
  pkTitle.className = "sidebar-category-title";
  pkTitle.textContent = "Paradigm Kryptos (PK1 - PK10)";
  sidebar.appendChild(pkTitle);

  const pkKeys = ["PK10", "PK9", "PK8", "PK7", "PK6", "PK5", "PK4", "PK3", "PK2", "PK1"];
  pkKeys.forEach(id => {
    const data = CIPHERS_DATA[id];
    const item = createSidebarItem(data);
    sidebar.appendChild(item);
  });

  // 2. CIA Sculpture Section
  const ciaTitle = document.createElement("div");
  ciaTitle.className = "sidebar-category-title";
  ciaTitle.textContent = "CIA Sculpture (K1 - K4)";
  sidebar.appendChild(ciaTitle);

  const ciaKeys = ["K4", "K3", "K2", "K1"];
  ciaKeys.forEach(id => {
    const data = CIPHERS_DATA[id];
    const item = createSidebarItem(data);
    sidebar.appendChild(item);
  });
}

function createSidebarItem(data) {
  const div = document.createElement("div");
  div.className = "cipher-nav-item";
  div.dataset.id = data.id;

  let badgeClass = "badge-unsolved";
  if (data.status === "SOLVED") badgeClass = "badge-solved";
  else if (data.status.includes("FRONTIER")) badgeClass = "badge-frontier";
  else if (data.status.includes("CUSTODY")) badgeClass = "badge-custody";

  div.innerHTML = `
    <div class="cipher-name">${data.id}: ${data.title.split("—")[1] || data.id}</div>
    <div class="cipher-badge ${badgeClass}">${data.status.split(" ")[0]}</div>
  `;

  div.addEventListener("click", () => selectCipher(data.id));
  return div;
}

function selectCipher(id) {
  currentCipherId = id;
  const data = CIPHERS_DATA[id];
  if (!data) return;

  // Highlight active sidebar item
  document.querySelectorAll(".cipher-nav-item").forEach(item => {
    item.classList.toggle("active", item.dataset.id === id);
  });

  // Calculate statistics
  const ct = data.ciphertext || "";
  const pt = data.plaintext || "";
  const ioc = calculateIoC(ct);
  const entropy = calculateEntropy(ct);
  const rareCount = countRareLetters(ct);

  // Render detail view
  document.getElementById("detail-title").textContent = data.title;
  document.getElementById("detail-subtitle").textContent = `${data.category} | ${data.mechanism} | Length: ${data.length} characters`;

  let badgeClass = "badge-unsolved";
  if (data.status === "SOLVED") badgeClass = "badge-solved";
  else if (data.status.includes("FRONTIER")) badgeClass = "badge-frontier";
  else if (data.status.includes("CUSTODY")) badgeClass = "badge-custody";

  const statusBadge = document.getElementById("detail-status-badge");
  statusBadge.className = `cipher-badge ${badgeClass}`;
  statusBadge.textContent = data.status;

  document.getElementById("stat-len").textContent = data.length;
  document.getElementById("stat-ioc").textContent = ioc.toFixed(5);
  document.getElementById("stat-entropy").textContent = `${entropy.toFixed(3)} b`;
  document.getElementById("stat-rare").textContent = `${rareCount} (${(rareCount/ct.length*100).toFixed(1)}%)`;

  document.getElementById("detail-ct").textContent = formatWrapped(ct, 42);
  document.getElementById("detail-key").textContent = data.key || "No verified key.";
  document.getElementById("detail-notes").textContent = data.notes || "";

  const challengeLink = document.getElementById("detail-challenge-link");
  challengeLink.hidden = !data.challengeUrl;
  if (data.challengeUrl) {
    challengeLink.href = data.challengeUrl;
    challengeLink.textContent = `Open official ${data.id} challenge ↗`;
  }

  const plaintextHeading = document.getElementById("detail-pt-heading");
  const plaintextDisplay = document.getElementById("detail-pt");
  if (pt) {
    plaintextHeading.textContent = "Verified Plaintext";
    plaintextDisplay.classList.remove("frontier-display");
    plaintextDisplay.classList.add("plaintext-highlight");
    plaintextDisplay.textContent = formatWrapped(pt, 42);
  } else {
    plaintextHeading.textContent = "Plaintext Status";
    plaintextDisplay.classList.remove("plaintext-highlight");
    plaintextDisplay.classList.add("frontier-display");
    plaintextDisplay.textContent = data.frontier || "No verified plaintext has been recovered.";
  }

  const methodSection = document.getElementById("detail-method-section");
  methodSection.hidden = !data.method;
  document.getElementById("detail-method").textContent = data.method || "";
}

// Famous Unsolved Cipher & Script Archive
function initUnsolvedArchive() {
  const grid = document.getElementById("unsolved-archive-grid");
  if (!grid || typeof UNSOLVED_CIPHER_ARCHIVE === "undefined") return;

  grid.innerHTML = "";
  UNSOLVED_CIPHER_ARCHIVE.forEach(item => {
    const card = document.createElement("article");
    card.className = "archive-card";

    const meta = document.createElement("div");
    meta.className = "archive-meta";
    const kind = document.createElement("span");
    kind.textContent = item.kind;
    const status = document.createElement("span");
    status.className = "cipher-badge badge-unsolved";
    status.textContent = "UNSOLVED";
    meta.append(kind, status);

    const title = document.createElement("h3");
    title.textContent = item.title;
    const date = document.createElement("p");
    date.className = "archive-date";
    date.textContent = item.date;
    const summary = document.createElement("p");
    summary.textContent = item.summary;

    const boundary = document.createElement("p");
    boundary.className = "archive-boundary";
    const label = document.createElement("strong");
    label.textContent = "Verification boundary: ";
    boundary.append(label, item.boundary);

    const source = document.createElement("a");
    source.className = "archive-source";
    source.href = item.sourceUrl;
    source.target = "_blank";
    source.rel = "noopener noreferrer";
    source.textContent = `${item.sourceLabel} ↗`;

    card.append(meta, title, date, summary, boundary, source);
    grid.appendChild(card);
  });
}

// Math & Cryptanalysis Helpers
function calculateIoC(text) {
  if (!text || text.length <= 1) return 0;
  const counts = {};
  for (const c of text) {
    if (c >= 'A' && c <= 'Z') counts[c] = (counts[c] || 0) + 1;
  }
  let sumPairs = 0;
  for (const k in counts) sumPairs += counts[k] * (counts[k] - 1);
  return sumPairs / (text.length * (text.length - 1));
}

function calculateEntropy(text) {
  if (!text || text.length === 0) return 0;
  const counts = {};
  for (const c of text) {
    if (c >= 'A' && c <= 'Z') counts[c] = (counts[c] || 0) + 1;
  }
  let ent = 0;
  const n = text.length;
  for (const k in counts) {
    const p = counts[k] / n;
    ent -= p * Math.log2(p);
  }
  return ent;
}

function countRareLetters(text) {
  if (!text) return 0;
  let count = 0;
  for (const c of text) {
    if ("JQXZ".includes(c)) count++;
  }
  return count;
}

function formatWrapped(text, width = 42) {
  if (!text) return "";
  let res = "";
  for (let i = 0; i < text.length; i += width) {
    res += text.substring(i, i + width) + "\n";
  }
  return res.trim();
}

// Workbench Setup
function initWorkbench() {
  const btnDecrypt = document.getElementById("wb-btn-decrypt");
  if (!btnDecrypt) return;

  btnDecrypt.addEventListener("click", () => {
    const ct = document.getElementById("wb-input-ct").value.trim().toUpperCase().replace(/[^A-Z]/g, '');
    const key = document.getElementById("wb-input-key").value.trim().toUpperCase().replace(/[^A-Z]/g, '');
    const algo = document.getElementById("wb-algo-select").value;

    if (!ct || !key) {
      alert("Please provide both ciphertext and key.");
      return;
    }

    let pt = "";
    if (algo === "vigenere-kr") {
      pt = decryptQuagmireIII(ct, key);
    } else if (algo === "vigenere-std") {
      pt = decryptVigenereStd(ct, key);
    } else if (algo === "columnar") {
      pt = decryptColumnar(ct, key);
    }

    document.getElementById("wb-output-pt").textContent = formatWrapped(pt, 42);
    document.getElementById("wb-res-ioc").textContent = calculateIoC(pt).toFixed(5);
    document.getElementById("wb-res-ent").textContent = `${calculateEntropy(pt).toFixed(3)} b`;
    document.getElementById("wb-res-rare").textContent = countRareLetters(pt);
  });
}

function decryptQuagmireIII(ct, key) {
  let pt = "";
  for (let i = 0; i < ct.length; i++) {
    const cIdx = KRYPTOS_ALPHABET.indexOf(ct[i]);
    const kIdx = KRYPTOS_ALPHABET.indexOf(key[i % key.length]);
    if (cIdx === -1 || kIdx === -1) { pt += ct[i]; continue; }
    const pIdx = (cIdx - kIdx + 26) % 26;
    pt += KRYPTOS_ALPHABET[pIdx];
  }
  return pt;
}

function decryptVigenereStd(ct, key) {
  let pt = "";
  for (let i = 0; i < ct.length; i++) {
    const cIdx = ct.charCodeAt(i) - 65;
    const kIdx = key.charCodeAt(i % key.length) - 65;
    const pIdx = (cIdx - kIdx + 26) % 26;
    pt += String.fromCharCode(pIdx + 65);
  }
  return pt;
}

function decryptColumnar(ct, key) {
  const W = key.length;
  const H = Math.ceil(ct.length / W);
  // Simple order by sorting key
  const order = key.split('').map((c, i) => ({ c, i })).sort((a, b) => a.c.localeCompare(b.c)).map(x => x.i);
  const grid = Array.from({ length: H }, () => Array(W).fill(''));
  let idx = 0;
  for (let c = 0; c < W; c++) {
    const colIdx = order.indexOf(c);
    for (let r = 0; r < H; r++) {
      if (idx < ct.length) grid[r][colIdx] = ct[idx++];
    }
  }
  let res = "";
  for (let r = 0; r < H; r++) {
    for (let c = 0; c < W; c++) res += grid[r][c];
  }
  return res;
}

// Book Reader Setup
function initBookReader() {
  const chapters = [
    { title: "Prologue: The CIA Sculpture & The 36-Year Mystery", target: "book-ch-prologue" },
    { title: "Chapter 1: The Narrative Arc of Paradigm Kryptos (PK1 – PK7)", target: "book-ch-1" },
    { title: "Chapter 2: PK8 — Verified Solution & Method", target: "book-ch-2" },
    { title: "Chapter 3: PK9 — Independently Verified Construction", target: "book-ch-3" },
    { title: "Chapter 4: PK10 — Independently Verified Construction", target: "book-ch-4" },
    { title: "Chapter 5: Research-Integrity Rules", target: "book-ch-5" },
    { title: "Chapter 6: PK9 Recovery and Provenance", target: "book-ch-6" },
    { title: "Chapter 7: Verification Commands", target: "book-ch-7" },
    { title: "Epilogue: Current Solution Status", target: "book-ch-epilogue" }
  ];

  const tocList = document.getElementById("book-toc-list");
  if (!tocList) return;

  tocList.innerHTML = "";
  chapters.forEach((ch, idx) => {
    const div = document.createElement("div");
    div.className = `toc-item ${idx === 0 ? 'active' : ''}`;
    div.textContent = ch.title;
    div.addEventListener("click", () => {
      document.querySelectorAll(".toc-item").forEach(item => item.classList.remove("active"));
      div.classList.add("active");
      const targetElem = document.getElementById(ch.target);
      if (targetElem) targetElem.scrollIntoView({ behavior: 'smooth' });
    });
    tocList.appendChild(div);
  });
}
