#!/usr/bin/env node
/**
 * watch.mjs — start it and forget it: waits for the drand round your file is
 * locked to, then decrypts automatically and exits.
 *
 * Usage:  node watch.mjs [file.age] [out.txt]
 *
 * Env:    DRAND_CHAIN_URL     drand API base URL (default: quicknet on api.drand.sh)
 *         WATCH_INTERVAL_MS   poll interval, default 15000 (15 s)
 *
 * Typical use — leave it running overnight (screen/tmux/nohup), e.g. on the
 * evening of 2026-10-30 US time, right before the 2026-10-31T06:59:57Z unlock:
 *
 *   nohup node watch.mjs what-is-locked.age > watch.log 2>&1 &
 *
 * When round 33542211 is emitted, the plaintext is written to
 * what-is-locked.txt and the process exits 0. The chain, not your clock, is
 * the source of truth, so an early/late local clock cannot fire too soon.
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { timelockDecrypt } from "tlock-js";
import { parseTlockStanza, makeClient, getStatus, roundTime, PAGES_BASE_URL } from "./web/src/core.js";

const [, , fileArg, outArg] = process.argv;
const file = fileArg ?? "what-is-locked.age";
const out = outArg ?? file.replace(/\.age$/i, "") + ".txt";
const baseUrl = (process.env.DRAND_CHAIN_URL ?? PAGES_BASE_URL).replace(/\/+$/, "");
const interval = Math.max(250, Number(process.env.WATCH_INTERVAL_MS ?? 15000));

if (!existsSync(file)) {
  console.error(`error: ${file} not found — save the armored age file first.`);
  process.exit(1);
}
const armored = readFileSync(file, "utf8").trim();
const stanza = parseTlockStanza(armored);
if (!stanza) {
  console.error("error: no tlock recipient stanza found in " + file);
  process.exit(1);
}

const log = (msg) => console.log(`[${new Date().toISOString()}] ${msg}`);
log(`watching ${file} — locked to round ${stanza.round} on ${stanza.chainHash.slice(0, 16)}…`);
log(`drand API ${baseUrl}, polling every ${interval / 1000}s; plaintext → ${out}`);

process.on("SIGINT", () => {
  console.log("stopped.");
  process.exit(130);
});

for (;;) {
  try {
    const { info, latest } = await getStatus(baseUrl);
    const left = stanza.round - latest.round;
    if (left <= 0) {
      log(`round ${stanza.round} has arrived (latest ${latest.round}) — decrypting…`);
      try {
        const plaintext = await timelockDecrypt(armored, makeClient(baseUrl));
        writeFileSync(out, plaintext);
        log(`UNLOCKED ✔  wrote ${out} (${plaintext.length} bytes)`);
        process.exit(0);
      } catch (err) {
        const msg = String(err?.message ?? err);
        if (/too early/i.test(msg)) {
          log("chain reports the round but the beacon is not served yet; retrying…");
        } else {
          console.error(`decryption failed: ${msg}`);
          process.exit(2);
        }
      }
    } else {
      const unlockAt = new Date(roundTime(info, stanza.round)).toISOString();
      const mins = Math.round((left * info.period) / 60);
      log(`latest round ${latest.round} — ${left} to go (~${mins} min; unlock ${unlockAt})`);
    }
  } catch (err) {
    log(`chain fetch failed (${err?.message ?? err}); retrying`);
  }
  await new Promise((r) => setTimeout(r, interval));
}
