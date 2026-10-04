"""The desktop launcher -- what the Windows installer's shortcut runs.

The window itself cannot be tested without a display, and the tray cannot be
tested off Windows, so what is covered here is everything underneath them: the
server binds loopback, it serves the UI and the API, it shuts down cleanly, and
each optional layer reports its own absence instead of raising.

That last part is the whole design: a frozen build on a machine with no Tk, no
tray and no browser must still come up and serve the page.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import unittest
import urllib.request
from unittest import mock

from buttcrack import cli, desktop
from buttcrack._wintray import TrayIcon
from buttcrack.paradigm import RECORDS


class FreePortTests(unittest.TestCase):
    def test_prefers_the_requested_port(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            spare = probe.getsockname()[1]
        self.assertEqual(desktop.free_port(spare), spare)

    def test_falls_back_when_the_port_is_taken(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as held:
            held.bind(("127.0.0.1", 0))
            held.listen(1)
            taken = held.getsockname()[1]
            chosen = desktop.free_port(taken)
        self.assertNotEqual(chosen, taken)
        self.assertGreater(chosen, 0)


class LocalAppTests(unittest.TestCase):
    """The server half: start, serve, stop."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = desktop.LocalApp(port=0)
        cls.app.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.app.stop()

    def get(self, path: str) -> tuple[int, bytes]:
        with urllib.request.urlopen(self.app.url + path, timeout=30) as response:
            return response.status, response.read()

    def post(self, path: str, payload: dict) -> tuple[int, bytes]:
        request = urllib.request.Request(
            self.app.url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read()

    def test_binds_loopback_only(self) -> None:
        # A desktop app that listens on 0.0.0.0 is a cipher solver anyone on
        # the coffee-shop wifi can post to; `serve` is the one allowed to.
        self.assertEqual(self.app.host, "127.0.0.1")
        self.assertIn("127.0.0.1", self.app.url)

    def test_serves_the_web_interface(self) -> None:
        status, body = self.get("")
        self.assertEqual(status, 200)
        self.assertIn(b"<html", body.lower())

    def test_serves_the_api(self) -> None:
        status, body = self.get("api/health")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertIn("version", payload)
        self.assertEqual(payload["paradigm_records"], 10)

    def test_serves_the_verified_paradigm_catalog(self) -> None:
        status, body = self.get("api/paradigm")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["match_policy"], "exact normalized A-Z equality")
        self.assertEqual([record["id"] for record in payload["records"]], [f"PK{i}" for i in range(1, 11)])
        self.assertIn("ciphertext", payload["records"][0])

    def test_local_assistant_api_reports_the_exact_match_boundary(self) -> None:
        status, body = self.post("api/assistant", {"text": RECORDS[0].ciphertext})
        self.assertEqual(status, 200)
        verified = json.loads(body)
        self.assertEqual(verified["status"], "verified_exact_match")
        self.assertEqual(verified["exact_match"]["id"], "PK1")

        status, body = self.post("api/assistant", {"text": "Z" + RECORDS[0].ciphertext[1:]})
        self.assertEqual(status, 200)
        unverified = json.loads(body)
        self.assertEqual(unverified["status"], "recommendations_only")
        self.assertIsNone(unverified["exact_match"])

    def test_summary_mentions_where_it_is_listening(self) -> None:
        lines = desktop.summary_lines(self.app)
        self.assertTrue(any(self.app.url in line for line in lines))

    def test_stop_is_idempotent(self) -> None:
        app = desktop.LocalApp(port=0)
        app.start()
        app.stop()
        app.stop()

    def test_stop_without_start_does_not_hang(self) -> None:
        # Regression: ThreadingHTTPServer.shutdown() waits for serve_forever()
        # to acknowledge it and blocks forever if the loop never ran, so any
        # failure between constructing the app and starting it would have hung
        # the process instead of reporting the failure.
        app = desktop.LocalApp(port=0)
        done = threading.Event()
        threading.Thread(target=lambda: (app.stop(), done.set()), daemon=True).start()
        self.assertTrue(done.wait(timeout=10), "LocalApp.stop() hung on a server that never started")

    def test_context_manager_releases_the_port(self) -> None:
        with desktop.LocalApp(port=0) as app:
            port = app.port
        # Rebinding proves the socket really closed rather than lingering.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))


class FrozenBuildTests(unittest.TestCase):
    """The things that only break inside a PyInstaller --windowed build."""

    def test_ensure_streams_replaces_missing_stdout(self) -> None:
        # PyInstaller sets both to None in a windowed build, and the first
        # print() in the server would then raise AttributeError on startup.
        with mock.patch.object(sys, "stdout", None), mock.patch.object(sys, "stderr", None):
            desktop.ensure_streams()
            self.assertIsNotNone(sys.stdout)
            print("this must not raise", file=sys.stderr)
            sys.stdout.write("nor this")
            sys.stdout.flush()

    def test_ensure_streams_leaves_real_streams_alone(self) -> None:
        before = sys.stdout
        desktop.ensure_streams()
        self.assertIs(sys.stdout, before)

    def test_is_frozen_is_false_from_a_checkout(self) -> None:
        self.assertFalse(desktop.is_frozen())


class OptionalLayerTests(unittest.TestCase):
    """Every optional dependency has to decline politely, not explode."""

    def test_tray_declines_off_windows(self) -> None:
        tray = TrayIcon("Buttcrack", items=(("Quit", lambda: None),))
        if sys.platform == "win32":  # pragma: no cover - not where CI runs
            self.skipTest("the tray is real on Windows")
        self.assertFalse(tray.start())
        self.assertFalse(tray.active)
        tray.stop()  # must be safe even though start() did nothing

    def test_window_declines_without_a_display(self) -> None:
        # No Tk, or Tk but no display: either way run() must fall through to
        # the console loop rather than taking the process down.
        with mock.patch.dict(sys.modules, {"tkinter": None}):
            self.assertFalse(desktop.run_window(mock.MagicMock()))

    def test_open_browser_survives_having_no_browser(self) -> None:
        app = desktop.LocalApp(port=0)
        try:
            with mock.patch("webbrowser.open", side_effect=RuntimeError("no browser")):
                self.assertFalse(app.open_browser())
        finally:
            app.stop()


class CliWiringTests(unittest.TestCase):
    def test_app_is_a_subcommand(self) -> None:
        self.assertIn("app", cli.SUBCOMMANDS)

    def test_app_defaults_to_loopback_and_a_free_port(self) -> None:
        args = cli.build_parser().parse_args(["app"])
        self.assertEqual(args.port, 0)
        self.assertFalse(args.no_browser)
        self.assertFalse(args.console)

    def test_app_forwards_its_flags(self) -> None:
        with mock.patch("buttcrack.desktop.run", return_value=0) as run:
            cli.main(["app", "--console", "--no-browser", "--port", "9123"])
        run.assert_called_once_with(port=9123, open_browser=False, window=False)

    def test_serve_still_binds_every_interface(self) -> None:
        # The two commands exist precisely because their defaults differ; if
        # this ever matches `app`, one of them has lost its purpose.
        args = cli.build_parser().parse_args(["serve"])
        self.assertEqual(args.host, "0.0.0.0")


if __name__ == "__main__":
    unittest.main()
