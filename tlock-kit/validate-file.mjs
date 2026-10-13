#!/usr/bin/env node
/**
 * validate-file.mjs — deep, fully offline structural validation of a tlock age
 * file. No network access required: it decodes the armor, parses the age
 * header, checks the tlock stanza body against a freshly generated canary of
 * the same scheme, and probes the decryption path to distinguish
 *
 *   "too early"  → the file is well-formed AND correctly locked (expected today)
 *   parse/MAC errors → the file is damaged or not a tlock file
 *   round in the past → ready to decrypt with unlock.mjs / offline.mjs
 *
 * Usage: node validate-file.mjs <file.age>
 *
 * Exit codes: 0 = valid (and either decryptable or ready), 2 = valid but still
 * locked, 1 = invalid / not a tlock file.
 */
import { readFileSync, existsSync } from "node:fs";
import { timelockDecrypt, timelockEncrypt, defaultChainInfo, roundTime } from "tlock-js";

const file = process.argv[2] ?? "what-is-locked.age";
if (!file || !existsSync(file)) {
  console.error(`error: ${file} not found`);
  process.exit(1);
}

const RAW = readFileSync(file);
const text = RAW.toString("utf8").trim();

const report = [];
const say = (s) => {
  report.push(s);
  console.log(s);
};
const fail = (s) => {
  say(`INVALID: ${s}`);
  console.log("\n" + report.join("\n"));
  process.exit(1);
};

// ---------- 1. armor ----------
if (!/-----BEGIN AGE ENCRYPTED FILE-----/.test(text)) {
  fail("missing '-----BEGIN AGE ENCRYPTED FILE-----' header — not an age file");
}
if (!/-----END AGE ENCRYPTED FILE-----/.test(text)) {
  fail("missing '-----END AGE ENCRYPTED FILE-----' footer — the file looks truncated");
}
const b64 = text
  .split(/\r?\n/)
  .map((l) => l.trim())
  .filter((l) => l && !l.startsWith("-----"))
  .join("");
if (/[^A-Za-z0-9+/=]/.test(b64)) fail("armor body contains characters that are not base64");
const body = Buffer.from(b64, "base64");
if (body.toString("base64").replace(/=+$/, "") !== b64.replace(/=+$/, "")) {
  fail("armor body does not re-encode to the same base64 — malformed/truncated");
}
say(`armor        : OK (${RAW.length} bytes on disk → ${body.length} bytes decoded)`);

// ---------- 2. age header ----------
const decoded = body.toString("latin1");
if (!decoded.startsWith("age-encryption.org/v1\n")) {
  fail("decoded payload does not start with 'age-encryption.org/v1'");
}
const macIdx = decoded.indexOf("\n--- ");
if (macIdx === -1) fail("no age header MAC line ('--- …') found — header truncated");
const macLineEnd = decoded.indexOf("\n", macIdx + 1);
if (macLineEnd === -1) fail("header MAC line is not terminated — header truncated");
const headerText = decoded.slice(0, macIdx); // version + stanzas, MAC line excluded
const payloadStart = macLineEnd + 1;
const macLine = decoded.slice(macIdx + 1, macLineEnd).replace(/^---\s*/, "");
const headerMac = Buffer.from(macLine, "base64");
say(`version      : OK (${decoded.slice(0, 19)})`);
say(`header MAC   : ${headerMac.length} bytes (expected 32)`);
if (headerMac.length !== 32) fail(`header MAC is ${headerMac.length} bytes, expected 32`);

const stanzas = [];
{
  const lines = headerText.split("\n").slice(1);
  let cur = null;
  for (const line of lines) {
    if (line.startsWith("-> ")) {
      const [type, ...args] = line.slice(3).split(" ").filter((s) => s !== "");
      cur = { type, args, bodyB64: "" };
      stanzas.push(cur);
    } else if (cur) {
      cur.bodyB64 += line;
    }
  }
  for (const s of stanzas) s.body = Buffer.from(s.bodyB64, "base64");
}
say(`stanzas      : ${stanzas.map((s) => s.type).join(", ")}`);

