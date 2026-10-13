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
import os
import socket
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from buttcrack import cli, desktop, userdata
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


class ScratchDataDirMixin:
    """A data directory of one's own, and a log sink closed after the test.

    The tests below exercise the sink a windowed build writes to, so they need
    somewhere harmless for it to write: without this, running the suite would
    append to the log of the person running it.
    """

    def setUp(self) -> None:
        self.base = tempfile.TemporaryDirectory()
        self.addCleanup(self.base.cleanup)
        env = mock.patch.dict(os.environ, {userdata.ENV_DATA_DIR: self.base.name})
        env.start()
        self.addCleanup(env.stop)
        stream = mock.patch.object(desktop, "_LOG_STREAM", None)
        stream.start()
        self.addCleanup(stream.stop)
        # Reverse order: the open handle is closed before the patch that owns
        # the global is undone, so no test leaves a file descriptor behind.
        self.addCleanup(self._close_log)

    @staticmethod
    def _close_log() -> None:
        handle = desktop._LOG_STREAM
        if handle is not None and not handle.closed:
            handle.close()


class FrozenBuildTests(ScratchDataDirMixin, unittest.TestCase):
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
        self.assertIn("nor this", desktop.log_path().read_text(encoding="utf-8"))

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
        self.assertFalse(args.force)

    def test_app_forwards_its_flags(self) -> None:
        with mock.patch("buttcrack.desktop.run", return_value=0) as run:
            cli.main(["app", "--console", "--no-browser", "--port", "9123"])
        # An explicit port is a request for a server of one's own, so the
        # second-launch handover does not apply.
        run.assert_called_once_with(port=9123, open_browser=False, window=False, reuse=False)

    def test_a_bare_app_call_hands_over_to_a_copy_that_is_running(self) -> None:
        with mock.patch("buttcrack.desktop.run", return_value=0) as run:
            cli.main(["app"])
        run.assert_called_once_with(port=0, open_browser=True, window=None, reuse=True)

    def test_force_starts_a_second_copy_on_purpose(self) -> None:
        with mock.patch("buttcrack.desktop.run", return_value=0) as run:
            cli.main(["app", "--force"])
        run.assert_called_once_with(port=0, open_browser=True, window=None, reuse=False)

    def test_serve_still_binds_every_interface(self) -> None:
        # The two commands exist precisely because their defaults differ; if
        # this ever matches `app`, one of them has lost its purpose.
        args = cli.build_parser().parse_args(["serve"])
        self.assertEqual(args.host, "0.0.0.0")


class LogFileTests(ScratchDataDirMixin, unittest.TestCase):
    """What a windowed build keeps after the window is gone.

    A GUI build has no console, so this file is the only record of a worker that
    died or a startup that failed -- which makes "it silently discards" a bug
    with a support cost, not a cosmetic one.
    """

    def test_the_sink_writes_to_a_file_in_the_data_directory(self) -> None:
        stream = desktop._NullStream()
        stream.write("buttcrack: a worker died\n")
        self.assertIn("a worker died", desktop.log_path().read_text(encoding="utf-8"))

    def test_writing_still_reports_a_length(self) -> None:
        stream = desktop._NullStream()
        self.assertEqual(stream.write("abc"), 3)
        self.assertEqual(stream.write(""), 0)

    def test_the_log_rotates_instead_of_growing_without_bound(self) -> None:
        stream = desktop._NullStream()
        stream.write("x" * (desktop.LOG_MAX_BYTES - 1))
        stream.write("first\n")  # takes it over the cap
        stream.write("second\n")  # this one rotates first
        self.assertIn("second", desktop.log_path().read_text(encoding="utf-8"))
        rotated = desktop.log_path().parent / f"{desktop.LOG_NAME}.1"
        self.assertTrue(rotated.is_file(), "the previous log was not kept")
        self.assertIn("first", rotated.read_text(encoding="utf-8"))

    def test_a_log_that_cannot_be_written_is_not_fatal(self) -> None:
        # A read-only or missing data directory costs the log, never the app.
        broken = Path(self.base.name) / "not-a-directory" / desktop.LOG_NAME
        (Path(self.base.name) / "not-a-directory").write_text("a file, not a directory", encoding="utf-8")
        with mock.patch.object(desktop, "log_path", return_value=broken):
            self.assertEqual(desktop._NullStream().write("still here\n"), 11)


