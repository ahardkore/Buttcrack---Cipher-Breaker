"""Where the program keeps its own state, and why it is not a relative path.

The desktop window is the only part of the package that chooses a location for
itself, and it used to choose two that do not exist once the program is
installed rather than run from a checkout: ``kryptos/pk9-results.sqlite3`` and
``~/buttcrack-assistant.jsonl``.  The first is the one that hurt -- SQLite will
not create a missing parent directory, so opening that panel in the installed
app produced "Campaign ledger unavailable: unable to open database file" and no
amount of clicking would change it.

These tests pin the resolution rules down, and the important one reproduces the
installed situation exactly: no checkout next to the code, and a working
directory that belongs to whoever launched the process.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from buttcrack import userdata
from buttcrack.results_db import ResultDB


class DataDirectoryTests(unittest.TestCase):
    def test_the_override_is_honoured_and_the_directory_is_created(self):
        with tempfile.TemporaryDirectory() as base:
            target = Path(base) / "deep" / "nested" / "buttcrack"
            self.assertFalse(target.exists())
            with mock.patch.dict(os.environ, {userdata.ENV_DATA_DIR: str(target)}):
                self.assertEqual(userdata.data_dir(), target)
            # Created, not merely named: SQLite will not make a parent directory
            # for itself, so handing back a path that cannot be written to is
            # the same bug in a different costume.
            self.assertTrue(target.is_dir())

    def test_asking_without_creating_leaves_the_filesystem_alone(self):
        with tempfile.TemporaryDirectory() as base:
            target = Path(base) / "not-yet"
            with mock.patch.dict(os.environ, {userdata.ENV_DATA_DIR: str(target)}):
                self.assertEqual(userdata.data_dir(create=False), target)
            self.assertFalse(target.exists())

    def test_the_windows_default_is_the_local_app_data_directory(self):
        # The branch that matters most, exercised on whatever platform is
        # running the suite.  %LOCALAPPDATA% is per-user, writable without
        # administrator rights, and outside anything an uninstall or an upgrade
        # would touch -- all three of which the paths this module replaced were
        # not.
        with (
            tempfile.TemporaryDirectory() as fake_local,
            mock.patch.dict(os.environ, {"LOCALAPPDATA": fake_local}, clear=True),
            mock.patch.object(userdata.sys, "platform", "win32"),
        ):
            self.assertEqual(userdata._default_data_dir(), Path(fake_local) / "Buttcrack")

    def test_the_posix_default_is_the_xdg_data_directory(self):
        with (
            mock.patch.dict(os.environ, {"XDG_DATA_HOME": "/home/somebody/.local/share"}, clear=True),
            mock.patch.object(userdata.sys, "platform", "linux"),
        ):
            self.assertEqual(userdata._default_data_dir(), Path("/home/somebody/.local/share/buttcrack"))

    def test_the_default_never_lands_beside_the_program_or_the_working_directory(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            resolved = userdata._default_data_dir()
        self.assertTrue(resolved.is_absolute())
        # Not under the package: an upgrade replaces that directory, and an
        # uninstall deletes it.
        self.assertFalse(resolved.is_relative_to(Path(userdata.__file__).resolve().parent))
        # And not the current directory either, which in an installed copy
        # belongs to whatever launched the process.
        self.assertNotEqual(resolved.resolve(), Path.cwd().resolve())

    def test_the_assistant_log_lives_in_the_data_directory(self):
        with tempfile.TemporaryDirectory() as base, mock.patch.dict(os.environ, {userdata.ENV_DATA_DIR: base}):
            log = userdata.assistant_log()
        self.assertEqual(log.parent, Path(base))
        # It used to be Path.home() / "buttcrack-assistant.jsonl", which scatters
        # a stray file across the top of the user's home directory.
        self.assertNotEqual(log.parent, Path.home())
        self.assertEqual(log.suffix, ".jsonl")


class CheckoutDetectionTests(unittest.TestCase):
    def test_this_repository_is_recognised_as_a_checkout(self):
        self.assertEqual(userdata._checkout_root(), Path(__file__).resolve().parents[1])

    def test_detection_does_not_depend_on_the_working_directory(self):
        # The point of judging this from the package's own location: an
        # installed copy must not be able to mistake wherever it was launched
        # from for a checkout.
        with tempfile.TemporaryDirectory() as elsewhere:
            previous = os.getcwd()
            os.chdir(elsewhere)
            try:
                self.assertEqual(userdata._checkout_root(), Path(__file__).resolve().parents[1])
            finally:
                os.chdir(previous)


class LedgerResolutionTests(unittest.TestCase):
    def test_the_override_wins(self):
        with tempfile.TemporaryDirectory() as base:
            chosen = Path(base) / "somewhere-else" / "ledger.sqlite3"
            with mock.patch.dict(os.environ, {userdata.ENV_LEDGER: str(chosen)}):
                self.assertEqual(userdata.pk9_ledger(), chosen)
            self.assertTrue(chosen.parent.is_dir())

    def test_a_checkout_with_a_ledger_keeps_using_it(self):
        # Running from source should see the same ledger the tooling in
        # scripts/ writes, which is the workflow this path exists for.
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            (root / "buttcrack").mkdir()
            (root / "kryptos").mkdir()
            existing = root / "kryptos" / "pk9-results.sqlite3"
            existing.write_bytes(b"")
            with (
                mock.patch.object(userdata, "_checkout_root", return_value=root),
                mock.patch.dict(os.environ, {userdata.ENV_DATA_DIR: str(root / "data")}),
            ):
                self.assertEqual(userdata.pk9_ledger(), existing)

    def test_a_checkout_without_a_ledger_falls_back_to_the_data_directory(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            (root / "buttcrack").mkdir()
            (root / "kryptos").mkdir()
            with (
                mock.patch.object(userdata, "_checkout_root", return_value=root),
                mock.patch.dict(os.environ, {userdata.ENV_DATA_DIR: str(root / "data")}),
            ):
                self.assertEqual(userdata.pk9_ledger(), root / "data" / "pk9-results.sqlite3")

    def test_an_installed_copy_uses_the_data_directory(self):
        with (
            tempfile.TemporaryDirectory() as base,
            mock.patch.object(userdata, "_checkout_root", return_value=None),
            mock.patch.dict(os.environ, {userdata.ENV_DATA_DIR: base}),
        ):
            self.assertEqual(userdata.pk9_ledger(), Path(base) / "pk9-results.sqlite3")


class InstalledApplicationTests(unittest.TestCase):
    """The situation the old relative paths could not survive."""

    def test_the_campaign_ledger_opens_from_an_unrelated_working_directory(self):
        with tempfile.TemporaryDirectory() as launch_dir, tempfile.TemporaryDirectory() as data_root:
            previous = os.getcwd()
            os.chdir(launch_dir)
            try:
                with (
                    mock.patch.object(userdata, "_checkout_root", return_value=None),
                    mock.patch.dict(os.environ, {userdata.ENV_DATA_DIR: data_root}),
                ):
                    ledger = userdata.pk9_ledger()
                    # This is what the campaign panel does, and what used to
                    # raise sqlite3.OperationalError: unable to open database
                    # file inside the shipped application.
                    db = ResultDB(ledger)
                    self.assertEqual(db.recent(10), [])
            finally:
                os.chdir(previous)

            self.assertTrue(ledger.is_file(), "the ledger was never created")
            self.assertEqual(ledger.parent, Path(data_root))
            # And it did not scatter a kryptos/ directory into whatever
            # directory the shortcut happened to leave the process in.
            self.assertFalse((Path(launch_dir) / "kryptos").exists())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
