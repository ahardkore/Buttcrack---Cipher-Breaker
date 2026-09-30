// Kryptos Cryptanalytic Suite Application Engine

let currentCipherId = "PK10";

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initCipherExplorer();
  initWorkbench();
  initBookReader();
  selectCipher("PK10");
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
// The data file is generated and verified by
// scripts/build_kryptos_app_data.py. Index it by id so the rest of the app can
// keep looking entries up by name.
const CIPHERS_DATA = Object.fromEntries(ENTRIES.map(e => [e.id, e]));

/** Quagmire III: Vigenere arithmetic inside a keyed alphabet's index space. */
function decryptQuagmire(ct, keyword, alphabet) {
  const idx = {};
  [...alphabet].forEach((c, i) => { idx[c] = i; });
  const ks = [...keyword].map(c => idx[c]).filter(v => v !== undefined);
  if (!ks.length) return "";
  let out = "", j = 0;
  for (const ch of ct) {
    if (idx[ch] === undefined) continue;
    out += alphabet[(idx[ch] - ks[j % ks.length] + 26) % 26];
    j++;
  }
  return out;
}

/** A sum of short wheels, added modulo 26 in the keyed alphabet. */
function decryptSumClock(ct, words, alphabet) {
  const idx = {};
  [...alphabet].forEach((c, i) => { idx[c] = i; });
  const wheels = words.map(w => [...w].map(c => idx[c]));
  let out = "", t = 0;
  for (const ch of ct) {
    if (idx[ch] === undefined) continue;
    let total = 0;
    for (const wheel of wheels) total += wheel[t % wheel.length];
    out += alphabet[((idx[ch] - total) % 26 + 26) % 26];
    t++;
  }
  return out;
}

/** Re-derive a solved entry in the browser and report whether it checks out.
 *
 * The point is not decoration. This app previously shipped seven fabricated
 * ciphertexts and could not have told you, because nothing ever tried to
 * reproduce a plaintext from one. Now the claim is tested in front of the
 * reader on every view.
 */
function verifyEntry(data) {
  if (!data.plaintext) return { state: "unsolved", text: "No published plaintext." };
  let recovered = null;
  if (data.id === "K1" || data.id === "K2") {
    recovered = decryptQuagmire(data.ciphertext, data.id === "K1" ? "PALIMPSEST" : "ABSCISSA", KRYPTOS_ALPHABET);
  } else if (data.id === "PK1") {
    recovered = decryptQuagmire(data.ciphertext, "PROVENANCE", KRYPTOS_ALPHABET);
  } else if (data.id === "PK3") {
    recovered = decryptSumClock(data.ciphertext, ["PENTIMENTO", "ORDINATE"], KRYPTOS_ALPHABET);
  }
  if (recovered !== null) {
    if (recovered === data.plaintext) {
      return { state: "verified", text: "Decrypted live in your browser with the published key; matches the plaintext exactly." };
    }
    let shared = 0;
    while (shared < recovered.length && recovered[shared] === data.plaintext[shared]) shared++;
    if (data.id === "K2" && shared >= 360) {
      return {
        state: "verified",
        text: `Decrypted live and matches for ${shared} characters. The panel then reads ` +
              `"${recovered.slice(shared)}" where the intended text reads "${data.plaintext.slice(shared)}" — ` +
              `Sanborn omitted a letter when cutting the copper, which he confirmed in 2006.`
      };
    }
    return { state: "failed", text: `Decryption diverges from the published plaintext at character ${shared}.` };
  }
  // Transpositions: the ciphertext must be an exact anagram of the plaintext.
  const tally = s => { const m = {}; for (const c of s) m[c] = (m[c] || 0) + 1; return m; };
  const a = tally(data.ciphertext), b = tally(data.plaintext);
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  const anagram = [...keys].every(k => a[k] === b[k]);
  if (data.provenance === "published") {
    return { state: "published", text: data.verification };
  }
  return anagram
    ? { state: "verified", text: "Ciphertext is an exact anagram of the plaintext, as a transposition must be." }
    : { state: "failed", text: "Ciphertext is not an anagram of the plaintext." };
}

function initCipherExplorer() {
  const sidebar = document.getElementById("cipher-sidebar-list");
  if (!sidebar) return;

  sidebar.innerHTML = "";
  // Groups come from the data, so a new entry appears without editing this.
  for (const group of [...new Set(ENTRIES.map(e => e.group))]) {
    const title = document.createElement("div");
    title.className = "sidebar-category-title";
    title.textContent = group;
    sidebar.appendChild(title);
    ENTRIES.filter(e => e.group === group)
      .forEach(data => sidebar.appendChild(createSidebarItem(data)));
  }
}

function createSidebarItem(data) {
  const div = document.createElement("div");
  div.className = "cipher-nav-item";
  div.dataset.id = data.id;

  let badgeClass = "badge-unsolved";
  if (data.status === "SOLVED") badgeClass = "badge-solved";
  else if (data.status.includes("FRONTIER")) badgeClass = "badge-frontier";
  else if (data.status.includes("CUSTODY")) badgeClass = "badge-custody";

  const label = data.title.includes("—") ? data.title.split("—")[1].trim() : data.title;
  div.innerHTML = `
    <div class="cipher-name">${data.id}: ${label}</div>
    <div class="cipher-badge ${badgeClass}">${data.provenance || data.status}</div>
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
  document.getElementById("detail-subtitle").textContent = `${data.group} | ${data.mechanism} | ${data.length} characters`;

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
  document.getElementById("detail-pt").textContent = formatWrapped(pt, 42);
  document.getElementById("detail-key").textContent = data.key || "See Mathematical Clock & Transposition Invariants";
  document.getElementById("detail-notes").textContent = data.notes || "";

  // Live verification, shown to the reader rather than asserted.
  const check = verifyEntry(data);
  const box = document.getElementById("detail-verification");
  if (box) {
    box.className = `verification verification-${check.state}`;
    const label = { verified: "VERIFIED IN BROWSER", published: "PUBLISHED, NOT VERIFIED HERE",
                    unsolved: "UNSOLVED", failed: "CHECK FAILED" }[check.state];
    box.innerHTML = `<strong>${label}</strong><span>${check.text}</span>`;
  }
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
    { title: "Chapter 2: Decoupling and Breaking PK8 (N = 153)", target: "book-ch-2" },
    { title: "Chapter 3: Cracking PK9 — The 135-Character Artisan Text (N = 144)", target: "book-ch-3" },
    { title: "Chapter 4: Cracking PK10 — The Modular Copper Triptych (N = 504)", target: "book-ch-4" },
    { title: "Chapter 5: The Dual-Cipher GPS Sculpture Theorem", target: "book-ch-5" },
    { title: "Chapter 6: Grand Cryptosystem Synthesis & Universal Invariants", target: "book-ch-6" },
    { title: "Chapter 7: Master Solutions Database & Verification Manifest", target: "book-ch-7" },
    { title: "Epilogue: Complete Suite Reproducibility Assurance", target: "book-ch-epilogue" }
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
