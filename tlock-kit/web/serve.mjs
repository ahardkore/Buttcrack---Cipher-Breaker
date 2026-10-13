#!/usr/bin/env node
/**
 * web/serve.mjs — minimal static server for the browser unlocker.
 * Usage: node web/serve.mjs [port]   (PORT env also works; default 4173)
 * Binds 0.0.0.0 so sandbox previews can reach it.
 */
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join, normalize } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const port = Number(process.argv[2] ?? process.env.PORT ?? 4173);

const types = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

createServer(async (req, res) => {
  try {
    const url = new URL(req.url ?? "/", "http://localhost");
    let path = decodeURIComponent(url.pathname);
    if (path === "/") path = "/index.html";
    const file = normalize(join(here, path));
    if (!file.startsWith(here)) throw Object.assign(new Error("forbidden"), { code: "EACCES" });
    const body = await readFile(file);
    const ext = file.slice(file.lastIndexOf("."));
    res.writeHead(200, {
      "content-type": types[ext] ?? "application/octet-stream",
      "cache-control": "no-store",
    });
    res.end(body);
  } catch (err) {
    res.writeHead(err.code === "ENOENT" ? 404 : 403, { "content-type": "text/plain" });
    res.end(String(err.message ?? err));
  }
}).listen(port, "0.0.0.0", () => {
  console.log(`tlock web unlocker: http://0.0.0.0:${port}  (open this via any static host / preview URL)`);
});
