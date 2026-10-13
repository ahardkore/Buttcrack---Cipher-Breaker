#!/usr/bin/env node
/**
 * mock/drand-server.mjs — a tiny local stand-in for the drand HTTP API,
 * used by the test suite so the kit can be validated without outbound
 * network access. It serves:
 *
 *   GET /info                → the REAL quicknet chain info (evidence/quicknet-info.json)
 *   GET /public/<round>      → a REAL published beacon (evidence/beacon-33025409.json)
 *                              when <round> === 33025409, else 404 (like drand
 *                              for rounds that don't exist yet)
 *   GET /public/latest       → the same real beacon
 *
 * All cryptography in the tests therefore runs against genuine drand data.
 *
 * Standalone: node mock/drand-server.mjs [port]
 */
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const info = JSON.parse(readFileSync(join(here, "../evidence/quicknet-info.json"), "utf8"));
const beacon = JSON.parse(readFileSync(join(here, "../evidence/beacon-33025409.json"), "utf8"));

export function startServer(port = Number(process.env.DRAND_MOCK_PORT ?? 42133)) {
  const server = createServer((req, res) => {
    const url = new URL(req.url ?? "/", "http://localhost");
    const send = (code, obj) => {
      const body = JSON.stringify(obj);
      res.writeHead(code, { "content-type": "application/json", "content-length": Buffer.byteLength(body) });
      res.end(body);
    };
    if (url.pathname === "/info") return send(200, info);
    const m = url.pathname.match(/^\/public\/(latest|\d+)\/?$/);
    if (m) {
      if (m[1] === "latest" || Number(m[1]) === beacon.round) return send(200, beacon);
      return send(404, { error: "beacon not found" });
    }
    send(404, { error: "not found" });
  });
  return new Promise((resolve) => {
    server.listen(port, "127.0.0.1", () => resolve({ server, port: server.address().port }));
  });
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  startServer().then(({ port }) => console.log(`mock drand server listening on http://127.0.0.1:${port}`));
}