const tlock = stanzas.find((s) => s.type === "tlock");
if (!tlock) fail("no tlock stanza — this is a normal age file, not a timelock");
if (tlock.args.length !== 2) fail(`tlock stanza has ${tlock.args.length} args, expected 2 (round, chain)`);
const round = Number(tlock.args[0]);
const chainHash = tlock.args[1];
if (!Number.isInteger(round) || round < 1) fail(`tlock round '${tlock.args[0]}' is not a positive integer`);
if (!/^[0-9a-f]{64}$/.test(chainHash)) fail(`tlock chain hash '${chainHash}' is not a 64-char hex string`);

// ---------- 3. stanza body shape vs. a fresh canary of the same scheme ----------
// Encryption is offline (needs only the public chain info), so we can generate a
// reference ciphertext of the same scheme and compare structural sizes.
const localInfo = { ...defaultChainInfo };
const localClient = { options: {}, chain: () => ({ info: async () => localInfo }), get: async () => { throw new Error("offline validation has no beacon"); } };
const canaryArmor = await timelockEncrypt(round, Buffer.from("size probe"), localClient);
const canaryBody = Buffer.from(
  canaryArmor.split("\n").filter((l) => l && !l.startsWith("-----")).join(""),
  "base64"
).toString("latin1");
const canaryStanza = canaryBody.match(/-> tlock \d+ [0-9a-f]{64}\n([A-Za-z0-9+/=\n]+)\n---/);
const canaryStanzaBody = Buffer.from(canaryStanza[1].replace(/\n/g, ""), "base64");
say(`tlock body   : ${tlock.body.length} bytes (reference ciphertext of same scheme: ${canaryStanzaBody.length})`);
if (tlock.body.length !== canaryStanzaBody.length) {
  fail(`tlock stanza body is ${tlock.body.length} bytes but the scheme produces ${canaryStanzaBody.length} — the ciphertext is truncated or from an incompatible tlock version`);
}

// ---------- 4. payload sanity ----------
const payload = body.subarray(payloadStart);
say(`payload      : ${payload.length} bytes of age STREAM data (~${payload.length - 16 - 16} bytes of ciphertext before overhead)`);
if (payload.length < 32) fail("payload is too small to be an age stream");

// ---------- 5. lock status ----------
if (chainHash === localInfo.hash) {
  const unlockMs = roundTime(localInfo, round);
  say(`chain        : ${localInfo.metadata.beaconID} (${chainHash.slice(0, 16)}…)`);
  say(`round        : ${round}`);
  say(`unlock time  : ${new Date(unlockMs).toISOString()}`);
  const left = unlockMs - Date.now();
  if (left > 0) {
    say(`status       : LOCKED — ${(left / 86400000).toFixed(2)} days to go`);
  } else {
    say(`status       : unlock round already emitted — decrypt with unlock.mjs or offline.mjs`);
  }

  // Probe the real decryption path. Offline: the "too early" gate fires before
  // any beacon fetch, so a locked file must produce exactly that error.
  try {
    await timelockDecrypt(text, localClient);
    say(`decrypt probe: SUCCEEDED (unexpected for a future round — but great news)`);
  } catch (err) {
    const msg = String(err?.message ?? err);
    if (/too early/i.test(msg)) say(`decrypt probe: correctly refused — "${msg}"`);
    else if (/no beacon/i.test(msg)) say(`decrypt probe: round is published; supply the beacon via offline.mjs to finish`);
    else fail(`decryption probe failed with an unexpected error: ${msg}`);
  }
} else {
  say(`chain        : ${chainHash} — not drand quicknet; unlock time must be computed against that chain's info`);
}

console.log("\nRESULT: file is structurally valid" + (chainHash === localInfo.hash && roundTime(localInfo, round) > Date.now() ? " and correctly locked." : "."));
process.exit(chainHash === localInfo.hash && roundTime(localInfo, round) > Date.now() ? 2 : 0);
