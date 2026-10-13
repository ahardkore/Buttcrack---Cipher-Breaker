"""The desktop application: ``buttcrack app``.

This is what the Windows installer's Start-menu shortcut runs.  It is the same
local web interface as :mod:`buttcrack.server`, wrapped so that it behaves like
a double-clickable program rather than a command you have to remember:

* it binds **127.0.0.1 only** -- a desktop app has no business accepting
  connections from the network, unlike ``buttcrack serve`` which defaults to
  ``0.0.0.0`` so you can reach it from another machine on purpose;
* it takes whatever port is free instead of failing when 8080 is taken;
* launching it twice does not give you two servers.  The first copy holds a lock
  and publishes its URL, and the second one opens that URL and exits -- see
  :class:`RunningInstance`;
* it opens the browser for you;
* it puts a small control window on screen (and, on Windows, a tray icon) so
  there is something to close.  Closing it stops the server.

Everything degrades.  No Tk, no tray, no browser, no console -- each of those
is handled and the server still runs.  The dependency list is still empty:
``tkinter`` and ``ctypes`` are standard library.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path
from typing import IO, Any, Callable

from . import __version__, userdata
from .userdata import assistant_log, pk9_ledger

#: A desktop app listens to itself and nothing else.
LOCAL_HOST = "127.0.0.1"

#: Tried first so the address stays familiar between launches; any free port
#: will do if something else already has it.
PREFERRED_PORT = 8080


# --------------------------------------------------------------------------- #
# frozen-build survival
# --------------------------------------------------------------------------- #


#: Windowed builds have no console, so this file is the only place a dying
#: worker's traceback, or a startup failure, survives to be read afterwards.
LOG_NAME = "buttcrack.log"
LOG_MAX_BYTES = 512 * 1024
LOG_KEEP = 2

_LOG_LOCK = threading.Lock()
_LOG_STREAM: IO[str] | None = None


def log_path() -> Path:
    """Where the frozen build keeps its own output."""
    return userdata.data_dir(create=False) / "logs" / LOG_NAME


def _rotate_log() -> None:
    """Shift ``buttcrack.log`` aside, keeping :data:`LOG_KEEP` older files."""
    directory = log_path().parent
    oldest = directory / f"{LOG_NAME}.{LOG_KEEP}"
    with contextlib.suppress(OSError):
        oldest.unlink(missing_ok=True)
    for index in range(LOG_KEEP - 1, 0, -1):
        source = directory / f"{LOG_NAME}.{index}"
        target = directory / f"{LOG_NAME}.{index + 1}"
        if source.is_file():
            with contextlib.suppress(OSError):
                source.replace(target)
    with contextlib.suppress(OSError):
        log_path().replace(directory / f"{LOG_NAME}.1")


def _log_stream() -> IO[str] | None:
    """The open log, rotated once it has had enough.  Never raises."""
    global _LOG_STREAM
    if _LOG_STREAM is not None:
        if _LOG_STREAM.closed:
            over_cap = True
        else:
            try:
                over_cap = _LOG_STREAM.tell() >= LOG_MAX_BYTES
            except (OSError, ValueError):  # unwritable: start a fresh file
                over_cap = True
        if not over_cap:
            return _LOG_STREAM
        with contextlib.suppress(OSError):
            _LOG_STREAM.close()
        _LOG_STREAM = None
        _rotate_log()
    try:
        log_path().parent.mkdir(parents=True, exist_ok=True)
        # The handle outlives this call on purpose: it is the log, kept open for
        # the life of the process and rotated when it fills.
        _LOG_STREAM = open(log_path(), "a", encoding="utf-8", errors="replace")  # noqa: SIM115
    except OSError:
        _LOG_STREAM = None
    return _LOG_STREAM


class _NullStream:
    """A file-like sink that also keeps what it was given, on disk.

    A GUI build on Windows has no console, and PyInstaller sets ``sys.stdout``
    and ``sys.stderr`` to ``None`` there.  Every ``print`` in the server, and
    every traceback the standard library writes -- including the one
    ``multiprocessing`` prints when a worker dies -- would then raise
    ``AttributeError: 'NoneType' object has no attribute 'write'``: a crash on
    startup for a program whose only fault was logging.

    Discarding the text was the first fix, and it threw away the only evidence a
    broken install produces.  It now goes to ``<data dir>/logs/buttcrack.log``,
    capped and rotated, and every failure to write is swallowed: a program must
    not fall over because its *log* would not open.
    """

    encoding = "utf-8"
    errors = "replace"

    def write(self, text: str) -> int:
        if not text:
            return 0
        try:
            with _LOG_LOCK:
                handle = _log_stream()
                if handle is not None:
                    handle.write(text)
                    handle.flush()
        except Exception:  # a missing or read-only log must never be fatal
            pass
        return len(text)

    def flush(self) -> None:
        with _LOG_LOCK, contextlib.suppress(Exception):
            if _LOG_STREAM is not None:
                _LOG_STREAM.flush()

    def isatty(self) -> bool:
        return False

    def fileno(self) -> int:
        raise OSError("null stream has no file descriptor")

    def close(self) -> None:
        return None


def ensure_streams() -> None:
    """Give ``sys.stdout``/``stderr`` something to write to if they are missing."""
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            setattr(sys, name, _NullStream())


def is_frozen() -> bool:
    """True inside a PyInstaller (or similar) one-file/one-dir build."""
    return bool(getattr(sys, "frozen", False))


# --------------------------------------------------------------------------- #
# what the app remembers
# --------------------------------------------------------------------------- #

#: Window geometry per panel, and the port that worked last time.  One small
#: JSON file: nothing here is worth a database, and nothing here is worth
#: failing over -- a read-only data directory costs the user a remembered
#: window, never the app.
STATE_NAME = "desktop-state.json"


def state_path() -> Path:
    return userdata.data_dir() / STATE_NAME


def load_state() -> dict[str, Any]:
    """The remembered state, or an empty dict if there is none to read."""
    try:
        loaded = json.loads(state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def save_state(**updates: Any) -> None:
    """Merge ``updates`` into the state file.  Never raises."""
    state = load_state()
    state.update(updates)
    try:
        state_path().parent.mkdir(parents=True, exist_ok=True)
        state_path().write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    except OSError:
        pass


def usable_geometry(geometry: str) -> bool:
    """Whether a Tk geometry string is worth restoring.

    A withdrawn window reports ``1x1+0+0`` on some systems; writing that back
    would make the next launch a one-pixel window.  Anything narrower than the
    root's own minimum is a report like that rather than a real window.
    """
    width = geometry.split("x", 1)[0]
    return "x" in geometry and width.isdigit() and int(width) >= 300


def remembered_port() -> int:
    """The port that worked last time, or 0 when there is nothing usable."""
    port = load_state().get("port")
    return port if isinstance(port, int) and 0 < port < 65536 else 0


def is_free(port: int, host: str = LOCAL_HOST) -> bool:
    """Whether ``port`` can be bound on ``host`` right now."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def desktop_port(preferred: int = PREFERRED_PORT, host: str = LOCAL_HOST) -> int:
    """Which port to serve on.

    The familiar one if it is free, then the one that worked last time -- so a
    bookmark survives the day some other program takes 8080 -- and only then a
    port the OS picks.
    """
    for candidate in (preferred, remembered_port()):
        if candidate and is_free(candidate, host):
            return candidate
    return free_port(0, host)


