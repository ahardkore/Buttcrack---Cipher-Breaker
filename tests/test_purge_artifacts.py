"""What the purge withdraws, and -- more to the point -- what it does not.

This script deletes things, so its selection rules are the whole of its safety:
which artifacts are candidates at all, which survive because they are the newest
of their version, which survive because somebody named them, and which were never
its business to begin with.  The deletion itself is not tested here; nothing in
this file touches the network.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


purge = _load("purge_artifacts")

BIG = 15_000_000


def artifact(artifact_id: int, name: str, created: str, size: int = BIG) -> dict:
    return {
        "id": artifact_id,
        "name": name,
        "created_at": f"{created}T05:00:00Z",
        "expires_at": "2026-11-12T05:00:00Z",
        "size_in_bytes": size,
    }


REPO = [
    artifact(10, "buttcrack-installer-1.2.1", "2026-10-13"),
    artifact(9, "buttcrack-installer-1.2.1", "2026-10-12"),
    artifact(8, "buttcrack-installer-1.2.1", "2026-10-11"),
    artifact(7, "buttcrack-installer-1.2.0", "2026-10-13"),
    artifact(6, "buttcrack-installer-1.2.0", "2026-10-12"),
    artifact(5, "buttcrack-installer-1.2.0", "2026-10-10"),
    artifact(4, "buttcrack-windows-latest", "2026-10-13"),
    artifact(3, "buttcrack-windows-latest", "2026-10-10"),
    artifact(2, "buttcrack-ubuntu-latest", "2026-10-13"),
    artifact(1, "github-pages", "2026-10-13"),
]


class Selection(unittest.TestCase):
    def test_the_newest_of_each_version_survives_by_default(self):
        doomed, spared, _ = purge.select(REPO)
        self.assertEqual({a["id"] for a in doomed}, {9, 8, 6, 5})
        self.assertEqual({a["id"] for a in spared}, {10, 7})

    def test_two_of_each_version_can_be_kept(self):
        doomed, spared, _ = purge.select(REPO, keep_newest=2)
        self.assertEqual({a["id"] for a in doomed}, {8, 5})
        self.assertEqual({a["id"] for a in spared}, {10, 9, 7, 6})

    def test_a_named_artifact_survives_however_old_it_is(self):
        doomed, spared, _ = purge.select(REPO, keep_ids={5})
        self.assertNotIn(5, {a["id"] for a in doomed})
        self.assertIn(5, {a["id"] for a in spared})

    def test_bundles_are_left_alone_unless_asked_for(self):
        doomed, _, ignored = purge.select(REPO)
        self.assertFalse({4, 3, 2} & {a["id"] for a in doomed})
        self.assertTrue({4, 3, 2} <= {a["id"] for a in ignored})

    def test_asking_for_bundles_still_keeps_the_newest_of_each_platform(self):
        doomed, spared, _ = purge.select(REPO, include_builds=True)
        self.assertEqual({4, 3, 2} & {a["id"] for a in doomed}, {3})
        self.assertTrue({4, 2} <= {a["id"] for a in spared})

    def test_the_site_deploy_is_never_a_candidate(self):
        for include_builds in (False, True):
            with self.subTest(include_builds=include_builds):
                doomed, _, ignored = purge.select(REPO, include_builds=include_builds)
                self.assertNotIn(1, {a["id"] for a in doomed})
                self.assertIn(1, {a["id"] for a in ignored})

    def test_an_empty_repository_selects_nothing(self):
        self.assertEqual(purge.select([]), ([], [], []))

    def test_versions_are_grouped_separately(self):
        # 1.2.0 and 1.2.1 are different products in different hands; keeping the
        # newest 1.2.1 must not withdraw the only 1.2.0 somebody is still selling.
        _, spared, _ = purge.select(REPO)
        self.assertEqual({a["name"] for a in spared}, {"buttcrack-installer-1.2.1", "buttcrack-installer-1.2.0"})


class Naming(unittest.TestCase):
    def test_installers_are_recognised_by_prefix(self):
        self.assertTrue(purge.is_installer(artifact(1, "buttcrack-installer-1.2.0", "2026-10-13")))
        self.assertFalse(purge.is_installer(artifact(1, "buttcrack-windows-latest", "2026-10-13")))

    def test_bundles_are_recognised_by_exact_name(self):
        self.assertTrue(purge.is_build(artifact(1, "buttcrack-windows-latest", "2026-10-13")))
        self.assertFalse(purge.is_build(artifact(1, "buttcrack-windows-latest-2", "2026-10-13")))

    def test_sizes_read_as_megabytes(self):
        self.assertEqual(purge.megabytes(15_500_000), "15.5 MB")


if __name__ == "__main__":
    unittest.main()
