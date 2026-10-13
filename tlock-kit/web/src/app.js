/**
 * web/src/app.js — DOM wiring for the browser unlocker. Bundled by esbuild
 * into web/app.bundle.js (IIFE), which lets the page run from file:// too.
 */
import { PAGES_BASE_URL, parseTlockStanza, decryptArmored, getStatus, roundTime, fmtDuration } from "./core.js";

const $ = (id) => document.getElementById(id);
const err = (msg) => {
  const box = $("err");
  box.textContent = msg ? String(msg) : "";
  box.style.display = msg ? "block" : "none";
};

let armored = null; // file text
let stanza = null; // { round, chainHash }
let targetMs = null;
let timer = null;

function setStatus(html, cls = "") {
  const el = $("status");
  el.className = cls;
  el.innerHTML = html;
}

function tick() {
  if (targetMs == null) return;
  const left = targetMs - Date.now();
  if (left > 0) {
    $("countdown").textContent = `${fmtDuration(left)} to go`;
    $("unlock").disabled = true;
    setStatus(`<b>LOCKED</b> — the key (drand round ${stanza.round}) does not exist yet.`, "locked");
  } else {
    $("countdown").textContent = "unlock round reached";
    $("unlock").disabled = false;
    setStatus(`<b>UNLOCK ROUND REACHED</b> — you can decrypt now.`, "ready");
  }
}

async function onFile(text, name) {
  err("");
  armored = text.trim();
  stanza = parseTlockStanza(armored);
  if (!stanza) {
    $("fileinfo").textContent = `${name}: not a tlock age file (no tlock stanza found).`;
    setStatus("Load the file again — it needs an age/tlock header.", "locked");
    return;
  }
  $("fileinfo").innerHTML =
    `<b>${name}</b><br>round <b>${stanza.round}</b> on chain <code>${stanza.chainHash.slice(0, 16)}…</code>` +
    (stanza.chainHash === PAGES_BASE_URL.split("/").pop() ? " (drand quicknet)" : "");
  targetMs = roundTime(
    { genesis_time: 1692803367, period: 3, hash: stanza.chainHash }, // quicknet defaults; refined after /info
    stanza.round
  );
  setStatus(`unlock time: ${new Date(targetMs).toISOString()} (${new Date(targetMs).toLocaleString()})`);
  updateTargetFromChain();
  refresh();
  if (!timer) timer = setInterval(tick, 1000);
  tick();
}

async function updateTargetFromChain() {
  try {
    const { info } = await getStatus($("baseurl").value);
    if (info.hash === stanza?.chainHash) {
      targetMs = roundTime(info, stanza.round);
      tick();
    }
  } catch {
    /* offline: keep the quicknet default */
  }
}

async function refresh() {
  if (!stanza) return;
  try {
    const { info, latest } = await getStatus($("baseurl").value);
    targetMs = roundTime(info, stanza.round);
    $("chaininfo").textContent = `${info.metadata?.beaconID ?? info.hash} · period ${info.period}s · latest round ${latest.round}`;
    tick();
  } catch (e) {
    $("chaininfo").textContent = "live chain status unavailable from this browser (CORS/network). Use the offline beacon file below — decryption then works with no network at all.";
  }
}

async function unlock() {
  err("");
  $("output").textContent = "";
  setStatus("decrypting…");
  try {
    const bytes = await decryptArmored(armored, $("baseurl").value);
    const text = new TextDecoder().decode(bytes);
    $("output").textContent = text;
    const blob = new Blob([bytes]);
    const a = $("download");
    a.href = URL.createObjectURL(blob);
    a.download = "plaintext.txt";
    a.style.display = "inline-block";
    setStatus(`<b>UNLOCKED</b> — ${bytes.length} bytes.`, "ready");
  } catch (e) {
    const msg = String(e?.message ?? e);
    setStatus("not decrypted", "locked");
    err(
      /too early/i.test(msg)
        ? `${msg}\nThe unlock round has not been emitted by drand yet — retry after the time shown above.`
        : `${msg}\nIf this is a network/CORS error, save the beacon JSON from\n${$("baseurl").value.replace(/\/+$/, "")}/public/${stanza.round}\nin a browser tab, then load it under "offline beacon file".`
    );
  }
}

async function onBeaconFile(text, name) {
  err("");
  try {
    const beacon = JSON.parse(text);
    setStatus(`offline beacon loaded: round ${beacon.round} — decrypting…`);
    const bytes = await decryptArmored(armored, null, { beacon });
    $("output").textContent = new TextDecoder().decode(bytes);
    const blob = new Blob([bytes]);
    const a = $("download");
    a.href = URL.createObjectURL(blob);
    a.download = "plaintext.txt";
    a.style.display = "inline-block";
    setStatus(`<b>UNLOCKED (offline)</b> from ${name} — ${bytes.length} bytes.`, "ready");
  } catch (e) {
    setStatus("offline decryption failed", "locked");
    err(`${e?.message ?? e}`);
  }
}

function init() {
  $("file").addEventListener("change", async (ev) => {
    const f = ev.target.files?.[0];
    if (f) onFile(await f.text(), f.name);
  });
  $("drop").addEventListener("dragover", (ev) => {
    ev.preventDefault();
    $("drop").classList.add("hot");
  });
  $("drop").addEventListener("dragleave", () => $("drop").classList.remove("hot"));
  $("drop").addEventListener("drop", async (ev) => {
    ev.preventDefault();
    $("drop").classList.remove("hot");
    const f = ev.dataTransfer?.files?.[0];
    if (f) onFile(await f.text(), f.name);
  });
  $("baseurl").addEventListener("change", refresh);
  $("refresh").addEventListener("click", refresh);
  $("unlock").addEventListener("click", unlock);
  $("beaconfile").addEventListener("change", async (ev) => {
    const f = ev.target.files?.[0];
    if (f) onBeaconFile(await f.text(), f.name);
  });
}

if (typeof document !== "undefined") init();