# --------------------------------------------------------------------------- #
# the server, on a thread
# --------------------------------------------------------------------------- #


def _lock_exclusive(handle: IO[str]) -> bool:
    """Take a non-blocking exclusive lock on ``handle``.  False if held."""
    if sys.platform == "win32":  # pragma: no cover - exercised by the release run
        import msvcrt

        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True
    import fcntl

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _unlock(handle: IO[str]) -> None:
    """Release a lock taken by :func:`_lock_exclusive`."""
    if sys.platform == "win32":  # pragma: no cover - exercised by the release run
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class RunningInstance:
    """The "I am the desktop app that is running" marker, and the URL in it.

    Launching twice used to give two servers on two ports: two tray icons, two
    browser tabs, two ``127.0.0.1:<port>`` addresses -- and two writers of the
    same SQLite ledger in the data directory.  The marker file is held under an
    exclusive lock for the life of the process, so the check has no race window,
    and it carries the URL that a second launch should open instead.

    Every failure here is silent and non-fatal.  A read-only data directory
    costs the user the duplicate-launch guard; it must not cost them the app.
    """

    def __init__(self) -> None:
        self.path = userdata.instance_file()
        self._handle: IO[str] | None = None

    def claim(self) -> bool:
        """Take the lock.  False means another copy is already running."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.exists():
                # open(..., "r+") refuses to create the file, and "a+" would put
                # every later write at the end of it instead of where publish()
                # seeks -- so the marker is created here and opened for update.
                self.path.touch()
            # Held open for the life of the process: the lock lives on the fd.
            handle = open(self.path, "r+", encoding="utf-8")  # noqa: SIM115
        except OSError:
            return True  # nowhere to write: behave as though we are alone
        try:
            held = _lock_exclusive(handle)
        except OSError:
            handle.close()
            return True
        if not held:
            handle.close()
            return False
        self._handle = handle
        return True

    def publish(self, url: str, port: int) -> None:
        """Record where a second launch should send the user."""
        if self._handle is None:
            return
        with contextlib.suppress(OSError, ValueError):
            self._handle.seek(0)
            json.dump(
                {"pid": os.getpid(), "port": port, "url": url, "version": __version__},
                self._handle,
            )
            self._handle.truncate()
            self._handle.flush()

    def release(self) -> None:
        """Drop the lock and the marker.  Safe to call twice."""
        handle, self._handle = self._handle, None
        if handle is None:
            return
        with contextlib.suppress(OSError):
            _unlock(handle)
        with contextlib.suppress(OSError):
            handle.close()
        with contextlib.suppress(OSError):
            self.path.unlink(missing_ok=True)


def running_instance(timeout: float = 0.5) -> str | None:
    """The URL of a desktop app already serving here, or ``None``.

    The lock says another copy *started*; it does not say that copy is well.  So
    the URL it published is probed over HTTP and only a live buttcrack behind it
    counts -- otherwise a crashed copy's marker would refuse every future launch,
    and so would a process wedged before it ever served a page.  A mutex alone
    cannot tell those apart; a probe can.
    """
    try:
        state = json.loads(userdata.instance_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    url = str(state.get("url") or "")
    if not url.startswith("http://"):
        return None
    try:
        with urllib.request.urlopen(f"{url}api/health", timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    return url if payload.get("name") == "buttcrack" else None


def free_port(preferred: int = PREFERRED_PORT, host: str = LOCAL_HOST) -> int:
    """``preferred`` if it is free on ``host``, otherwise one the OS picks."""
    if preferred and is_free(preferred, host):
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return int(probe.getsockname()[1])


class LocalApp:
    """A running local server plus the handful of actions the UI needs."""

    def __init__(self, host: str = LOCAL_HOST, port: int = 0) -> None:
        from .server import make_server  # imported late: loading the model is slow

        self.host = host
        self.port = port or desktop_port(host=host)
        # make_server keeps the bind address with the server, which is what the
        # handler checks the Host header against.
        self._httpd = make_server(self.host, self.port)
        # Port 0 would have been resolved by bind(); ask the socket, not ourselves.
        self.port = int(self._httpd.server_address[1])
        self._thread: threading.Thread | None = None
        # Best effort: the lock is what tells a second launch to hand over rather
        # than start a second server.  Claiming it here means every path that
        # constructs a LocalApp -- including the library's own tests, which
        # construct several -- behaves the same way.
        self._instance = RunningInstance()
        self._instance.claim()

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            kwargs={"poll_interval": 0.2},
            name="buttcrack-http",
            daemon=True,
        )
        self._thread.start()
        # The lock was taken in __init__ (or lost to a copy that already had it);
        # publishing here is what lets a second launch find *this* app.
        self._instance.publish(self.url, self.port)

    def stop(self) -> None:
        """Close the socket and wait for the serving thread.  Safe to call twice."""
        self._instance.release()
        thread, self._thread = self._thread, None
        if thread is not None:
            # Only when the loop is actually running: ThreadingHTTPServer.shutdown()
            # waits for serve_forever() to acknowledge it, and a server that was
            # constructed but never started will never do that -- the call just
            # blocks, forever, with no error.
            with contextlib.suppress(Exception):
                self._httpd.shutdown()
            thread.join(timeout=3.0)
        with contextlib.suppress(Exception):
            self._httpd.server_close()

    def open_browser(self) -> bool:
        """Show the UI in the user's browser.  False if there was nothing to open."""
        try:
            return bool(webbrowser.open(self.url))
        except Exception:
            return False

    def __enter__(self) -> LocalApp:
        self.start()
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.stop()


def summary_lines(app: LocalApp) -> list[str]:
    """The few facts worth putting in front of someone: where it is, what it knows."""
    lines = [f"buttcrack {__version__}", f"Listening on {app.url}"]
    if app.port != PREFERRED_PORT:
        # The bookmark people have is the familiar port; saying why this is not
        # it is worth the line, and it names the URL to bookmark instead.
        lines.append(f"port {PREFERRED_PORT} was busy, so this is {app.port} -- bookmark this address")
    try:
        from .ciphers import ALL_CIPHERS
        from .lang import LANGUAGES, get_model
        from .paradigm import RECORDS

        model = get_model()
        lines.append(
            f"{len(ALL_CIPHERS)} ciphers | {model.ngram_count(4):,} quadgrams | "
            f"{len(model.words):,} words | {len(LANGUAGES)} languages"
        )
        lines.append(f"{len(RECORDS)} verified Paradigm Kryptos records | exact-match recognition offline")
    except Exception:  # a broken model must not stop the window from appearing
        lines.append("language model unavailable")
    lines.append("Your text is never uploaded: the server is this machine.")
    return lines


# --------------------------------------------------------------------------- #
# the control window
# --------------------------------------------------------------------------- #


