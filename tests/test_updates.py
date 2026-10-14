"""Update checks stay opt-in, bounded, offline-testable and separate from solving."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from buttcrack import desktop, updates
from scripts import build_site


class VersionTests(unittest.TestCase):
    def test_numeric_order(self):
        self.assertGreater(updates.version_parts("1.10.0"), updates.version_parts("1.9.9"))
        self.assertGreater(updates.version_parts("2.0.0"), updates.version_parts("1.99.99"))

    def test_rejects_invalid_versions(self):
        for version in (None, 123, "", "1.2", "v1.2.3", "1.2.3rc1", "1.2.3.4", "-1.2.3", "1.2.3\n"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                updates.version_parts(version)


class CheckTests(unittest.TestCase):
    def fetch(self, raw, current="1.2.1"):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = raw
        with mock.patch.object(updates.urllib.request, "build_opener") as factory:
            factory.return_value.open.return_value = response
            result = updates.check_for_updates(current)
            request = factory.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, updates.MANIFEST_URL)
            self.assertEqual(request.get_method(), "GET")
            self.assertIsNone(request.data)
            self.assertEqual(factory.return_value.open.call_args.kwargs["timeout"], updates.TIMEOUT)
            response.__enter__.return_value.read.assert_called_once_with(updates.MAX_MANIFEST_BYTES + 1)
            return result

    def test_newer_equal_and_older(self):
        for version, newer in (("1.10.0", True), ("1.2.1", False), ("1.2.0", False)):
            with self.subTest(version=version):
                self.assertEqual(self.fetch(json.dumps({"version": version}).encode()), updates.UpdateResult(version, newer))

    def test_invalid_payloads(self):
        for raw in (b"not json", b"[]", b"null", b"{}", b'{"version": null}', b'{"version": "1.2"}', b"\xff", b"x" * 4097):
            with self.subTest(raw=raw[:40]), self.assertRaises(updates.UpdateError):
                self.fetch(raw)

    def test_published_improvements_are_loaded(self):
        result = self.fetch(json.dumps({
            "version": "2.0.0",
            "release_notes": ["Added a new cipher.", "Improved solver accuracy.", "Fixed a startup issue."],
        }).encode())
        self.assertEqual(result.release_notes, (
            "Added a new cipher.", "Improved solver accuracy.", "Fixed a startup issue.",
        ))

    def test_bad_notes_are_rejected(self):
        for notes in (None, "not a list", [42], [""], [" "], ["x" * 181], ["note"] * 9, ["two\nlines"], ["control\x00character"]):
            with self.subTest(notes=notes), self.assertRaises(updates.UpdateError):
                self.fetch(json.dumps({"version": "2.0.0", "release_notes": notes}).encode())

    def test_remote_urls_are_ignored(self):
        result = self.fetch(b'{"version": "2.0.0", "url": "http://evil.example/installer.exe"}')
        self.assertTrue(result.newer)
        self.assertEqual(updates.UPDATES_URL, "https://ciphersolverpro.com/windows-app.html#updates")

    def test_network_failures(self):
        for error in (TimeoutError(), urllib.error.URLError("offline"), urllib.error.HTTPError(updates.MANIFEST_URL, 404, "missing", {}, None)):
            with self.subTest(error=error), mock.patch.object(updates.urllib.request, "build_opener") as factory:
                factory.return_value.open.side_effect = error
                with self.assertRaisesRegex(updates.UpdateError, "connection"):
                    updates.check_for_updates()

    def test_redirects_are_refused(self):
        with self.assertRaises(updates.UpdateError):
            updates._NoRedirect().redirect_request(None, None, 302, "", {}, "http://evil.example/")


class DialogTextTests(unittest.TestCase):
    def test_dialog_lists_improvements_before_the_update_choice(self):
        result = updates.UpdateResult("2.0.0", True, ("Added a new cipher.", "Improved accuracy."))
        text = updates.update_dialog_text(result, "1.2.2")
        self.assertIn("You have 1.2.2", text)
        self.assertIn("What's new in 2.0.0:", text)
        self.assertIn("• Added a new cipher.", text)
        self.assertIn("• Improved accuracy.", text)
        self.assertLess(text.index("Improved accuracy."), text.index("Open update information?"))
        self.assertIn("nothing is installed automatically", text)

    def test_old_manifest_has_an_honest_fallback(self):
        text = updates.update_dialog_text(updates.UpdateResult("2.0.0", True))
        self.assertIn("Release notes were not provided", text)


class WorkerTests(unittest.TestCase):
    def test_opt_in_duplicate_guard_and_retry(self):
        entered, release = threading.Event(), threading.Event()
        result = updates.UpdateResult("2.0.0", True)

        def check():
            entered.set()
            release.wait(2)
            return result

        with mock.patch.object(updates, "check_for_updates", side_effect=check) as fetch:
            checker = updates.UpdateChecker()
            fetch.assert_not_called()
            self.assertIsNone(checker.poll())
            self.assertTrue(checker.start())
            self.assertTrue(entered.wait(2))
            self.assertFalse(checker.start())
            self.assertIsNone(checker.poll())
            release.set()
            # Blocking queue access in the test only: the GUI uses poll().
            finished = checker._results.get(timeout=2)
            checker._results.put(finished)
            self.assertEqual(checker.poll(), result)
            self.assertFalse(checker.busy)
            self.assertTrue(checker.start())
            self.assertEqual(checker._results.get(timeout=2), result)

    def test_worker_errors_are_delivered(self):
        with mock.patch.object(updates, "check_for_updates", side_effect=updates.UpdateError("offline")):
            checker = updates.UpdateChecker()
            checker.start()
            result = checker._results.get(timeout=2)
            checker._results.put(result)
            self.assertIsInstance(checker.poll(), updates.UpdateError)
            self.assertFalse(checker.busy)


class ManifestTests(unittest.TestCase):
    def test_only_published_version_is_exposed(self):
        config = {"windows_app": {"version": "1.2.1", "delivery_url": "https://private.example/paid.exe"}}
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(build_site, "site_config", return_value=config):
            build_site.write_desktop_version(Path(directory))
            manifest = json.loads((Path(directory) / "desktop-version.json").read_text())
            self.assertEqual(manifest, {"version": "1.2.1", "release_notes": []})

    def test_only_notes_for_the_published_installer_are_exposed(self):
        config = {
            "windows_app": {"version": "1.2.1", "delivery_url": "https://private.example/paid.exe"},
            "desktop_release_notes": {
                "1.2.1": ["Fixed startup."],
                "1.2.2": ["Unreleased feature — do not announce."],
            },
        }
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(build_site, "site_config", return_value=config):
            build_site.write_desktop_version(Path(directory))
            manifest = json.loads((Path(directory) / "desktop-version.json").read_text())
            self.assertEqual(manifest, {"version": "1.2.1", "release_notes": ["Fixed startup."]})

    def test_oversize_or_invalid_notes_fail_build(self):
        for notes in ([""], "not a list", ["😀" * 180] * 8):
            config = {"windows_app": {"version": "1.2.1"}, "desktop_release_notes": {"1.2.1": notes}}
            with self.subTest(notes=str(notes)[:20]), tempfile.TemporaryDirectory() as directory, mock.patch.object(build_site, "site_config", return_value=config), self.assertRaises(SystemExit):
                build_site.write_desktop_version(Path(directory))

    def test_invalid_published_version_fails_build(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(build_site, "site_config", return_value={}), self.assertRaises(SystemExit):
            build_site.write_desktop_version(Path(directory))


class WindowTests(unittest.TestCase):
    """Exercise GUI callbacks with fake widgets; no display or network required."""

    def run_check(self, result, accept=False):
        tk, ttk, messagebox = mock.MagicMock(), mock.MagicMock(), mock.MagicMock()
        tk.ttk = ttk
        tk.messagebox = messagebox
        root = tk.Tk.return_value
        buttons = {}

        def button(*args, **kwargs):
            widget = mock.MagicMock()
            buttons[kwargs["text"]] = (widget, kwargs["command"])
            return widget

        ttk.Button.side_effect = button
        checker = mock.MagicMock()
        checker.start.return_value = True
        checker.poll.return_value = result
        messagebox.askyesno.return_value = accept

        def mainloop():
            checker.start.assert_not_called()
            buttons["Check for updates"][1]()
            buttons["Check for updates"][0].configure.assert_called_with(state="disabled")
            # Run the scheduled main-thread tick, which receives the worker result.
            root.after.call_args.args[1]()
            buttons["Check for updates"][0].configure.assert_called_with(state="normal")

        root.mainloop.side_effect = mainloop
        modules = {"tkinter": tk, "tkinter.ttk": ttk, "tkinter.messagebox": messagebox}
        with mock.patch.dict("sys.modules", modules), mock.patch.object(updates, "UpdateChecker", return_value=checker), mock.patch.object(desktop, "load_state", return_value={}), mock.patch.object(desktop, "summary_lines", return_value=["version"]), mock.patch("buttcrack._wintray.TrayIcon") as tray, mock.patch.object(desktop.webbrowser, "open", return_value=True) as browser:
            self.assertTrue(desktop.run_window(mock.MagicMock()))
        return messagebox, tray.return_value, browser, buttons

    def test_available_update_notifies_without_opening_browser(self):
        messagebox, tray, browser, buttons = self.run_check(updates.UpdateResult("2.0.0", True))
        tray.notify.assert_called_once()
        messagebox.askyesno.assert_called_once()
        browser.assert_not_called()
        buttons["Update information"][0].grid.assert_called()

    def test_popup_shows_release_improvements(self):
        result = updates.UpdateResult("2.0.0", True, ("New cipher support.", "Faster solving."))
        messagebox, _, browser, _ = self.run_check(result)
        message = messagebox.askyesno.call_args.args[1]
        self.assertIn("What's new in 2.0.0:", message)
        self.assertIn("• New cipher support.", message)
        self.assertIn("• Faster solving.", message)
        browser.assert_not_called()

    def test_update_page_opens_only_with_consent(self):
        _, _, browser, _ = self.run_check(updates.UpdateResult("2.0.0", True), accept=True)
        browser.assert_called_once_with(updates.UPDATES_URL)

    def test_current_version(self):
        messagebox, tray, browser, _ = self.run_check(updates.UpdateResult("1.0.0", False))
        messagebox.showinfo.assert_called_once()
        tray.notify.assert_not_called()
        browser.assert_not_called()

    def test_failure_is_recoverable(self):
        messagebox, tray, browser, _ = self.run_check(updates.UpdateError("offline"))
        messagebox.showwarning.assert_called_once()
        tray.notify.assert_not_called()
        browser.assert_not_called()


if __name__ == "__main__":
    unittest.main()