class SingleInstanceTests(unittest.TestCase):
    """Two launches used to mean two servers, two tray icons and two ledgers."""

    def setUp(self) -> None:
        self.base = tempfile.TemporaryDirectory()
        self.addCleanup(self.base.cleanup)
        env = mock.patch.dict(os.environ, {userdata.ENV_DATA_DIR: self.base.name})
        env.start()
        self.addCleanup(env.stop)

    def test_the_first_claim_wins_and_the_second_is_told_so(self) -> None:
        first = desktop.RunningInstance()
        second = desktop.RunningInstance()
        self.assertTrue(first.claim())
        self.assertFalse(second.claim())
        first.release()
        self.assertTrue(second.claim(), "the lock outlived the process that held it")
        second.release()

    def test_a_running_app_publishes_the_url_it_is_serving(self) -> None:
        app = desktop.LocalApp(port=0)
        app.start()
        try:
            self.assertEqual(desktop.running_instance(), app.url)
        finally:
            app.stop()
        self.assertIsNone(desktop.running_instance(), "the marker outlived the app")

    def test_a_stale_marker_does_not_stop_the_next_launch(self) -> None:
        # Written by a copy that crashed: nothing is listening on that port.
        userdata.instance_file().write_text(
            json.dumps({"pid": 1, "port": 9, "url": "http://127.0.0.1:9/"}), encoding="utf-8"
        )
        self.assertIsNone(desktop.running_instance())

    def test_garbage_in_the_marker_is_not_a_crash(self) -> None:
        userdata.instance_file().write_text("{not json", encoding="utf-8")
        self.assertIsNone(desktop.running_instance())

    @mock.patch.object(desktop, "LocalApp")
    @mock.patch("webbrowser.open")
    @mock.patch.object(desktop, "running_instance")
    def test_a_second_launch_opens_the_running_copy_and_starts_nothing(self, probe, opened, app) -> None:
        url = "http://127.0.0.1:8123/"
        probe.return_value = url
        self.assertEqual(desktop.run(reuse=True), 0)
        probe.assert_called_once()
        opened.assert_called_once_with(url)
        app.assert_not_called()

    @mock.patch.object(desktop, "save_state")
    @mock.patch.object(desktop, "run_window", return_value=True)
    @mock.patch.object(desktop, "LocalApp")
    @mock.patch.object(desktop, "running_instance")
    def test_the_handover_is_not_consulted_unless_asked_for(self, probe, app, _window, _state) -> None:
        desktop.run(open_browser=False)
        probe.assert_not_called()
        app.assert_called_once()

    @mock.patch.object(desktop, "save_state")
    @mock.patch.object(desktop, "run_window", return_value=True)
    @mock.patch.object(desktop, "LocalApp")
    def test_the_port_that_worked_is_the_one_remembered(self, app, _window, state) -> None:
        # The desktop app remembers where it served so the bookmark keeps
        # working; a LocalApp built by a library user does not write anything.
        app.return_value.port = 53412
        desktop.run(open_browser=False)
        state.assert_called_once_with(port=53412)


class RememberedStateTests(unittest.TestCase):
    """The small file that makes the second launch feel like the first."""

    def setUp(self) -> None:
        self.base = tempfile.TemporaryDirectory()
        self.addCleanup(self.base.cleanup)
        env = mock.patch.dict(os.environ, {userdata.ENV_DATA_DIR: self.base.name})
        env.start()
        self.addCleanup(env.stop)

    def test_state_round_trips(self) -> None:
        desktop.save_state(port=53412, windows={"main": "430x520+100+80"})
        self.assertEqual(desktop.remembered_port(), 53412)
        self.assertEqual(desktop.load_state()["windows"], {"main": "430x520+100+80"})

    def test_saving_keeps_what_was_there(self) -> None:
        desktop.save_state(windows={"main": "430x520+100+80"})
        desktop.save_state(port=53412)
        self.assertEqual(desktop.load_state()["windows"], {"main": "430x520+100+80"})

    def test_a_corrupt_or_missing_file_is_not_an_error(self) -> None:
        self.assertEqual(desktop.load_state(), {})
        self.assertEqual(desktop.remembered_port(), 0)
        desktop.state_path().write_text("{not json", encoding="utf-8")
        self.assertEqual(desktop.load_state(), {})
        desktop.state_path().write_text('["a list"]', encoding="utf-8")
        self.assertEqual(desktop.load_state(), {})

    def test_only_a_plausible_port_is_remembered(self) -> None:
        for stored in (0, -1, 70000, "8080", None, 8080.5):
            desktop.state_path().write_text(json.dumps({"port": stored}), encoding="utf-8")
            self.assertEqual(desktop.remembered_port(), 0, stored)

    def test_a_withdrawn_windows_geometry_is_not_restored(self) -> None:
        self.assertFalse(desktop.usable_geometry("1x1+0+0"))
        self.assertFalse(desktop.usable_geometry(""))
        self.assertTrue(desktop.usable_geometry("430x520+100+80"))
        self.assertTrue(desktop.usable_geometry("430x520-10-20"))

    def test_a_busy_familiar_port_falls_through_to_anything_free(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen(1)
            taken = busy.getsockname()[1]
            chosen = desktop.desktop_port(preferred=taken)
        self.assertGreater(chosen, 0)
        self.assertNotEqual(chosen, taken)

    def test_the_remembered_port_beats_a_random_one(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as free_socket:
            free_socket.bind(("127.0.0.1", 0))
            remembered = free_socket.getsockname()[1]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen(1)
            taken = busy.getsockname()[1]
            desktop.save_state(port=remembered)
            self.assertEqual(desktop.desktop_port(preferred=taken), remembered)

    def test_the_dpi_call_declines_off_windows(self) -> None:
        if sys.platform == "win32":  # pragma: no cover - not where CI runs
            self.skipTest("this is the Windows path")
        self.assertFalse(desktop.enable_dpi_awareness())

    def test_the_data_folder_is_created_before_it_is_opened(self) -> None:
        # Whether the file manager actually starts is the desktop's business;
        # that the directory exists when it is asked for is ours.
        with mock.patch.object(desktop, "open_path", return_value=True) as opened:
            self.assertTrue(desktop.open_data_folder())
        self.assertTrue(userdata.data_dir().is_dir())
        opened.assert_called_once_with(userdata.data_dir())

    def test_a_tray_that_is_not_running_cannot_notify(self) -> None:
        tray = TrayIcon("Buttcrack")
        self.assertFalse(tray.notify("title", "message"))


if __name__ == "__main__":
    unittest.main()