def _icon_path() -> str | None:
    """The .ico, from the frozen bundle or -- running from a checkout -- the source tree."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(getattr(sys, "_MEIPASS", root), "buttcrack.ico"),
        os.path.join(root, "packaging", "windows", "assets", "buttcrack.ico"),
    ]
    return next((path for path in candidates if os.path.isfile(path)), None)


def enable_dpi_awareness() -> bool:
    """Tell Windows this process draws its own pixels.  No-op anywhere else.

    A DPI-unaware process on a 125-200% display is rendered at 96 dpi and then
    bitmap-stretched by the compositor, which is what makes every Tk widget
    blurry and slightly wrong-sized.  System awareness is the cheap 90% of the
    fix and needs nothing but this call, done before the first window exists;
    per-monitor v2 needs a manifest, which is a packaging change.

    Returns whether the process is aware.  Fails quietly: a manifest may have
    set this already, which is the same outcome by a different route.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        try:
            # PROCESS_SYSTEM_DPI_AWARE, Windows 8.1 and later.
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()  # the pre-8.1 call
        return True
    except Exception:
        return False


def open_path(target: Path) -> bool:
    """Hand a file or folder to the desktop environment.  False if it could not."""
    try:
        if sys.platform == "win32":
            os.startfile(target)  # type: ignore[attr-defined]  # Windows only
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return True
    except Exception:
        return False


def open_data_folder() -> bool:
    """Show the data directory in the file manager, creating it if necessary."""
    directory = userdata.data_dir()
    with contextlib.suppress(OSError):
        directory.mkdir(parents=True, exist_ok=True)
    return open_path(directory)


