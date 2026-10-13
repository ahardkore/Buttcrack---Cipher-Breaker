/**
 * web/src/core.js — pure logic shared by the browser page and the test suite.
 * No DOM access in here.
 */
import {
  timelockDecrypt,
  HttpChainClient,
  HttpCachingChain,
  defaultChainInfo,
  roundTime,
} from "tlock-js";

export { defaultChainInfo, roundTime };
export const PAGES_BASE_URL = `https://api.drand.sh/${defaultChainInfo.hash}`;

/** Decode enough of the ASCII armor to read the age header text. */
export function armorHeaderText(armored, maxBytes = 8192) {
  const lines = armored
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith("-----"));
  for (let n = 4; n <= lines.length; n += 4) {
    const head = atob(lines.slice(0, n).join(""));
    if (lines.length - n < 4 || head.length > maxBytes) return head;
    if (/->\s+tlock\s+\d+\s+[0-9a-f]{64}/.test(head)) return head;
  }
  return lines.length ? atob(lines.join("")) : "";
}

/** Pull `-> tlock <round> <chainHash>` out of an armored age file. */
export function parseTlockStanza(armored) {
  const m = armorHeaderText(armored).match(/->\s+tlock\s+(\d+)\s+([0-9a-f]{64})/);
  return m ? { round: Number(m[1]), chainHash: m[2] } : null;
}

/** Client for decryption over the network (browser fetch). */
export function makeClient(baseUrl) {
  const opts = { disableBeaconVerification: false, noCache: true };
  const chain = new HttpCachingChain(baseUrl.replace(/\/+$/, ""), opts);
  return new HttpChainClient(chain, opts, { headers: {} });
}

/** Client backed by a locally provided beacon JSON — fully offline decryption. */
export function offlineClient(beacon) {
  const chain = { info: async () => defaultChainInfo };
  return {
    options: { disableBeaconVerification: false, noCache: false },
    chain: () => chain,
    get: async (roundNumber) => {
      if (Number(roundNumber) !== Number(beacon.round)) {
        throw new Error(`this file needs beacon round ${roundNumber}; the supplied file contains round ${beacon.round}`);
      }
      return beacon;
    },
  };
}

export async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} from ${url}`);
  return await res.json();
}

/** Chain info + latest beacon from a drand API base URL. */
export async function getStatus(baseUrl) {
  const base = baseUrl.replace(/\/+$/, "");
  const [info, latest] = await Promise.all([fetchJson(`${base}/info`), fetchJson(`${base}/public/latest`)]);
  return { info, latest };
}

/** Decrypt. Pass { beacon } to work fully offline. Returns Uint8Array. */
export async function decryptArmored(armored, baseUrl, { beacon } = {}) {
  const client = beacon ? offlineClient(beacon) : makeClient(baseUrl ?? PAGES_BASE_URL);
  const buf = await timelockDecrypt(armored, client);
  return new Uint8Array(buf.buffer, buf.byteOffset, buf.byteLength);
}

export function fmtDuration(ms) {
  if (!Number.isFinite(ms) || ms <= 0) return "0s";
  const s = Math.floor(ms / 1000);
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const parts = [];
  if (d) parts.push(`${d}d`);
  if (d || h) parts.push(`${h}h`);
  parts.push(`${m}m`, `${sec}s`);
  return parts.join(" ");
}
