#!/usr/bin/env node
/**
 * offline.mjs — timelock-decrypt an age file with zero network access,
 * using a beacon JSON you saved earlier (e.g. from a browser or another
 * machine that can reach https://api.drand.sh).
 *
 * Usage:
 *   node offline.mjs <file.age> <beacon.json> [info.json] [out.txt]
 *
 * Defaults: info.json = evidence/quicknet-info.json, out = <file minus .age>.txt
 *
 * How to get the beacon JSON after the unlock round exists:
 *   https://api.drand.sh/52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971/public/33542211
 * (save the JSON object exactly as served)
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { timelockDecrypt } from "tlock-js";

const [file, beaconPath, infoPath, outArg] = process.argv.slice(2);
if (!file || !beaconPath) {
  console.error("usage: node offline.mjs <file.age> <beacon.json> [info.json] [out.txt]");
  process.exit(1);
}
const infoFile = infoPath ?? new URL("./evidence/quicknet-info.json", import.meta.url).pathname;
const out = outArg ?? file.replace(/\.age$/i, "") + ".txt";

for (const f of [file, beaconPath, infoFile]) {
  if (!existsSync(f)) {
    console.error(`error: ${f} not found`);
    process.exit(1);
  }
}

const armored = readFileSync(file, "utf8").trim();
const beacon = JSON.parse(readFileSync(beaconPath, "utf8"));
const info = JSON.parse(readFileSync(infoFile, "utf8"));

console.log(`file     : ${file}`);
console.log(`beacon   : round ${beacon.round} (${beaconPath})`);
console.log(`chain    : ${info.metadata?.beaconID ?? info.hash}`);

// Minimal ChainClient: everything comes from local files. Beacon verification
// stays enabled, so a wrong or tampered beacon fails instead of decrypting garbage.
const chain = { info: async () => info };
const client = {
  options: { disableBeaconVerification: false, noCache: false },
  chain: () => chain,
  get: async (roundNumber) => {
    if (Number(roundNumber) !== Number(beacon.round)) {
      throw new Error(`this file needs beacon round ${roundNumber}, but ${beaconPath} contains round ${beacon.round}`);
    }
    return beacon;
  },
};

try {
  const plaintext = await timelockDecrypt(armored, client);
  writeFileSync(out, plaintext);
  console.log(`\nUNLOCKED ✔  plaintext written to ${out} (${plaintext.length} bytes)`);
  console.log(`\n--- first 4000 bytes ---\n${plaintext.subarray(0, 4000).toString("utf8")}\n--- end of preview ---`);
} catch (err) {
  console.error(`\nnot decrypted: ${err?.message ?? err}`);
  if (/round \d+/i.test(String(err?.message)) && /contains round/i.test(String(err?.message))) {
    console.error("→ fetch the beacon for the round named above and pass that file instead.");
  } else if (/too early/i.test(String(err?.message))) {
    console.error("→ that beacon's round has not happened yet: this file is still timelocked.");
  } else {
    console.error("→ the beacon may be for the wrong chain/round, may be tampered, or the file is not a tlock file for this chain.");
  }
  process.exit(2);
}
