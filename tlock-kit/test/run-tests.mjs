#!/usr/bin/env node
/**
 * test/run-tests.mjs — end-to-end validation of the tlock kit, offline.
 *
 * All cryptography here is REAL: the chain info and the beacon (round
 * 33025409, signature 8870a4c8…) were fetched from api.drand.sh and are
 * served locally by mock/drand-server.mjs. The tests therefore exercise
 * genuine drand chain verification and genuine IBE/timelock decryption.
 *
 * Checks:
 *   1. roundTime(33542211) == 2026-10-31T06:59:57Z
 *   2. the real beacon verifies against the real quicknet public key
 *      (and a tampered copy does NOT verify)
 *   3. encrypt a canary to the published round 33025409 and decrypt it again
 *      → plaintext round-trips (this is exactly what unlock.mjs will do on
 *       2026-10-31 for the user's file, one round later)
 *   4. encrypt a canary to round 33542211 → decryption must fail with
 *      "too early" (this is what the user's real file does today)
 *   5. CLI: unlock.mjs decrypts the past-round canary (UNLOCKED, exit 0)
 *   6. CLI: unlock.mjs refuses the future-round canary with a clear message
 *   7. CLI: offline.mjs decrypts the past-round canary from a beacon file alone
 *   8. CLI: verify-beacon.mjs accepts the real beacon, rejects a tampered one
 */
import { startServer } from "../mock/drand-server.mjs";

// Async spawn so the parent's event loop stays free to serve the mock API.
function runNode(args, env = {}) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, args, { env: { ...process.env, ...env } });
    let stdout = "", stderr = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));
    const killer = setTimeout(() => child.kill("SIGKILL"), 30000);
    child.on("close", (status) => {
      clearTimeout(killer);
      resolve({ status, stdout, stderr });
    });
  });
}

import { spawn } from "node:child_process";
import { readFileSync, writeFileSync, mkdirSync, rmSync, existsSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  timelockEncrypt,
  timelockDecrypt,
  HttpChainClient,
  HttpCachingChain,
  roundTime,
  defaultChainInfo,
} from "tlock-js";
import { verifyBeacon } from "drand-client/beacon-verification.js";

const here = dirname(fileURLToPath(import.meta.url));
const kit = join(here, "..");
const tmp = join(here, "tmp");
mkdirSync(tmp, { recursive: true });

const PAST_ROUND = 33025409; // real, published, we have its real signature
const TARGET_ROUND = 33542211; // the user's file is locked to this one

let failures = 0;
const ok = (cond, label, extra = "") => {
  console.log(`${cond ? "PASS" : "FAIL"}  ${label}${extra ? "  — " + extra : ""}`);
  if (!cond) failures++;
};

const { server, port } = await startServer(0);
const base = `http://127.0.0.1:${port}`;
const opts = { disableBeaconVerification: false, noCache: false };
const client = new HttpChainClient(new HttpCachingChain(base, opts), opts);
console.log(`mock drand server: ${base} (serving real quicknet info + real round ${PAST_ROUND} beacon)\n`);

// ---------- 1. time math ----------
const t = roundTime(defaultChainInfo, TARGET_ROUND);
ok(
  t === new Date("2026-10-31T06:59:57Z").getTime(),
  "roundTime(33542211) == 2026-10-31T06:59:57Z",
  `library says ${new Date(t).toISOString()}`
);

// ---------- 2. beacon verification ----------
const realBeacon = JSON.parse(readFileSync(join(kit, "evidence/beacon-33025409.json"), "utf8"));
const info = JSON.parse(readFileSync(join(kit, "evidence/quicknet-info.json"), "utf8"));
ok(await verifyBeacon(info, realBeacon, realBeacon.round), `real beacon ${realBeacon.round} verifies against quicknet public key`);
const tampered = { ...realBeacon, randomness: "00".repeat(32) };
ok(!(await verifyBeacon(info, tampered, tampered.round)), "tampered beacon is rejected");

// ---------- 3. past-round canary round trip (the full unlock path) ----------
const canary = `canary-${Date.now()} :: this line must come back byte-for-byte`;
const pastArmor = await timelockEncrypt(PAST_ROUND, Buffer.from(canary), client);
const pastFile = join(tmp, "canary-past.age");
writeFileSync(pastFile, pastArmor);
const back = (await timelockDecrypt(pastArmor, client)).toString("utf8");
ok(back === canary, `encrypt→decrypt round trip on real published round ${PAST_ROUND}`);

