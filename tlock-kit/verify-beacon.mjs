#!/usr/bin/env node
/**
 * verify-beacon.mjs — check that a beacon JSON really is signed by the drand
 * quicknet threshold key (no network needed).
 *
 * Usage: node verify-beacon.mjs <beacon.json> [info.json]
 *   Defaults: info.json = evidence/quicknet-info.json
 *
 * A beacon is valid iff sha256(signature) == randomness and the BLS signature
 * verifies against the chain public key for message sha256(round_uint64_be).
 */
import { readFileSync, existsSync } from "node:fs";
import { verifyBeacon } from "drand-client/beacon-verification.js";
import { roundTime } from "tlock-js";

const [beaconPath, infoPath] = process.argv.slice(2);
if (!beaconPath) {
  console.error("usage: node verify-beacon.mjs <beacon.json> [info.json]");
  process.exit(1);
}
const infoFile = infoPath ?? new URL("./evidence/quicknet-info.json", import.meta.url).pathname;
for (const f of [beaconPath, infoFile]) {
  if (!existsSync(f)) {
    console.error(`error: ${f} not found`);
    process.exit(1);
  }
}
const beacon = JSON.parse(readFileSync(beaconPath, "utf8"));
const info = JSON.parse(readFileSync(infoFile, "utf8"));

const valid = await verifyBeacon(info, beacon, beacon.round);
console.log(`${valid ? "VALID ✔" : "INVALID ✘"}  round ${beacon.round} of ${info.metadata?.beaconID ?? info.hash}`);
console.log(`  beacon time: ${new Date(roundTime(info, beacon.round)).toISOString()}`);
console.log(`  randomness : ${beacon.randomness}`);
console.log(`  signature  : ${beacon.signature}`);
process.exit(valid ? 0 : 1);