def run_window(app: LocalApp) -> bool:
    """Show the Tk control panel and block until it is closed.

    Returns False if Tk is unavailable (a headless box, a Python built without
    it), which tells the caller to fall back to the console loop.
    """
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return False

    # Before the first window exists: awareness is a process property, and Tk
    # reads it when it creates one.
    enable_dpi_awareness()
    try:
        root = tk.Tk()
    except Exception:  # no display
        return False

    with contextlib.suppress(Exception):
        # Tk assumes 96 dpi; this is the display's own answer, so the window is
        # the size the rest of the desktop is.
        root.tk.call("tk", "scaling", root.winfo_fpixels("1i") / 72.0)

    stopping = threading.Event()
    from .project import Project

    active_project = [Project(source="desktop")]

    def shutdown() -> None:
        if stopping.is_set():
            return
        stopping.set()
        with contextlib.suppress(Exception):
            remember_geometry()
        with contextlib.suppress(Exception):
            tray.stop()
        with contextlib.suppress(Exception):
            root.destroy()

    root.title("Buttcrack")
    root.minsize(430, 0)
    root.resizable(False, False)

    # Panels the user has opened, so their geometry can be written back on the
    # way out (see "what the app remembers" above).
    open_panels: dict[str, Any] = {}
    remembered_windows = load_state().get("windows") or {}

    def open_panel(title: str, width: int, height: int) -> tk.Toplevel:
        """A panel, put back where the user last had it."""
        opened = tk.Toplevel(root)
        opened.title(title)
        opened.minsize(width, height)
        place = remembered_windows.get(title)
        if isinstance(place, str):
            with contextlib.suppress(Exception):
                opened.geometry(place)
        open_panels[title] = opened
        return opened

    def remember_geometry() -> None:
        """Write back where the windows are, so the next launch opens there."""
        windows = {"main": root.winfo_geometry()} if usable_geometry(root.winfo_geometry()) else {}
        for title, panel in open_panels.items():
            with contextlib.suppress(Exception):
                if panel.winfo_exists() and usable_geometry(panel.winfo_geometry()):
                    windows[title] = panel.winfo_geometry()
        if windows:
            save_state(windows=windows)
    with contextlib.suppress(Exception):
        icon = _icon_path()
        if icon:
            root.iconbitmap(icon)

    frame = ttk.Frame(root, padding=18)
    frame.grid(sticky="nsew")

    ttk.Label(frame, text="Buttcrack is running", font=("Segoe UI", 13, "bold")).grid(
        row=0, column=0, columnspan=3, sticky="w"
    )

    address = tk.StringVar(value=app.url)
    entry = ttk.Entry(frame, textvariable=address, state="readonly", width=34)
    entry.grid(row=1, column=0, columnspan=2, sticky="we", pady=(12, 0))

    def copy_address() -> None:
        focused = root.focus_get()
        if isinstance(focused, (tk.Entry, tk.Text)) and focused.selection_present():
            # Ctrl+C in a field means "copy what I selected", not "copy the URL".
            with contextlib.suppress(Exception):
                focused.event_generate("<<Copy>>")
            return
        with contextlib.suppress(Exception):
            root.clipboard_clear()
            root.clipboard_append(app.url)
        status.set("Address copied to the clipboard.")

    def copy_diagnostics() -> None:
        """One paste for a support email: version, paths, port, tray."""
        from .diagnostics import report_text

        body = report_text(port=app.port, tray=tray.active)
        with contextlib.suppress(Exception):
            root.clipboard_clear()
            root.clipboard_append(body)
        status.set("Diagnostics copied to the clipboard.")

    ttk.Button(frame, text="Copy", width=8, command=copy_address).grid(row=1, column=2, sticky="e", pady=(12, 0))

    def open_browser() -> None:
        status.set("Opened in your browser." if app.open_browser() else "Could not open a browser.")

    def open_candidate_panel() -> None:
        panel = open_panel("Buttcrack — Candidate Manager", 760, 560)
        body = ttk.Frame(panel, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Candidate Manager", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(
            body,
            text="Candidates remain hypotheses until exact round-trip and independent recheck both pass.",
            foreground="#555555",
        ).pack(anchor="w", pady=(2, 10))
        labels = (
            "Plaintext",
            "Score",
            "Key",
            "Algorithm",
            "Source attack",
            "Chunk/job ID",
            "Exact verification",
            "Independent recheck",
            "Notes",
        )
        fields = {}
        for label in labels:
            ttk.Label(body, text=label).pack(anchor="w", pady=(4, 1))
            if label in ("Exact verification", "Independent recheck"):
                widget = ttk.Combobox(body, values=("not_checked", "passed", "failed"), state="readonly")
                widget.set("not_checked")
            else:
                widget = tk.Entry(body)
            widget.pack(fill="x")
            fields[label] = widget
        rows = tk.Listbox(body, height=8)
        rows.pack(fill="both", expand=True, pady=(10, 0))

        def refresh():
            rows.delete(0, "end")
            for i, c in enumerate(active_project[0].candidates):
                ev = c.get("evidence", {})
                rows.insert(
                    "end",
                    f"{i}: {ev.get('status', 'heuristic')} | score={ev.get('score', '—')} | {c.get('plaintext', '')[:70]}",
                )

        def add():
            evidence = {
                "score": fields["Score"].get(),
                "key": fields["Key"].get(),
                "algorithm": fields["Algorithm"].get(),
                "source_attack": fields["Source attack"].get(),
                "chunk_job_id": fields["Chunk/job ID"].get(),
                "exact_round_trip": fields["Exact verification"].get(),
                "independent_recheck": fields["Independent recheck"].get(),
                "status": "heuristic",
                "notes": fields["Notes"].get(),
            }
            active_project[0].add_candidate(fields["Plaintext"].get(), evidence)
            refresh()

        def set_status(status):
            selection = rows.curselection()
            if not selection:
                return
            candidate = active_project[0].candidates[selection[0]]
            evidence = candidate.get("evidence", {})
            if status == "promoted_pending_recheck" and not (
                evidence.get("exact_round_trip") == "passed" and evidence.get("independent_recheck") == "passed"
            ):
                tk.messagebox.showwarning(
                    "Promotion blocked",
                    "Exact round-trip validation and independent recheck must both pass.",
                    parent=panel,
                )
                return
            evidence["status"] = status
            refresh()

        actions = ttk.Frame(body)
        actions.pack(anchor="w", pady=(8, 0))
        ttk.Button(actions, text="Add candidate", command=add).pack(side="left")
        ttk.Button(actions, text="Promote", command=lambda: set_status("promoted_pending_recheck")).pack(
            side="left", padx=6
        )
        ttk.Button(actions, text="Reject", command=lambda: set_status("rejected")).pack(side="left")
        refresh()

    def open_campaign_dashboard() -> None:
        import csv
        import json
        import time
        from tkinter import filedialog

        from .results_db import ResultDB

        panel = open_panel("Buttcrack — PK9 Campaign", 760, 560)
        body = ttk.Frame(panel, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="PK9 Global Campaign", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        stats = tk.StringVar()
        ttk.Label(body, textvariable=stats, justify="left").pack(anchor="w", pady=10)
        view = tk.Text(body, height=18, state="disabled")
        view.pack(fill="both", expand=True)

        def data():
            # Not a path relative to the current directory: in an installed copy
            # there is no checkout, the shortcut's working directory is not
            # ours, and the parent directory would not exist, so SQLite would
            # refuse to open the file and this panel would show "ledger
            # unavailable" for everyone.  See buttcrack/userdata.py.
            db = ResultDB(pk9_ledger())
            rows = db.recent(10000)
            meta = active_project[0].campaign
            total = int(meta.get("total_chunks", len(rows)))
            counts = {s: sum(1 for r in rows if r[1] == s) for s in ("completed", "interrupted", "queued")}
            done = counts["completed"]
            runtimes = []
            for r in rows:
                if r[2] is not None:
                    runtimes.append(r)
            throughput = (done / (sum(float(r[2] or 0) for r in runtimes) or 1)) * 3600
            remaining = max(0, total - done)
            eta = remaining / throughput * 3600 if throughput else None
            board = db.leaderboard(1000)
            local = max((r[2] for r in rows if r[2] is not None), default=None)
            globalbest = board[0] if board else None
            return db, rows, meta, total, counts, throughput, eta, local, globalbest

        def refresh():
            try:
                db, rows, meta, total, c, throughput, eta, local, gb = data()
                eta_text = f"{eta / 3600:.1f}h" if eta is not None else "—"
                stats.set(
                    f"Chunks total: {total} | completed: {c['completed']} | interrupted: {c['interrupted']} | queued: {c['queued']}\nThroughput: {throughput:.2f} chunks/hour | ETA: {eta_text} | current: {meta.get('current_chunk', '—')}\nLocal best: {local if local is not None else '—'} | Global best: {gb.get('best_score', '—') if gb else '—'} (ledger provenance)"
                )
                text = "Candidate | score | verification | status\n" + "\n".join(
                    f"{r[3] or '(none)'} | {r[2]} | {r[4]} | {r[1]}" for r in rows[:80]
                )
                view.configure(state="normal")
                view.delete("1.0", "end")
                view.insert("1.0", text)
                view.configure(state="disabled")
            except Exception as e:
                stats.set(f"Campaign ledger unavailable: {e}")

        def export(kind):
            db, _, _, _, _, _, _, _, _ = data()
            target = filedialog.asksaveasfilename(
                defaultextension="." + kind, filetypes=[(kind.upper(), "*." + kind)]
            )
            if not target:
                return
            board = db.leaderboard(10000)
            if kind == "json":
                Path(target).write_text(json.dumps(board, indent=2), encoding="utf-8")
            else:
                with open(target, "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=["candidate", "best_score", "status", "first_seen"])
                    w.writeheader()
                    w.writerows({k: x.get(k) for k in w.fieldnames} for x in board)

        def recheck():
            active_project[0].campaign["last_independent_recheck_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            active_project[0].notes.append(
                "Independent recheck requested; no promotion occurs without exact round-trip validation."
            )
            refresh()

        def resume():
            active_project[0].campaign["resume_requested"] = True
            active_project[0].campaign["resume_requested_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            refresh()

        actions = ttk.Frame(body)
        actions.pack(anchor="w")
        for label, cmd in (
            ("Refresh", refresh),
            ("Resume campaign", resume),
            ("Independent recheck", recheck),
            ("Export JSON", lambda: export("json")),
            ("Export CSV", lambda: export("csv")),
        ):
            ttk.Button(actions, text=label, command=cmd).pack(side="left", padx=(0, 6))
        refresh()

    def open_scoring_dashboard() -> None:
        from .scoring import score_all

        panel = open_panel("Buttcrack — Score Dashboard", 650, 480)
        body = ttk.Frame(panel, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Language Score Dashboard", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(
            body,
            text="Separate ranking clues; not a proof. Random and language calibration may be unavailable.",
            foreground="#555555",
            wraplength=600,
        ).pack(anchor="w", pady=(2, 10))
        input_box = tk.Text(body, height=7)
        input_box.pack(fill="x")
        output = tk.Text(body, height=14, state="disabled")
        output.pack(fill="both", expand=True, pady=(10, 0))

        def measure():
            rows = score_all(input_box.get("1.0", "end"))
            report = "\\n".join(f"{r.name}: {r.value:.6f}\\n  {r.explanation}" for r in rows)
            output.configure(state="normal")
            output.delete("1.0", "end")
            output.insert("1.0", report)
            output.configure(state="disabled")
            active_project[0].notes.append(report)

        ttk.Button(body, text="Measure separate signals", command=measure).pack(anchor="w", pady=(8, 0))

    def open_transposition_lab() -> None:
        from tkinter import filedialog

        from .transposition import decrypt, encrypt

        panel = open_panel("Buttcrack — Transposition Lab", 760, 620)
        body = ttk.Frame(panel, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Interactive Transposition Grid", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        text = tk.StringVar(value="MEETATNOONXXXXXX")
        key = tk.StringVar(value="KEYS")
        key2 = tk.StringVar(value="")
        fill = tk.StringVar(value="row-fill")
        route = tk.StringVar(value="rank-order")
        direction = tk.StringVar(value="encrypt")
        double = tk.BooleanVar()
        controls = ttk.Frame(body)
        controls.pack(fill="x")
        for label, var in (("Text", text), ("Key", key), ("Second key", key2)):
            ttk.Label(controls, text=label).pack(side="left", padx=(0, 3))
            ttk.Entry(controls, textvariable=var, width=18).pack(side="left", padx=(0, 8))
        ttk.Combobox(
            controls, textvariable=fill, values=("row-fill", "column-fill"), state="readonly", width=12
        ).pack(side="left", padx=3)
        ttk.Combobox(
            controls,
            textvariable=route,
            values=("rank-order", "original-order", "spiral-clockwise", "spiral-counterclockwise"),
            state="readonly",
            width=18,
        ).pack(side="left", padx=3)
        ttk.Checkbutton(body, text="Double transposition", variable=double).pack(anchor="w", pady=5)
        ttk.Radiobutton(body, text="Encrypt", variable=direction, value="encrypt").pack(anchor="w")
        ttk.Radiobutton(body, text="Decrypt", variable=direction, value="decrypt").pack(anchor="w")
        grid = ttk.Frame(body)
        grid.pack(fill="both", expand=True, pady=8)
        history = []
        cursor = [-1]
        report = tk.Text(body, height=8, state="disabled")
        report.pack(fill="x")

        def worksheet():
            raw = "".join(text.get().split())
            cols = max(1, len(key.get()))
            rows = (len(raw) + cols - 1) // cols
            matrix = [
                [raw[r * cols + c] if r * cols + c < len(raw) else "·" for c in range(cols)] for r in range(rows)
            ]
            return raw, cols, matrix

        def draw(matrix):
            for w in grid.winfo_children():
                w.destroy()
            for c in range(len(matrix[0]) if matrix else 0):
                ttk.Label(grid, text=f"{c + 1}", relief="raised", width=4).grid(row=0, column=c, padx=1, pady=1)
            for r, row in enumerate(matrix):
                for c, ch in enumerate(row):
                    ttk.Label(grid, text=ch, relief="groove", width=4, anchor="center").grid(
                        row=r + 1, column=c, padx=1, pady=1
                    )

        def render():
            try:
                raw, cols, matrix = worksheet()
                out = raw
                if direction.get() == "encrypt":
                    out = encrypt(raw, key.get())
                else:
                    out = decrypt(raw, key.get())
                if double.get() and key2.get():
                    out = encrypt(out, key2.get()) if direction.get() == "encrypt" else decrypt(out, key2.get())
                draw(matrix)
                msg = (
                    f"fill={fill.get()} route={route.get()} key={key.get()} second_key={key2.get()}\nintermediate grid\n"
                    + "\n".join(" ".join(r) for r in matrix)
                    + f"\noutput={out}"
                )
                report.configure(state="normal")
                report.delete("1.0", "end")
                report.insert("1.0", msg)
                report.configure(state="disabled")
                del history[cursor[0] + 1 :]
                history.append(msg)
                cursor[0] += 1
                active_project[0].notes.append(msg)
            except Exception as e:
                report.configure(state="normal")
                report.delete("1.0", "end")
                report.insert("1.0", f"Input error: {e}")
                report.configure(state="disabled")

        def move(delta):
            n = max(0, min(len(history) - 1, cursor[0] + delta))
            if history and n != cursor[0]:
                cursor[0] = n
                report.configure(state="normal")
                report.delete("1.0", "end")
                report.insert("1.0", history[n])
                report.configure(state="disabled")

        def export():
            target = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Worksheet", "*.txt")])
            if target:
                Path(target).write_text(
                    report.get("1.0", "end")
                    + f"\nparameters: fill={fill.get()}, route={route.get()}, double={double.get()}, direction={direction.get()}",
                    encoding="utf-8",
                )

        actions = ttk.Frame(body)
        actions.pack(anchor="w")
        ttk.Button(actions, text="Render step", command=render).pack(side="left")
        ttk.Button(actions, text="Step back", command=lambda: move(-1)).pack(side="left", padx=5)
        ttk.Button(actions, text="Step forward", command=lambda: move(1)).pack(side="left")
        ttk.Button(actions, text="Export worksheet", command=export).pack(side="left", padx=5)
        render()

    def open_verification() -> None:
        from .verification import round_trip

        panel = open_panel("Buttcrack — Verification Center", 700, 620)
        body = ttk.Frame(panel, padding=16)
        body.pack(fill="both", expand=True)
        fields = {}
        for label in (
            "Plaintext",
            "Expected ciphertext",
            "Produced ciphertext",
            "Algorithm",
            "Key",
            "Alphabet",
            "Normalization",
            "Padding",
        ):
            ttk.Label(body, text=label).pack(anchor="w", pady=(6, 2))
            if label == "Algorithm":
                from .ciphers import all_ciphers

                widget = ttk.Combobox(body, values=[cipher.name for cipher in all_ciphers()], state="normal")
                widget.pack(fill="x")
                fields[label] = widget
            elif label == "Normalization":
                widget = ttk.Combobox(
                    body, values=["letters-only", "preserve-spaces", "preserve-punctuation"], state="readonly"
                )
                widget.set("letters-only")
                widget.pack(fill="x")
                fields[label] = widget
            elif label == "Padding":
                widget = ttk.Combobox(
                    body, values=["none", "documented nulls", "PKCS-style (document explicitly)"], state="normal"
                )
                widget.set("none")
                widget.pack(fill="x")
                fields[label] = widget
            else:
                widget = tk.Text(
                    body,
                    height=2 if label in ("Plaintext", "Expected ciphertext", "Produced ciphertext") else 1,
                    wrap="word",
                )
                widget.pack(fill="x")
                fields[label] = widget
        output = tk.Text(body, height=10, state="disabled", wrap="word")
        output.pack(fill="both", expand=True, pady=(10, 0))

        def compare():
            plain = fields["Plaintext"].get("1.0", "end").strip()
            expected = fields["Expected ciphertext"].get("1.0", "end").strip()
            produced = fields["Produced ciphertext"].get("1.0", "end").strip()
            algorithm = fields["Algorithm"].get().strip()
            key = fields["Key"].get("1.0", "end").strip()
            if algorithm:
                try:
                    from .ciphers import get

                    cipher = get(algorithm)
                    produced = cipher.encrypt(plain, key)
                    fields["Produced ciphertext"].delete("1.0", "end")
                    fields["Produced ciphertext"].insert("1.0", produced)
                except Exception as error:
                    produced = fields["Produced ciphertext"].get("1.0", "end").strip()
                    status.set(f"Algorithm unavailable; comparing supplied output: {error}")
            result = round_trip(plain, expected, lambda _: produced)
            # The UI accepts a produced stream through the expected field when no cipher runner is attached.
            normalized_expected = "".join(expected.split())
            normalized_produced = "".join(produced.split())
            h = hashlib.sha256(normalized_expected.encode()).hexdigest()
            ph = hashlib.sha256(normalized_produced.encode()).hexdigest()
            text = f"Status: {'EXACT MATCH' if result.exact else 'MISMATCH'}\\nAlgorithm: {fields['Algorithm'].get().strip()}\\nKey: {fields['Key'].get('1.0', 'end').strip()}\\nAlphabet: {fields['Alphabet'].get('1.0', 'end').strip()}\\nNormalization: {fields['Normalization'].get().strip()}\\nPadding: {fields['Padding'].get('1.0', 'end').strip()}\\nNormalized expected: {normalized_expected}\\nNormalized produced: {normalized_produced}\\nExpected SHA-256: {h}\\nProduced SHA-256: {ph}\\nDetail: {result.message}\\nEvidence: reproduction requires an attached encryptor and independent recheck."
            output.configure(state="normal")
            output.delete("1.0", "end")
            output.insert("1.0", text)
            output.configure(state="disabled")
            active_project[0].notes.append(text)

        ttk.Button(body, text="Compare / verify", command=compare).pack(anchor="w", pady=(8, 0))

    def open_crib_lab() -> None:
        from tkinter import filedialog

        from .crib import consistent_period, implied_shifts

        panel = open_panel("Buttcrack — Crib Dragging Lab", 700, 520)
        body = ttk.Frame(panel, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Ciphertext").pack(anchor="w")
        cipher = tk.Text(body, height=4)
        cipher.pack(fill="x")
        ttk.Label(body, text="Crib").pack(anchor="w", pady=(8, 0))
        crib = ttk.Entry(body)
        crib.pack(fill="x")
        offset = tk.IntVar(value=0)
        period = tk.IntVar(value=1)
        ttk.Label(body, text="Offset").pack(anchor="w")
        ttk.Scale(body, from_=0, to=100, variable=offset, orient="horizontal").pack(fill="x")
        ttk.Label(body, text="Period").pack(anchor="w")
        ttk.Spinbox(body, from_=1, to=100, textvariable=period).pack(anchor="w")
        output = tk.Text(body, height=10, state="disabled")
        output.pack(fill="both", expand=True, pady=(8, 0))

        def calculate():
            shifts = implied_shifts(cipher.get("1.0", "end"), crib.get(), offset.get())
            ok = consistent_period(shifts, max(1, period.get()))
            text = f"Crib: {crib.get()}\\nOffset: {offset.get()}\\nImplied shifts: {shifts}\\nPeriod consistent: {ok}\\nStatus: worksheet hypothesis; verify against a complete model."
            active_project[0].notes.append(text)
            output.configure(state="normal")
            output.delete("1.0", "end")
            output.insert("1.0", text)
            output.configure(state="disabled")

        def export():
            target = filedialog.asksaveasfilename(
                parent=panel, defaultextension=".txt", filetypes=[("Worksheet", "*.txt")]
            )
            if target:
                Path(target).write_text(output.get("1.0", "end"), encoding="utf-8")

        actions = ttk.Frame(body)
        actions.pack(anchor="w", pady=(8, 0))
        ttk.Button(actions, text="Calculate", command=calculate).pack(side="left")
        ttk.Button(actions, text="Export worksheet", command=export).pack(side="left", padx=8)

    def open_attack_queue() -> None:
        """Show a local, checkpoint-aware attack queue scaffold."""
        from .queue import AttackQueue

        panel = open_panel("Buttcrack — Attack Queue", 620, 420)
        panel.transient(root)
        body = ttk.Frame(panel, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Attack Queue", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(
            body, text="Jobs are local and remain hypotheses until exact verification.", foreground="#555555"
        ).pack(anchor="w", pady=(2, 10))
        queue = AttackQueue()
        rows = tk.Listbox(body, height=12)
        rows.pack(fill="both", expand=True)
        state = tk.StringVar(value="Ready.")
        ttk.Label(body, textvariable=state, foreground="#2a6f3a").pack(anchor="w", pady=(8, 0))

        def refresh():
            rows.delete(0, "end")
            for job in queue.jobs:
                rows.insert("end", f"{job.status.upper():10} {job.name}")

        def new_attack():
            name = f"Local analysis {len(queue.jobs) + 1}"
            queue.add(name, lambda: {"status": "recommendations_only"})
            active_project[0].add_attack(name, {}, "queued")
            refresh()
            state.set(f"Added {name}.")

        def run_next():
            job = queue.run_next()
            refresh()
            state.set(f"Completed {job.name}." if job else "No queued jobs.")

        def cancel():
            for job in queue.jobs:
                if job.status == "queued":
                    job.status = "cancelled"
                    break
            refresh()
            state.set("Queued job cancelled.")

        def save_checkpoint():
            import json
            from tkinter import filedialog

            target = filedialog.asksaveasfilename(
                parent=panel, defaultextension=".queue.json", filetypes=[("Queue checkpoint", "*.queue.json")]
            )
            if target:
                Path(target).write_text(json.dumps(queue.checkpoint(), indent=2), encoding="utf-8")
                state.set("Checkpoint saved.")

        def export_report():
            from tkinter import filedialog

            target = filedialog.asksaveasfilename(
                parent=panel, defaultextension=".txt", filetypes=[("Text report", "*.txt")]
            )
            if target:
                Path(target).write_text(
                    "\\n".join(rows.get(0, "") for _ in [0]) + "\\n" + "\\n".join(str(x) for x in queue.checkpoint()),
                    encoding="utf-8",
                )
                state.set("Report exported.")

        actions = ttk.Frame(body)
        actions.pack(anchor="w", pady=(10, 0))
        for label, command in (
            ("New attack", new_attack),
            ("Resume", run_next),
            ("Cancel", cancel),
            ("Save checkpoint", save_checkpoint),
            ("Export report", export_report),
        ):
            ttk.Button(actions, text=label, command=command).pack(side="left", padx=(0, 6))
        refresh()

    def open_paradigm_archive() -> None:
        """Browse the exact-match PK1–PK10 corpus without implying a generic solve."""
        from .paradigm import RECORDS

        panel = open_panel("Buttcrack — Paradigm Kryptos PK1–PK10 Archive", 820, 570)
        panel.transient(root)
        body = ttk.Frame(panel, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Verified Paradigm Kryptos PK1–PK10 Archive", font=("Segoe UI", 13, "bold")).pack(
            anchor="w"
        )
        ttk.Label(
            body,
            text=(
                "These are canonical corpus records. A result is marked verified only when normalized ciphertext "
                "matches one record exactly; shared length or alphabet is not a match."
            ),
            foreground="#555555",
            wraplength=760,
        ).pack(anchor="w", pady=(2, 10))
        columns = ("id", "title", "length", "mechanism")
        tree = ttk.Treeview(body, columns=columns, show="headings", height=10)
        for name, label, width in (
            ("id", "ID", 55),
            ("title", "Challenge", 230),
            ("length", "CT", 55),
            ("mechanism", "Recovered construction", 440),
        ):
            tree.heading(name, text=label)
            tree.column(name, width=width, stretch=name == "mechanism")
        for record in RECORDS:
            tree.insert(
                "",
                "end",
                iid=record.challenge_id,
                values=(record.challenge_id, record.title, record.ciphertext_length, record.mechanism),
            )
        tree.pack(fill="x")
        detail = tk.Text(body, height=15, wrap="word", state="disabled")
        detail.pack(fill="both", expand=True, pady=(10, 0))

        def selected():
            item = tree.selection()
            return next((record for record in RECORDS if item and record.challenge_id == item[0]), None)

        def show_record(_event=None) -> None:
            record = selected()
            if record is None:
                return
            content = (
                f"{record.challenge_id} — {record.title}\n\n"
                f"Recovered construction: {record.mechanism}\n"
                f"Key material: {record.key}\n"
                f"Ciphertext letters: {record.ciphertext_length}\n"
                f"Plaintext letters: {record.plaintext_length}\n"
                f"Plaintext SHA-256: {record.plaintext_sha256}\n"
                f"Verification: {record.verification}\n\n"
                f"Ciphertext\n{record.ciphertext}\n\nPlaintext\n{record.plaintext}"
            )
            detail.configure(state="normal")
            detail.delete("1.0", "end")
            detail.insert("1.0", content)
            detail.configure(state="disabled")

        def copy(kind: str) -> None:
            record = selected()
            if record is None:
                status.set("Select a PK record first.")
                return
            value = record.ciphertext if kind == "ciphertext" else record.plaintext
            with contextlib.suppress(Exception):
                root.clipboard_clear()
                root.clipboard_append(value)
            status.set(f"{record.challenge_id} {kind} copied to the clipboard.")

        actions = ttk.Frame(body)
        actions.pack(anchor="w", pady=(10, 0))
        ttk.Button(actions, text="Copy ciphertext", command=lambda: copy("ciphertext")).pack(side="left")
        ttk.Button(actions, text="Copy plaintext", command=lambda: copy("plaintext")).pack(side="left", padx=(8, 0))
        tree.bind("<<TreeviewSelect>>", show_record)
        tree.selection_set(RECORDS[0].challenge_id)
        show_record()

    def open_local_assistant() -> None:
        """Open the dependency-free assistant without leaving the desktop app."""
        from .assistant import explain
        from .local_model import LocalModelAdapter
        from .project import Project
        from .provenance import AssistantRecord

        panel = open_panel("Buttcrack — Local Assistant", 620, 440)
        panel.transient(root)
        body = ttk.Frame(panel, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Local Cryptanalysis Assistant", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(
            body, text="Runs offline. Recommendations are hypotheses, not solutions.", foreground="#555555"
        ).pack(anchor="w", pady=(2, 4))
        providers = "; ".join(
            f"{item.provider}: {'available' if item.available else 'not installed'}"
            for item in LocalModelAdapter().capabilities()
        )
        ttk.Label(body, text=f"Providers — {providers}", foreground="#555555", wraplength=580).pack(
            anchor="w", pady=(0, 10)
        )
        input_box = tk.Text(body, height=7, wrap="word")
        input_box.pack(fill="x")
        output_box = tk.Text(body, height=13, wrap="word", state="disabled")
        output_box.pack(fill="both", expand=True, pady=(10, 0))

        def analyze() -> None:
            result = explain(input_box.get("1.0", "end"))
            output_box.configure(state="normal")
            output_box.delete("1.0", "end")
            output_box.insert("1.0", result)
            output_box.configure(state="disabled")
            active_project[0].notes.append(result)
            AssistantRecord.create(
                "explainable-planner", "built-in", input_box.get("1.0", "end"), result, input_box.get("1.0", "end")
            ).save_jsonl(assistant_log())

        def open_session() -> None:
            from tkinter import filedialog

            target = filedialog.askopenfilename(
                parent=panel,
                title="Open cryptanalysis session",
                filetypes=[("Buttcrack session", "*.kryptos-project.json"), ("JSON", "*.json")],
            )
            if target:
                try:
                    loaded = Project.load(target)
                    active_project[0] = loaded
                    input_box.delete("1.0", "end")
                    input_box.insert("1.0", loaded.ciphertext)
                    output_box.configure(state="normal")
                    output_box.delete("1.0", "end")
                    output_box.insert("1.0", "Session loaded. Run analysis to refresh recommendations.")
                    output_box.configure(state="disabled")
                    status.set(f"Loaded session: {os.path.basename(target)}")
                except Exception as error:
                    status.set(f"Could not load session: {error}")

        def save_session() -> None:
            from tkinter import filedialog

            target = filedialog.asksaveasfilename(
                parent=panel,
                title="Save cryptanalysis session",
                defaultextension=".kryptos-project.json",
                filetypes=[("Buttcrack session", "*.kryptos-project.json"), ("JSON", "*.json")],
            )
            if target:
                active_project[0].ciphertext = input_box.get("1.0", "end").strip()
                active_project[0].source = "desktop local assistant"
                active_project[0].save(target)
                status.set(f"Saved session: {os.path.basename(target)}")

        actions = ttk.Frame(body)
        actions.pack(anchor="w", pady=(10, 0))
        ttk.Button(actions, text="Analyze locally", command=analyze).pack(side="left")
        ttk.Button(actions, text="Open session", command=open_session).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Save session", command=save_session).pack(side="left", padx=(8, 0))
        input_box.focus_set()

    ttk.Button(frame, text="Verify", command=open_verification).grid(row=2, column=0, sticky="w", pady=(14, 0))
    ttk.Button(frame, text="Crib Lab", command=open_crib_lab).grid(row=2, column=1, sticky="w", pady=(14, 0))
    ttk.Button(frame, text="Attack Queue", command=open_attack_queue).grid(row=2, column=2, sticky="w", pady=(14, 0))
    ttk.Button(frame, text="Local Assistant", command=open_local_assistant).grid(
        row=3, column=0, sticky="w", pady=(4, 0)
    )
    ttk.Button(frame, text="Open Buttcrack", command=open_browser).grid(row=3, column=1, sticky="w", pady=(4, 0))
    ttk.Button(frame, text="Candidates", command=open_candidate_panel).grid(row=3, column=2, sticky="e", pady=(4, 0))
    ttk.Button(frame, text="Hide", command=lambda: hide()).grid(row=4, column=0, sticky="w", pady=(4, 0))
    ttk.Button(frame, text="Transposition Lab", command=open_transposition_lab).grid(
        row=4, column=1, sticky="w", pady=(4, 0)
    )
    ttk.Button(frame, text="Quit", command=shutdown).grid(row=4, column=2, sticky="e", pady=(4, 0))
    ttk.Button(frame, text="Score Dashboard", command=open_scoring_dashboard).grid(
        row=5, column=0, sticky="w", pady=(4, 0)
    )
    ttk.Button(frame, text="PK9 Campaign", command=open_campaign_dashboard).grid(
        row=5, column=1, sticky="w", pady=(4, 0)
    )
    ttk.Button(frame, text="PK1–10 Archive", command=open_paradigm_archive).grid(
        row=5, column=2, sticky="e", pady=(4, 0)
    )

    support = ttk.Frame(frame)
    support.grid(row=11, column=0, columnspan=3, sticky="w", pady=(10, 0))
    ttk.Button(support, text="Copy diagnostics", command=copy_diagnostics).grid(row=0, column=0, sticky="w")
    ttk.Button(support, text="Open data folder", command=open_data_folder).grid(row=0, column=1, sticky="w", padx=(8, 0))

    ttk.Separator(frame, orient="horizontal").grid(row=6, column=0, columnspan=3, sticky="we", pady=14)

    for offset, line in enumerate(summary_lines(app)[1:]):
        ttk.Label(frame, text=line, wraplength=390, foreground="#555555").grid(
            row=7 + offset, column=0, columnspan=3, sticky="w", pady=(0, 2)
        )

    status = tk.StringVar(value="Ready.")
    ttk.Label(frame, textvariable=status, foreground="#2a6f3a").grid(
        row=23, column=0, columnspan=3, sticky="w", pady=(12, 0)
    )

    frame.columnconfigure(0, weight=1)

    hidden_once = [False]

    def hide() -> None:
        if tray.active:
            root.withdraw()
            status.set("Hidden. Use the tray icon to bring it back.")
            if not hidden_once[0]:
                # The difference between "the app closed" and "the app is in the
                # tray" is one balloon, shown once, never again.
                hidden_once[0] = True
                tray.notify("Buttcrack is still running", "Click the tray icon to bring the window back.")
        else:
            root.iconify()

    def show() -> None:
        with contextlib.suppress(Exception):
            root.deiconify()
            root.lift()
            root.focus_force()

    # The tray is a bonus, not a requirement: on anything but Windows -- or if
    # the shell refuses the icon -- `start` reports False and the Hide button
    # quietly becomes a normal minimise.
    from ._wintray import TrayIcon

    tray = TrayIcon(
        title="Buttcrack",
        icon_path=_icon_path(),
        items=(
            ("Open Buttcrack", lambda: root.after(0, open_browser)),
            ("Show window", lambda: root.after(0, show)),
            ("Copy address", lambda: root.after(0, copy_address)),
            ("Copy diagnostics", lambda: root.after(0, copy_diagnostics)),
            ("Open data folder", lambda: root.after(0, open_data_folder)),
            ("Quit", lambda: root.after(0, shutdown)),
        ),
        on_activate=lambda: root.after(0, show),
    )
    tray.start()

    root.protocol("WM_DELETE_WINDOW", hide if tray.active else shutdown)

    def show_about() -> None:
        from tkinter import messagebox

        messagebox.showinfo(
            "About Buttcrack",
            f"Buttcrack {__version__}\n\n"
            "Everything runs on this machine: the server is 127.0.0.1 and nothing\n"
            "is uploaded. The language model, the ciphers and the archive all ship\n"
            "with the program.\n\n"
            f"Data: {userdata.data_dir()}\n"
            f"Log: {log_path()}",
        )

    def open_log() -> None:
        open_path(log_path())

    # A menu bar is how a desktop application says what it can do; the buttons
    # below are the shortcuts for the four things people actually press.
    menu_bar = tk.Menu(root)
    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="Open in browser", accelerator="F1", command=open_browser)
    file_menu.add_command(label="Copy address", accelerator="Ctrl+C", command=copy_address)
    file_menu.add_separator()
    file_menu.add_command(label="Hide to tray", accelerator="Ctrl+H", command=hide)
    file_menu.add_command(label="Quit", accelerator="Ctrl+Q", command=shutdown)
    menu_bar.add_cascade(label="File", menu=file_menu)

    lab_entries = (
        ("Candidate Manager", open_candidate_panel),
        ("PK9 Campaign", open_campaign_dashboard),
        ("Score Dashboard", open_scoring_dashboard),
        ("Transposition Lab", open_transposition_lab),
        ("Verification Center", open_verification),
        ("Crib Dragging Lab", open_crib_lab),
        ("Attack Queue", open_attack_queue),
        ("PK1-PK10 Archive", open_paradigm_archive),
        ("Local Assistant", open_local_assistant),
    )
    labs_menu = tk.Menu(menu_bar, tearoff=0)
    for number, (label, opener) in enumerate(lab_entries, start=1):
        labs_menu.add_command(label=label, accelerator=f"Alt+{number}", command=opener)
    menu_bar.add_cascade(label="Labs", menu=labs_menu)

    help_menu = tk.Menu(menu_bar, tearoff=0)
    help_menu.add_command(label="Copy diagnostics", accelerator="Ctrl+D", command=copy_diagnostics)
    help_menu.add_command(label="Open data folder", command=open_data_folder)
    help_menu.add_command(label="Open log file", command=open_log)
    help_menu.add_separator()
    help_menu.add_command(label="About Buttcrack", command=show_about)
    menu_bar.add_cascade(label="Help", menu=help_menu)
    root.config(menu=menu_bar)

    shortcuts = (
        ("<F1>", open_browser),
        ("<Control-c>", copy_address),
        ("<Control-d>", copy_diagnostics),
        ("<Control-h>", hide),
        ("<Control-l>", open_log),
        ("<Control-q>", shutdown),
    )
    for sequence, action in shortcuts:
        root.bind_all(sequence, lambda _event, run=action: run())
    for number, (_label, opener) in enumerate(lab_entries, start=1):
        root.bind_all(f"<Alt-Key-{number}>", lambda _event, run=opener: run())

    # Tk ignores signals while it is in its own event loop unless it wakes up
    # periodically; this also gives Ctrl-C somewhere to land.
    def tick() -> None:
        if not stopping.is_set():
            root.after(400, tick)

    root.after(400, tick)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        shutdown()
    finally:
        with contextlib.suppress(Exception):
            tray.stop()
    return True


def run_console(app: LocalApp) -> None:
    """No window: print where it is and wait for Ctrl-C."""
    for line in summary_lines(app):
        print(line)
    print("Press Ctrl-C to stop.")
    try:
        while True:
            threading.Event().wait(0.5)
    except KeyboardInterrupt:
        print("\nshutting down")


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #


def run(
    port: int = 0,
    open_browser: bool = True,
    window: bool | None = None,
    on_ready: Callable[[LocalApp], None] | None = None,
    reuse: bool = False,
) -> int:
    """Start the desktop app and block until it is closed.

    ``window=None`` means "show one if you can"; ``False`` forces the console
    loop, which is what ``--console`` and a headless server want.  ``reuse``
    asks the copy that is already running to take over, which is what a second
    click on the Start-menu shortcut should do.
    """
    ensure_streams()
    if reuse:
        running = running_instance()
        if running is not None:
            print(f"buttcrack is already running at {running}")
            if open_browser:
                with contextlib.suppress(Exception):
                    webbrowser.open(running)
            return 0
    try:
        app = LocalApp(port=port)
    except OSError as error:
        _fatal(f"Could not start the local server: {error}")
        return 1

    app.start()
    # Only the desktop app remembers where it served: a library user building a
    # LocalApp should not have a file change under them (B6).
    if app.port != remembered_port():
        save_state(port=app.port)
    if on_ready is not None:
        with contextlib.suppress(Exception):
            on_ready(app)
    if open_browser:
        app.open_browser()

    try:
        # Three UIs, in descending order of niceness, each falling through to
        # the next when it is not available.  The message box exists because a
        # windowed .exe with no Tk has no console either: without it the user
        # is left with an invisible process only Task Manager can end.
        shown = False
        if window is not False:
            shown = run_window(app) or _message_box_wait(app)
        if not shown:
            run_console(app)
    finally:
        app.stop()
    return 0


def _message_box_wait(app: LocalApp) -> bool:
    """Last-resort window: a modal box naming the address.  False if unavailable."""
    if sys.platform != "win32" or not is_frozen():
        return False
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            f"Buttcrack is running at {app.url}\n\n"
            "That address is open in your browser. Leave this box open while "
            "you use it, and click OK to stop Buttcrack.",
            "Buttcrack",
            0x40,  # MB_ICONINFORMATION
        )
        return True
    except Exception:
        return False


def _fatal(message: str) -> None:
    """Report a startup failure through whatever channel exists."""
    print(f"buttcrack: {message}", file=sys.stderr)
    if sys.platform == "win32" and is_frozen():
        with contextlib.suppress(Exception):
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, message, "Buttcrack", 0x10)


def main(argv: list[str] | None = None) -> int:
    """``buttcrack-desktop`` / the frozen GUI executable."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="buttcrack app",
        description="Run buttcrack as a local desktop application (127.0.0.1 only).",
    )
    parser.add_argument("--port", "-p", type=int, default=0, help="port to use (default: 8080, or any free port)")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser on startup")
    parser.add_argument("--console", action="store_true", help="no control window; run in the terminal")
    parser.add_argument(
        "--force",
        action="store_true",
        help="start even if a copy is already running",
    )
    args = parser.parse_args(argv)

    return run(
        port=args.port,
        open_browser=not args.no_browser,
        window=False if args.console else None,
        # An explicit port is a request for a server of one's own; without one,
        # a second launch hands over to the copy that is already up.
        reuse=not args.force and not args.port,
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
