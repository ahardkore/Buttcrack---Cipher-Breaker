#!/usr/bin/env node
/**
 * unlock.mjs — open a drand *tlock* (timelock) age file.
 *
 * The file is an AGE-encrypted file whose key is the BLS signature of a future
 * drand round (a "timelock"). Consequences:
 *
 *   * Before that round is published  -> the key does not exist anywhere yet.
 *     No password, no brute force, nothing to crack; you must wait.
 *   * After it is published           -> this script fetches the signature
 *     from a drand API, timelock-decrypts, and writes the plaintext.
 *
 * Usage:
 *   node unlock.mjs [file.age] [out.txt]
 *
 * Defaults: file = what-is-locked.age, out = <file without .age>.txt
 *
 * Environment:
 *   DRAND_CHAIN_URL   drand chain base URL (default: quicknet on api.drand.sh).
 *                     Alternates: https://api2.drand.sh/<chain>,
 *                     https://api3.drand.sh/<chain>,
 *                     https://drand.cloudflare.com/<chain>,
 *                     or a local mock: http://127.0.0.1:42133
 *
 * Requires: node >= 18 and `npm install` in this folder once
 * (tlock-js 0.9.0 — the drand team's implementation of the tlock spec).
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import {
  timelockDecrypt,
  mainnetClient,
  HttpChainClient,
  HttpCachingChain,
} from "tlock-js";

const DEFAULT_CHAIN_URL =
  "https://api.drand.sh/52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971";

const file = process.argv[2] ?? "what-is-locked.age";
const out = process.argv[3] ?? file.replace(/\.age$/i, "") + ".txt";
const chainUrl = (process.env.DRAND_CHAIN_URL ?? DEFAULT_CHAIN_URL).replace(/\/$/, "");

if (!existsSync(file)) {
  console.error(`error: ${file} not found. Save the BEGIN AGE ENCRYPTED FILE…END block from chat into ${file} first.`);
  process.exit(1);
}

const armored = readFileSync(file, "utf8").trim();
if (!armored.includes("BEGIN AGE ENCRYPTED FILE")) {
  console.error(`error: ${file} is not an ASCII-armored age file (missing BEGIN AGE ENCRYPTED FILE header).`);
  process.exit(1);
}

// The whole age payload (header included) is base64 inside the armor, so the
// stanza has to be read from the decoded text, not from the armored file.
function decodeArmorText(text) {
  const b64 = text
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith("-----"))
    .join("");
  return Buffer.from(b64, "base64").toString("latin1");
}
const headerText = decodeArmorText(armored);
const stanza = headerText.match(/->\s+tlock\s+(\d+)\s+([0-9a-f]{64})/);
if (!stanza) {
  console.error("error: no tlock recipient stanza found — this is not a timelock file (maybe a normal age/passphrase file).");
  process.exit(1);
}
const targetRound = Number(stanza[1]);
const chainHash = stanza[2];
console.log(`file        : ${file}`);
console.log(`target round: ${targetRound}`);
console.log(`chain       : ${chainHash}${chainHash === "52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971" ? " (drand quicknet, League of Entropy mainnet)" : ""}`);
console.log(`chain url   : ${chainUrl}`);

// ---- informational status (uses the same base URL as decryption) ----------
let secsLeft = null;
let unlockMs = null;
try {
  const info = await (await fetch(`${chainUrl}/info`)).json();
  const latest = await (await fetch(`${chainUrl}/public/latest`)).json();
  unlockMs = (info.genesis_time + (targetRound - 1) * info.period) * 1000;
  const roundsLeft = targetRound - latest.round;
  secsLeft = roundsLeft * info.period;
  console.log(`latest round: ${latest.round}`);
  console.log(`unlock time : ${new Date(unlockMs).toISOString()}`);
  console.log(
    secsLeft > 0
      ? `status      : LOCKED — ${roundsLeft} rounds (${secsLeft}s ≈ ${(secsLeft / 86400).toFixed(2)} days) to go`
      : `status      : unlock round reached — attempting decryption…`
  );
} catch (err) {
  console.warn(`warning: could not fetch chain status from ${chainUrl} (${err?.message ?? err}); attempting decryption anyway.`);
}

// ---- decryption ------------------------------------------------------------
function makeClient(url) {
  if (url === DEFAULT_CHAIN_URL) return mainnetClient(); // verified quicknet params built in
  const opts = { disableBeaconVerification: false, noCache: false };
  const chain = new HttpCachingChain(url, opts);
  return new HttpChainClient(chain, opts);
}

try {
  const plaintext = await timelockDecrypt(armored, makeClient(chainUrl));
  writeFileSync(out, plaintext);
  console.log(`\nUNLOCKED ✔  plaintext written to ${out} (${plaintext.length} bytes)`);
  const preview = plaintext.subarray(0, 4000).toString("utf8");
  console.log(`\n--- first ${Math.min(4000, plaintext.length)} bytes ---\n${preview}\n--- end of preview ---`);
} catch (err) {
  const msg = String(err?.message ?? err);
  console.error(`\nnot decrypted: ${msg}`);
  if (secsLeft !== null && secsLeft > 0) {
    console.error(`drand has not yet produced round ${targetRound}. Re-run this script after ${new Date(unlockMs).toISOString()}.`);
    console.error(`The file is fine and so is the script — the key simply does not exist yet.`);
  } else if (/too early/i.test(msg)) {
    console.error(`drand has not yet produced round ${targetRound} (status fetch was unavailable, but the library says it is too early). Re-run later.`);
  } else {
    console.error(`The unlock round should exist, but fetch/decrypt failed. Check network access to ${chainUrl}, or use the offline procedure in README.md.`);
  }
  process.exit(2);
}
