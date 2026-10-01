"""The desktop application: ``buttcrack app``.

This is what the Windows installer's Start-menu shortcut runs.  It is the same
local web interface as :mod:`buttcrack.server`, wrapped so that it behaves like
a double-clickable program rather than a command you have to remember:

* it binds **127.0.0.1 only** -- a desktop app has no business accepting
  connections from the network, unlike ``buttcrack serve`` which defaults to
  ``0.0.0.0`` so you can reach it from another machine on purpose;
* it takes whatever port is free instead of failing when 8080 is taken, so a
  second launch cannot collide with the first;
* it opens the browser for you;
* it puts a small control window on screen (and, on Windows, a tray icon) so
  there is something to close.  Closing it stops the server.

Everything degrades.  No Tk, no tray, no browser, no console -- each of those
is handled and the server still runs.  The dependency list is still empty:
``tkinter`` and ``ctypes`` are standard library.
"""

from __future__ import annotations

import contextlib
import http.server
import os
import socket
import sys
import threading
import webbrowser
from typing import Any, Callable

from . import __version__

#: A desktop app listens to itself and nothing else.
LOCAL_HOST = "127.0.0.1"

#: Tried first so the address stays familiar between launches; any free port
#: will do if something else already has it.
PREFERRED_PORT = 8080


# --------------------------------------------------------------------------- #
# frozen-build survival
# --------------------------------------------------------------------------- #


class _NullStream:
    """A file-like black hole.

    A GUI build on Windows has no console, and PyInstaller sets ``sys.stdout``
    and ``sys.stderr`` to ``None`` there.  Every ``print`` in the server, and
    every traceback the standard library writes, would then raise
    ``AttributeError: 'NoneType' object has no attribute 'write'`` -- which is
    a crash on startup for a program whose only fault was logging.
    """

    encoding = "utf-8"
    errors = "replace"

    def write(self, text: str) -> int:
        return len(text)

    def flush(self) -> None:
        return None

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
# the server, on a thread
# --------------------------------------------------------------------------- #


def free_port(preferred: int = PREFERRED_PORT, host: str = LOCAL_HOST) -> int:
    """``preferred`` if it is free on ``host``, otherwise one the OS picks."""
    if preferred:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((host, preferred))
                return preferred
            except OSError:
                pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return int(probe.getsockname()[1])


class LocalApp:
    """A running local server plus the handful of actions the UI needs."""

    def __init__(self, host: str = LOCAL_HOST, port: int = 0) -> None:
        from .server import Handler  # imported late: loading the model is slow

        http.server.ThreadingHTTPServer.allow_reuse_address = True
        http.server.ThreadingHTTPServer.daemon_threads = True
        self.host = host
        self.port = port or free_port(PREFERRED_PORT, host)
        self._httpd = http.server.ThreadingHTTPServer((self.host, self.port), Handler)
        # Port 0 would have been resolved by bind(); ask the socket, not ourselves.
        self.port = int(self._httpd.server_address[1])
        self._thread: threading.Thread | None = None

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

    def stop(self) -> None:
        """Close the socket and wait for the serving thread.  Safe to call twice."""
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
    try:
        from .ciphers import ALL_CIPHERS
        from .lang import LANGUAGES, get_model

        model = get_model()
        lines.append(
            f"{len(ALL_CIPHERS)} ciphers | {model.ngram_count(4):,} quadgrams | "
            f"{len(model.words):,} words | {len(LANGUAGES)} languages"
        )
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

    try:
        root = tk.Tk()
    except Exception:  # no display
        return False

    stopping = threading.Event()

    def shutdown() -> None:
        if stopping.is_set():
            return
        stopping.set()
        with contextlib.suppress(Exception):
            tray.stop()
        with contextlib.suppress(Exception):
            root.destroy()

    root.title("Buttcrack")
    root.minsize(430, 0)
    root.resizable(False, False)
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
        with contextlib.suppress(Exception):
            root.clipboard_clear()
            root.clipboard_append(app.url)
        status.set("Address copied to the clipboard.")

    ttk.Button(frame, text="Copy", width=8, command=copy_address).grid(row=1, column=2, sticky="e", pady=(12, 0))

    def open_browser() -> None:
        status.set("Opened in your browser." if app.open_browser() else "Could not open a browser.")

    ttk.Button(frame, text="Open Buttcrack", command=open_browser).grid(
        row=2, column=0, sticky="w", pady=(14, 0)
    )
    ttk.Button(frame, text="Hide", command=lambda: hide()).grid(row=2, column=1, sticky="w", pady=(14, 0))
    ttk.Button(frame, text="Quit", command=shutdown).grid(row=2, column=2, sticky="e", pady=(14, 0))

    ttk.Separator(frame, orient="horizontal").grid(row=3, column=0, columnspan=3, sticky="we", pady=14)

    for offset, line in enumerate(summary_lines(app)[1:]):
        ttk.Label(frame, text=line, wraplength=390, foreground="#555555").grid(
            row=4 + offset, column=0, columnspan=3, sticky="w", pady=(0, 2)
        )

    status = tk.StringVar(value="Ready.")
    ttk.Label(frame, textvariable=status, foreground="#2a6f3a").grid(
        row=20, column=0, columnspan=3, sticky="w", pady=(12, 0)
    )

    frame.columnconfigure(0, weight=1)

    def hide() -> None:
        if tray.active:
            root.withdraw()
            status.set("Hidden. Use the tray icon to bring it back.")
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
            ("Quit", lambda: root.after(0, shutdown)),
        ),
        on_activate=lambda: root.after(0, show),
    )
    tray.start()

    root.protocol("WM_DELETE_WINDOW", hide if tray.active else shutdown)

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
) -> int:
    """Start the desktop app and block until it is closed.

    ``window=None`` means "show one if you can"; ``False`` forces the console
    loop, which is what ``--console`` and a headless server want.
    """
    ensure_streams()
    try:
        app = LocalApp(port=port)
    except OSError as error:
        _fatal(f"Could not start the local server: {error}")
        return 1

    app.start()
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
    args = parser.parse_args(argv)

    return run(port=args.port, open_browser=not args.no_browser, window=False if args.console else None)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
