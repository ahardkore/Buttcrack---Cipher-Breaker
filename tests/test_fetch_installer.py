"""The one command that answers "where is the installer".

The installer lives only as a CI artifact, and after the release workflow
started withdrawing an ordinary run's copy, the newest run is usually the one
with nothing to find.  ``scripts/fetch_installer.py`` exists so that question is
answered by asking which artifacts are live rather than by opening runs one at a
time -- and it is the only piece of the release tooling a person runs by hand
when something is already going wrong, which makes its failure messages part of
the feature.

These tests are offline: they exercise the selection, the formatting and the
error paths, and stand in a fake artifact list for the API.  Nothing here
downloads anything.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def _load():
    """Import the script by path: scripts/ is not a package."""
    spec = importlib.util.spec_from_file_location("fetch_installer", ROOT / "scripts" / "fetch_installer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch_installer = _load()


def _artifact(artifact_id: int, version: str, created: str, size: int = 15_558_568) -> dict:
    return {
        "id": artifact_id,
        "name": f"buttcrack-installer-{version}",
        "created_at": f"{created}T05:00:00Z",
        "expires_at": "2026-11-12T05:00:00Z",
        "size_in_bytes": size,
        "expired": False,
    }


LIVE = [
    _artifact(3, "1.2.1", "2026-10-13"),
    _artifact(2, "1.2.0", "2026-10-12"),
    _artifact(1, "1.2.0", "2026-10-11"),
]


class VersionNaming(unittest.TestCase):
    def test_version_comes_out_of_the_artifact_name(self):
        self.assertEqual(fetch_installer.version_of(_artifact(1, "1.2.0", "2026-10-12")), "1.2.0")


class Choosing(unittest.TestCase):
    def test_newest_wins_by_default(self):
        self.assertEqual(fetch_installer.choose(LIVE, None, None)["id"], 3)

    def test_a_version_picks_its_newest_build(self):
        # Two 1.2.0 artifacts: the list is newest-first, so the first match is
        # the newer build of that version.
        self.assertEqual(fetch_installer.choose(LIVE, "1.2.0", None)["id"], 2)

    def test_an_artifact_id_is_honoured_exactly(self):
        self.assertEqual(fetch_installer.choose(LIVE, None, 1)["id"], 1)

    def test_an_unknown_version_lists_what_is_live(self):
        with self.assertRaises(SystemExit) as caught:
            fetch_installer.choose(LIVE, "9.9.9", None)
        self.assertIn("1.2.0, 1.2.1", str(caught.exception))

    def test_an_unknown_id_says_so(self):
        with self.assertRaises(SystemExit) as caught:
            fetch_installer.choose(LIVE, None, 99)
        self.assertIn("--list", str(caught.exception))

    def test_nothing_live_asks_for_a_run_instead_of_failing_blankly(self):
        with self.assertRaises(SystemExit) as caught:
            fetch_installer.choose([], None, None)
        message = str(caught.exception)
        self.assertIn("gh workflow run 'Release artifacts'", message)

    def test_an_unknown_version_names_the_dispatch_that_produces_one(self):
        # The usual cause is not a typo in the version but a build that was never
        # kept: an ordinary push or pull-request run withdraws its own artifact,
        # so "no installer for 1.2.2" almost always means "nobody dispatched one".
        with self.assertRaises(SystemExit) as caught:
            fetch_installer.choose(LIVE, "9.9.9", None)
        message = str(caught.exception)
        self.assertIn("gh workflow run 'Release artifacts'", message)
        self.assertIn("withdraws its own artifact", message)


class PrintId(unittest.TestCase):
    """`--print-id` is how the publish workflow asks which artifact to fetch.

    It replaced a step that took the first row of the artifact list, which is the
    newest *live* build rather than the newest build -- the difference that let a
    stale 1.2.1 be published from a 1.2.2 checkout.
    """

    def _main(self, *args: str) -> tuple[int, str]:
        buffer = io.StringIO()
        with mock.patch.object(fetch_installer, "live_installers", return_value=LIVE), contextlib.redirect_stdout(
            buffer
        ):
            code = fetch_installer.main(list(args))
        return code, buffer.getvalue().strip()

    def test_it_prints_the_bare_id_of_the_version_asked_for(self):
        code, printed = self._main("--version", "1.2.0", "--print-id")
        self.assertEqual(code, 0)
        self.assertEqual(printed, "2", "the workflow reads this straight into a variable")

    def test_without_a_version_it_still_picks_the_newest_live(self):
        self.assertEqual(self._main("--print-id"), (0, "3"))

    def test_an_explicit_id_is_passed_through(self):
        self.assertEqual(self._main("--artifact", "1", "--print-id"), (0, "1"))

    def test_it_downloads_nothing(self):
        with mock.patch.object(fetch_installer, "live_installers", return_value=LIVE), mock.patch.object(
            fetch_installer, "download"
        ) as download, contextlib.redirect_stdout(io.StringIO()):
            fetch_installer.main(["--version", "1.2.1", "--print-id"])
        download.assert_not_called()

    def test_a_version_nobody_built_fails_rather_than_substituting(self):
        with mock.patch.object(fetch_installer, "live_installers", return_value=LIVE), contextlib.redirect_stdout(
            io.StringIO()
        ), self.assertRaises(SystemExit):
            fetch_installer.main(["--version", "9.9.9", "--print-id"])


class Formatting(unittest.TestCase):
    def test_sizes_read_the_way_the_download_page_writes_them(self):
        self.assertEqual(fetch_installer.human_megabytes(15_558_568), "15.6 MB")
        self.assertEqual(fetch_installer.human_megabytes(0), "0.0 MB")


if __name__ == "__main__":
    unittest.main()
