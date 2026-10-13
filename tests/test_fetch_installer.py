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

import importlib.util
import unittest
from pathlib import Path

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


class Formatting(unittest.TestCase):
    def test_sizes_read_the_way_the_download_page_writes_them(self):
        self.assertEqual(fetch_installer.human_megabytes(15_558_568), "15.6 MB")
        self.assertEqual(fetch_installer.human_megabytes(0), "0.0 MB")


if __name__ == "__main__":
    unittest.main()
