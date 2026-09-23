"""A zero-dependency web interface: ``python3 -m buttcrack serve``.

Standard library only (``http.server`` + ``json`` + ``threading``), so the UI is
available anywhere Python is -- no build step, no node_modules, no framework.

API
---
``GET  /``                     the single-page app
``GET  /api/health``           version, model provenance, CPU count
``GET  /api/ciphers``          the registry, for the reference panel
``POST /api/identify``         ``{"text": ...}`` -> characterisation + hypotheses
``POST /api/transform``        ``{"cipher","key","text","operation"}`` -> output
``POST /api/crack``            ``{"text","budget","workers","depth","hints"}`` -> ``{"job": id}``
``GET  /api/job/<id>``         ``{"done", "progress": [...], "report": {...}}``

Cracking runs in a worker thread and the browser polls the job: that keeps the
live progress log without needing websockets, and it means a long search cannot
block the rest of the UI.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import __version__
from .ciphers import ALL_CIPHERS, layer_ciphers, try_get
from .detect import characterise, identify
from .engine import solve
from .lang import get_model

STATIC_DIR = Path(__file__).parent / "static"
MAX_BODY_BYTES = 4 * 1024 * 1024
#: Finished jobs are kept for a while so a slow poller can still collect them.
JOB_TTL_SECONDS = 600
MAX_JOBS = 32


class JobStore:
    """Crack jobs, their progress lines and their eventual reports."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, dict[str, Any]] = {}

    def create(self, options: dict[str, Any]) -> str:
        job_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._prune()
            self._jobs[job_id] = {
                "id": job_id,
                "created": time.time(),
                "options": options,
                "progress": [],
                "done": False,
                "report": None,
                "error": None,
            }
        thread = threading.Thread(target=self._run, args=(job_id,), daemon=True)
        thread.start()
        return job_id

    def _prune(self) -> None:
        cutoff = time.time() - JOB_TTL_SECONDS
        stale = [k for k, v in self._jobs.items() if v["created"] < cutoff and v["done"]]
        for key in stale:
            del self._jobs[key]
        while len(self._jobs) > MAX_JOBS:
            oldest = min(self._jobs, key=lambda k: self._jobs[k]["created"])
            del self._jobs[oldest]

    def _run(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:  # pragma: no cover - pruned mid-flight
            return
        options = job["options"]

        def progress(message: str, fraction: float, extra: dict) -> None:
            with self._lock:
                job["progress"].append(
                    {
                        "at": round(time.time() - job["created"], 3),
                        "message": message,
                        "fraction": round(fraction, 4) if fraction and fraction > 0 else None,
                        "extra": {k: v for k, v in extra.items() if isinstance(v, (str, int, float, bool))},
                    }
                )

        try:
            report = solve(
                options.get("text", ""),
                budget=float(options.get("budget", 30.0)),
                workers=int(options.get("workers", 1)),
                max_depth=int(options.get("depth", 3)),
                hints=options.get("hints") or None,
                progress=progress,
                exhaustive=bool(options.get("exhaustive", False)),
            )
            payload = report.as_dict(max_candidates=int(options.get("candidates", 8)))
            payload["input"] = {
                "length": len(options.get("text", "")),
                "preview": options.get("text", "")[:400],
            }
            with self._lock:
                job["report"] = payload
        except Exception as error:  # surfaced in the UI rather than swallowed
            with self._lock:
                job["error"] = f"{type(error).__name__}: {error}"
                job["traceback"] = traceback.format_exc(limit=6)
        finally:
            with self._lock:
                job["done"] = True

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return {
                "id": job["id"],
                "done": job["done"],
                "progress": list(job["progress"]),
                "report": job["report"],
                "error": job["error"],
                "options": job["options"],
            }


JOBS = JobStore()


class Handler(BaseHTTPRequestHandler):
    server_version = f"buttcrack/{__version__}"
    protocol_version = "HTTP/1.1"

    # -- plumbing ----------------------------------------------------------- #
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        if os.environ.get("BUTTCRACK_HTTP_LOG"):
            sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def _send(self, status: int, body: bytes, content_type: str, extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self._json({"error": message}, status)

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise ValueError(f"request body too large (limit {MAX_BODY_BYTES} bytes)")
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"body is not valid JSON: {error}") from error
        if not isinstance(data, dict):
            raise ValueError("body must be a JSON object")
        return data

    # -- routes ------------------------------------------------------------- #
    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        path = urlparse(self.path).path
        try:
            if path in ("/", "/index.html"):
                return self._static("index.html")
            if path == "/api/health":
                return self._json(
                    {
                        "name": "buttcrack",
                        "version": __version__,
                        "python": sys.version.split()[0],
                        "cpus": os.cpu_count() or 1,
                        "ciphers": len(ALL_CIPHERS),
                        "layers": [c.info.name for c in layer_ciphers()],
                        "model": get_model().meta,
                    }
                )
            if path == "/api/ciphers":
                return self._json([c.info.as_dict() for c in ALL_CIPHERS])
            if path.startswith("/api/job/"):
                job = JOBS.get(path.rsplit("/", 1)[-1])
                if job is None:
                    return self._error(404, "no such job")
                return self._json(job)
            if path.startswith("/api/"):
                return self._error(404, f"unknown endpoint {path}")
            return self._static(path.lstrip("/"))
        except BrokenPipeError:  # pragma: no cover - browser navigated away
            return None
        except Exception as error:  # pragma: no cover - never kill the server
            return self._error(500, f"{type(error).__name__}: {error}")

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            body = self._read_body()
        except ValueError as error:
            return self._error(400, str(error))
        try:
            if path == "/api/crack":
                text = str(body.get("text") or "")
                if not text.strip():
                    return self._error(400, "no ciphertext given")
                options = {
                    "text": text,
                    "budget": _clamp(float(body.get("budget", 30.0)), 0.5, 600.0),
                    "workers": int(_clamp(float(body.get("workers", 1)), 1, max(1, os.cpu_count() or 1) * 2)),
                    "depth": int(_clamp(float(body.get("depth", 3)), 0, 6)),
                    "candidates": int(_clamp(float(body.get("candidates", 8)), 1, 24)),
                    "exhaustive": bool(body.get("exhaustive", False)),
                    "hints": _clean_hints(body.get("hints")),
                }
                return self._json({"job": JOBS.create(options), "options": options})
            if path == "/api/identify":
                text = str(body.get("text") or "")
                if not text.strip():
                    return self._error(400, "no text given")
                hypotheses, stats = identify(text)
                return self._json(
                    {"stats": stats.as_dict(), "hypotheses": [h.as_dict() for h in hypotheses]}
                )
            if path == "/api/transform":
                return self._transform(body)
            return self._error(404, f"unknown endpoint {path}")
        except Exception as error:
            return self._error(500, f"{type(error).__name__}: {error}")

    def _transform(self, body: dict[str, Any]) -> None:
        cipher = try_get(str(body.get("cipher") or ""))
        if cipher is None:
            return self._error(400, f"unknown cipher {body.get('cipher')!r}")
        text = str(body.get("text") or "")
        if not text.strip():
            return self._error(400, "no text given")
        operation = str(body.get("operation") or "encrypt")
        if operation not in ("encrypt", "decrypt", "encode", "decode"):
            return self._error(400, f"unknown operation {operation!r}")
        key = body.get("key", cipher.info.example_key)
        try:
            if operation in ("encrypt", "encode"):
                out = cipher.encrypt(text, key)
            else:
                out = cipher.decrypt(text, key)
        except Exception as error:
            return self._error(400, f"{cipher.info.name} could not {operation}: {error}")
        return self._json(
            {
                "cipher": cipher.info.name,
                "operation": operation,
                "key": key,
                "input": text,
                "output": out,
                "length": len(out),
            }
        )

    def _static(self, relative: str) -> None:
        candidate = (STATIC_DIR / relative).resolve()
        if not str(candidate).startswith(str(STATIC_DIR.resolve())):
            return self._error(403, "outside the static directory")
        if not candidate.is_file():
            return self._error(404, f"no such file: {relative}")
        types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
            ".png": "image/png",
            ".woff2": "font/woff2",
        }
        self._send(200, candidate.read_bytes(), types.get(candidate.suffix, "application/octet-stream"))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clean_hints(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    allowed = ("key", "key_length", "width", "seed", "crib")
    out: dict[str, Any] = {}
    for name in allowed:
        if raw.get(name) in (None, ""):
            continue
        value = raw[name]
        if name in ("key_length", "width", "seed"):
            try:
                out[name] = int(value)
            except (TypeError, ValueError):
                continue
        else:
            out[name] = str(value)[:200]
    return out


def serve(host: str = "0.0.0.0", port: int = 8080, open_browser: bool = True) -> int:
    """Run the web interface until interrupted.  Returns a process exit code."""
    ThreadingHTTPServer.allow_reuse_address = True
    ThreadingHTTPServer.daemon_threads = True
    try:
        httpd = ThreadingHTTPServer((host, port), Handler)
    except OSError as error:
        print(f"buttcrack: cannot listen on {host}:{port} ({error})", file=sys.stderr)
        return 1

    shown_host = "localhost" if host in ("0.0.0.0", "::", "") else host
    url = f"http://{shown_host}:{port}/"
    model = get_model()
    print(f"buttcrack {__version__} web interface")
    print(f"  listening on {url}  (bound to {host}:{port})")
    print(f"  {len(ALL_CIPHERS)} ciphers, {model.ngram_count(4):,} quadgrams, {len(model.words):,} words")
    print("  press Ctrl-C to stop")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:  # headless boxes have no browser; that is fine
            pass
    try:
        httpd.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        httpd.server_close()
    return 0


def _free_port(preferred: int) -> int:
    """``preferred`` if it is free, otherwise whatever the OS hands out."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("0.0.0.0", preferred))
            return preferred
        except OSError:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("0.0.0.0", 0))
        return probe.getsockname()[1]


if __name__ == "__main__":  # pragma: no cover
    target = _free_port(int(os.environ.get("PORT", 8080)))
    raise SystemExit(serve(port=target, open_browser=False))
