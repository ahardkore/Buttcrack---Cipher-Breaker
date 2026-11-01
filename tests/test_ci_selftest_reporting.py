"""Exercise the CI self-test failure handler under GitHub's bash flags."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "requires POSIX bash")
class SelftestReportingTests(unittest.TestCase):
    def run_step(self, exit_code):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        section = workflow.split("      - name: Self-test (quick)\n", 1)[1]
        script = textwrap.dedent(section.split("        run: |\n", 1)[1].split("\n      - name:", 1)[0])
        with tempfile.TemporaryDirectory() as directory:
            # Stub only the outer timeout command: no cipher searches are run.
            timeout = Path(directory) / "timeout"
            timeout.write_text(f"#!/bin/sh\nprintf 'starting synthetic self-test check\\n'\nexit {exit_code}\n", encoding="utf-8")
            timeout.chmod(0o700)
            env = dict(os.environ, PATH=directory + os.pathsep + os.environ.get("PATH", ""))
            return subprocess.run([shutil.which("bash"), "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", script],
                                  cwd=directory, env=env, capture_output=True, text=True, timeout=10)

    def test_timeout_preserves_exit_code_and_emits_diagnostic_tail(self):
        result = self.run_step(124)
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertIn("::error title=self-test (quick) failed with exit 124::", result.stdout)
        self.assertIn("::notice::starting synthetic self-test check", result.stdout)

    def test_success_is_not_reported_as_failure(self):
        result = self.run_step(0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("starting synthetic self-test check", result.stdout)
        self.assertNotIn("::error", result.stdout)


if __name__ == "__main__":
    unittest.main()
