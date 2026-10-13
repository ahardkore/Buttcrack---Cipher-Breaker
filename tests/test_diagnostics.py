"""``buttcrack doctor`` and the block the desktop window copies.

Everything here is about the *answer being usable*: a diagnostics block that
names the wrong directory, or says "writable" when it is not, sends a support
conversation the wrong way for a day.  So the checks below are about the values,
not the formatting.
"""

from __future__ import annotations

import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from buttcrack import __version__, diagnostics, userdata


def field(lines: list[str], label: str) -> str:
    """The value of one ``label   value`` row."""
    for line in lines:
        if line.startswith(label):
            return line[len(label) :].strip()
    raise AssertionError(f"no {label!r} row in:\n" + "\n".join(lines))


class ScratchDataDir:
    def setUp(self) -> None:
        self.base = tempfile.TemporaryDirectory()
        self.addCleanup(self.base.cleanup)
        env = mock.patch.dict(os.environ, {userdata.ENV_DATA_DIR: self.base.name})
        env.start()
        self.addCleanup(env.stop)


class ReportTests(ScratchDataDir, unittest.TestCase):
    def test_it_names_the_version_and_the_build(self) -> None:
        lines, problems = diagnostics.report_lines()
        self.assertFalse(problems, lines)
        self.assertEqual(field(lines, "buttcrack"), __version__)
        # From a checkout, not a frozen build -- and it says which.
        self.assertIn("source checkout", field(lines, "build"))

    def test_the_data_directory_is_read_back_from_the_environment(self) -> None:
        lines, _problems = diagnostics.report_lines()
        self.assertIn(self.base.name, field(lines, "data directory"))
        self.assertIn("writable", field(lines, "data directory"))

    def test_a_log_that_does_not_exist_yet_says_so(self) -> None:
        lines, _problems = diagnostics.report_lines()
        self.assertIn("not created yet", field(lines, "log file"))

    def test_a_log_that_exists_reports_its_size(self) -> None:
        log = diagnostics.userdata.data_dir() / "logs" / "buttcrack.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("x" * 2048, encoding="utf-8")
        lines, _problems = diagnostics.report_lines()
        self.assertIn("2.0 KB", field(lines, "log file"))

    def test_a_busy_preferred_port_is_reported_rather_than_hidden(self) -> None:
        # The port the app would like is a property of the run, not of the
        # machine: another test in the same process may already be serving
        # 8080, so the check holds the port it is asking about.
        from buttcrack import desktop

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as taken:
            taken.bind((desktop.LOCAL_HOST, 0))
            taken.listen(1)
            port = taken.getsockname()[1]
            with mock.patch.object(desktop, "PREFERRED_PORT", port):
                lines, problems = diagnostics.report_lines()
        address = field(lines, "address")
        self.assertFalse(problems, lines)
        self.assertIn(f"{port} is busy", address)
        self.assertIn("free", address)

    def test_the_model_is_loaded_rather_than_assumed(self) -> None:
        lines, problems = diagnostics.report_lines()
        self.assertFalse(problems, lines)
        self.assertIn("quadgrams", field(lines, "language model"))
        self.assertIn("languages", field(lines, "language model"))

    def test_the_window_adds_what_only_it_knows(self) -> None:
        lines, _problems = diagnostics.report_lines(port=53412, tray=True, last_job="solved: caesar")
        self.assertIn("53412", field(lines, "address"))
        self.assertEqual(field(lines, "tray icon"), "active")
        self.assertEqual(field(lines, "last search"), "solved: caesar")

    def test_an_override_of_the_data_directory_is_called_out(self) -> None:
        # Otherwise the block names a directory that the next double-click will
        # not use, and the answer is worse than no answer.
        lines, _problems = diagnostics.report_lines()
        self.assertIn(userdata.ENV_DATA_DIR, " ".join(lines))

    def test_a_read_only_data_directory_is_a_problem_not_a_crash(self) -> None:
        with mock.patch.object(userdata, "data_dir", return_value=Path("/proc/nope/buttcrack")):
            lines, problems = diagnostics.report_lines()
            text = diagnostics.report_text()
        self.assertTrue(problems, lines)
        self.assertIn("NOT WRITABLE", field(lines, "data directory"))
        self.assertIn("problems:", text)

    def test_a_model_that_will_not_load_is_reported(self) -> None:
        with mock.patch.object(diagnostics, "_model_row", return_value=("FAILED TO LOAD: boom", False)):
            lines, problems = diagnostics.report_lines()
        self.assertTrue(problems, lines)
        self.assertIn("FAILED TO LOAD", field(lines, "language model"))

    def test_the_text_ends_with_a_verdict(self) -> None:
        self.assertIn("no problems found.", diagnostics.report_text())


class DoctorCommandTests(ScratchDataDir, unittest.TestCase):
    def test_doctor_is_a_real_subcommand(self) -> None:
        from buttcrack import cli

        self.assertIn("doctor", cli.SUBCOMMANDS)

    def test_the_command_prints_the_block_and_succeeds(self) -> None:
        import contextlib
        import io

        from buttcrack import cli

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["doctor"])
        printed = out.getvalue()
        self.assertEqual(code, 0, printed)
        self.assertIn(__version__, printed)
        self.assertIn("no problems found.", printed)

    def test_the_command_fails_when_the_install_is_broken(self) -> None:
        import contextlib
        import io

        from buttcrack import cli

        out = io.StringIO()
        broken = mock.patch.object(userdata, "data_dir", return_value=Path("/proc/nope/buttcrack"))
        with broken, contextlib.redirect_stdout(out):
            code = cli.main(["doctor"])
        self.assertEqual(code, 1)
        self.assertIn("problems found", out.getvalue())
