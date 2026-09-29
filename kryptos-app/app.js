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
  document.getElementById("detail-pt").textContent = formatWrapped(pt, 42);
  document.getElementById("detail-key").textContent = data.key || "See Mathematical Clock & Transposition Invariants";
  document.getElementById("detail-notes").textContent = data.notes || "";
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