// ---------- 4. future-round canary is locked ----------
const futureArmor = await timelockEncrypt(TARGET_ROUND, Buffer.from("future canary"), client);
const futureFile = join(tmp, "canary-future.age");
writeFileSync(futureFile, futureArmor);
let lockedErr = null;
try {
  await timelockDecrypt(futureArmor, client);
} catch (err) {
  lockedErr = String(err?.message ?? err);
}
ok(lockedErr !== null && /too early/i.test(lockedErr), `round ${TARGET_ROUND} still locked`, lockedErr ?? "decryption unexpectedly SUCCEEDED");

// ---------- 5. CLI: unlock.mjs on the past-round canary ----------
{
  const r = await runNode([join(kit, "unlock.mjs"), pastFile, join(tmp, "past-out.txt")], { DRAND_CHAIN_URL: base });
  const wrote = readFileSync(join(tmp, "past-out.txt"), "utf8");
  ok(r.status === 0 && /UNLOCKED/.test(r.stdout) && wrote === canary, "unlock.mjs decrypts the canary (exit 0)",
     r.status === 0 ? "" : `exit ${r.status}: ${r.stderr.split("\n").slice(-3).join(" | ")}`);
}

// ---------- 6. CLI: unlock.mjs on the future-round canary ----------
{
  const r = await runNode([join(kit, "unlock.mjs"), futureFile, join(tmp, "future-out.txt")], { DRAND_CHAIN_URL: base });
  ok(r.status === 2 && /2026-10-31T06:59:57/.test(r.stderr), "unlock.mjs correctly reports LOCKED with the unlock date (exit 2)",
     r.status === 2 ? "" : `exit ${r.status}: ${r.stdout.slice(-200)}`);
}

// ---------- 7. CLI: offline.mjs ----------
{
  const r = await runNode([
    join(kit, "offline.mjs"), pastFile, join(kit, "evidence/beacon-33025409.json"),
    join(kit, "evidence/quicknet-info.json"), join(tmp, "offline-out.txt"),
  ]);
  const wrote = readFileSync(join(tmp, "offline-out.txt"), "utf8");
  ok(r.status === 0 && wrote === canary, "offline.mjs decrypts from beacon JSON alone (exit 0)",
     r.status === 0 ? "" : `exit ${r.status}: ${r.stderr.split("\n").slice(-2).join(" | ")}`);
}

// ---------- 8. CLI: verify-beacon.mjs ----------
{
  const rOk = await runNode([join(kit, "verify-beacon.mjs"), join(kit, "evidence/beacon-33025409.json")]);
  const badPath = join(tmp, "beacon-bad.json");
  writeFileSync(badPath, JSON.stringify(tampered));
  const rBad = await runNode([join(kit, "verify-beacon.mjs"), badPath]);
  ok(rOk.status === 0 && /VALID/.test(rOk.stdout), "verify-beacon.mjs accepts the real beacon");
  ok(rBad.status === 1 && /INVALID/.test(rBad.stdout), "verify-beacon.mjs rejects the tampered beacon");
}

// ---------- 9. web core (the exact code the browser page runs) ----------
{
  const { parseTlockStanza, decryptArmored, fmtDuration } = await import("../web/src/core.js");
  const parsed = parseTlockStanza(pastArmor);
  ok(parsed?.round === PAST_ROUND && parsed?.chainHash === defaultChainInfo.hash,
     "web core: parses round + chain from the armored file", JSON.stringify(parsed));
  const viaWeb = new TextDecoder().decode(await decryptArmored(pastArmor, base));
  ok(viaWeb === canary, "web core: browser decrypt path reproduces the canary");
  ok(fmtDuration(90061000) === "1d 1h 1m 1s", "web core: countdown formatting");
  const bundle = join(kit, "web/app.bundle.js");
  ok(existsSync(bundle) && statSync(bundle).size > 50_000, "web bundle built (web/app.bundle.js)",
     existsSync(bundle) ? `${statSync(bundle).size} bytes` : "missing — run: npm run build:web");
}

server.close();
rmSync(tmp, { recursive: true, force: true });
console.log(failures === 0 ? "\nALL CHECKS PASSED ✔  — kit validated end-to-end against real drand data." : `\n${failures} CHECK(S) FAILED ✘`);
process.exit(failures === 0 ? 0 : 1);
