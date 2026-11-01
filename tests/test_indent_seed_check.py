"""Native seeded-indentation verification must preserve and check every row."""
from __future__ import annotations

import contextlib
import io
import json
import random
import tempfile
import unittest
from pathlib import Path

from scripts.indent_seed_check import check_indent_seed, main

# Observed leading-space counts from the original 146-row Nachtlorn transcript.
OBSERVED = (
    "704165421026041253755351362424567661211272653076433336640656507543343"
    "776107043446727276060534403322031102550167161757510312670130421011642"
    "51627066"
)


class IndentSeedTests(unittest.TestCase):
    def body(self):
        return [" " * int(digit) + "ABCDE" for digit in OBSERVED]

    def test_original_146_counts_match_seed4300_exactly(self):
        self.assertEqual(len(OBSERVED), 146)
        report = check_indent_seed(self.body(), 4300)
        self.assertTrue(report["exact_match"])
        self.assertEqual(report["matches"], 146)
        self.assertEqual(report["mismatches"], [])
        self.assertEqual(report["observed"], report["predicted"])

    def test_single_changed_indent_is_not_ignored(self):
        body = self.body()
        body[-1] = " " + body[-1]
        report = check_indent_seed(body, 4300)
        self.assertFalse(report["exact_match"])
        self.assertEqual(report["matches"], 145)
        self.assertEqual(report["mismatches"], [
            {"body_row": 146, "observed": 7, "predicted": 6},
        ])

    def test_wrong_seed_does_not_match(self):
        report = check_indent_seed(self.body(), 4301)
        self.assertFalse(report["exact_match"])
        self.assertLess(report["matches"], 146)

    def test_local_rng_does_not_modify_global_state(self):
        state = random.getstate()
        check_indent_seed(self.body(), 4300)
        self.assertEqual(state, random.getstate())

    def test_trailing_whitespace_does_not_change_indent(self):
        body = [line + "  " for line in self.body()]
        self.assertTrue(check_indent_seed(body, 4300)["exact_match"])

    def test_empty_rows_input_invalid_width_and_leading_tabs_rejected(self):
        for body, width in (([], 8), (["ABC"], 0), (["\tABC"], 8), ([" \tABC"], 8)):
            with self.subTest(body=body, width=width), self.assertRaises(ValueError):
                check_indent_seed(body, 4300, width)

    def test_cli_header_filter_and_explicit_body_start(self):
        text = "blue at the bottom.\nFind the outlier.\n\n" + "\n".join(self.body()) + "\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            path.write_text(text, encoding="ascii")
            before = path.read_bytes()
            for options in ([], ["--body-start", "4"]):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    status = main([str(path), "--seed", "4300", *options])
                self.assertEqual(status, 0)
                self.assertEqual(json.loads(output.getvalue())["matches"], 146)
            self.assertEqual(path.read_bytes(), before)

    def test_cli_nonmatch_is_exit_one(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            path.write_text("\n".join(self.body()), encoding="ascii")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                status = main([str(path), "--seed", "4301"])
            self.assertEqual(status, 1)
            self.assertFalse(json.loads(output.getvalue())["exact_match"])

    def test_cli_bad_bounds_fail_before_reading_file(self):
        for options in (["--width", "0"], ["--body-start", "0"]):
            with self.subTest(options=options):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
                    main(["nonexistent-input.txt", "--seed", "4300", *options])
                self.assertEqual(result.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
