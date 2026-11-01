"""Supplied-parameter probes must not silently change a candidate or its frame."""
from __future__ import annotations

import contextlib
import io
import json
import random
import tempfile
import unittest
from pathlib import Path

from scripts.seed_pad_probe import main, probe_pad, restore_terminal_i


class SeedPadProbeTests(unittest.TestCase):
    cipher = "PWRPSYVPMBAZZI"
    observed = "SHAREISPAGETTI"

    def test_known_unmodified_candidate_not_repaired(self):
        # Original body offsets2021..2034 use raw word indices2674..2687.
        result = probe_pad(self.cipher, 4300, 2674, 0, 14)
        self.assertEqual(result, self.observed)
        self.assertNotEqual(result, "SHARESPAGHETTI")

    def test_letter_offset_advances_pad_instead_of_restarting_it(self):
        self.assertEqual(
            probe_pad("ABC" + self.cipher + "ZZ", 4300, 2671, 3, 14),
            self.observed,
        )

    def test_native_independent_additive_control(self):
        plain = "THISISANINDEPENDENTNATIVEPADCONTROL"
        rng = random.Random(20261101)
        for _ in range(17):
            rng.getrandbits(32)
        cipher = "".join(
            chr(65 + (ord(char) - 65 - ((rng.getrandbits(32) >> 27) % 26)) % 26)
            for char in plain
        )
        self.assertEqual(probe_pad(cipher, 20261101, 17, 0, len(cipher)), plain)
        self.assertEqual(probe_pad(plain, 20261101, 17, 0, len(plain), "subtract"), cipher)

    def test_reverse_subtract_is_an_involution_with_the_same_pad(self):
        plain = "ATTACKATDAWN"
        cipher = probe_pad(plain, 9876, 5, 0, len(plain), "reverse-subtract")
        self.assertEqual(
            probe_pad(cipher, 9876, 5, 0, len(cipher), "reverse-subtract"), plain,
        )

    def test_global_random_state_is_unchanged(self):
        state = random.getstate()
        probe_pad(self.cipher, 4300, 2674, 0, 14)
        self.assertEqual(state, random.getstate())

    def test_invalid_stream_bounds_and_operation_rejected(self):
        for stream, word, letter, length, operation in (
            ("abc", 0, 0, 1, "add"), ("A B", 0, 0, 1, "add"),
            ("É", 0, 0, 1, "add"), ("A", -1, 0, 1, "add"),
            ("A", 0, -1, 1, "add"), ("A", 0, 0, 0, "add"),
            ("A", 0, 0, 2, "add"), ("A", 0, 0, 1, "unknown"),
        ):
            with self.subTest(stream=stream, word=word, letter=letter, length=length):
                with self.assertRaises(ValueError):
                    probe_pad(stream, 4300, word, letter, length, operation)

    def test_cli_is_read_only_and_preserves_the_raw_candidate(self):
        text = "BLOOM\nFind the outlier.\n\n  PWRPS YVPMB AZZI\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            path.write_text(text, encoding="ascii")
            before = path.read_bytes()
            for options in ([], ["--body-start", "4"]):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    status = main([str(path), "--seed", "4300", "--word-offset", "2674",
                                   "--length", "14", *options])
                self.assertEqual(status, 0)
                report = json.loads(output.getvalue())
                self.assertEqual(report["decoded_candidate"], self.observed)
                self.assertEqual(report["ciphertext_window"], self.cipher)
                self.assertIn("hypothesis", report["caution"])
            self.assertEqual(path.read_bytes(), before)

    def test_cli_bad_bounds_fail_before_reading_input(self):
        for option, value in (("--word-offset", "-1"), ("--letter-offset", "-1"),
                              ("--length", "0"), ("--body-start", "0")):
            with self.subTest(option=option):
                args = ["missing.txt", "--seed", "4300", "--word-offset", "0",
                        "--length", "1", option, value]
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as result:
                        main(args)
                self.assertEqual(result.exception.code, 2)


class TerminalIRestorationTests(unittest.TestCase):
    def test_only_terminal_i_is_removed_and_length_preserved(self):
        for boundary, letter, expected in (
            (0, "X", "XABCD"), (2, "X", "ABXCD"),
            (4, "X", "ABCDX"), (4, "I", "ABCDI"),
        ):
            with self.subTest(boundary=boundary, letter=letter):
                result = restore_terminal_i("ABCDI", boundary, letter)
                self.assertEqual(result, expected)
                self.assertEqual(len(result), 5)
        self.assertEqual(restore_terminal_i("AIBCI", 2, "X"), "AIXBC")

    def test_invalid_source_and_letter_rejected(self):
        for source, letter in (("", "X"), ("ABCDX", "X"), ("A B I", "X"),
                               ("ABCDI", "x"), ("ABCDI", "XY"), ("ABCDI", "É")):
            with self.subTest(source=source, letter=letter):
                with self.assertRaises(ValueError):
                    restore_terminal_i(source, 0, letter)

    def test_invalid_boundaries_rejected(self):
        for boundary in (-1, 5):
            with self.subTest(boundary=boundary):
                with self.assertRaises(ValueError):
                    restore_terminal_i("ABCDI", boundary, "X")

    def test_cli_restoration_flags_must_be_paired(self):
        for options in (["--restore-at", "5"], ["--restore-letter", "Y"]):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    main(["missing.txt", "--seed", "4300", "--word-offset", "2674",
                          "--length", "14", *options])
            self.assertEqual(result.exception.code, 2)

    def test_cli_invalid_restoration_fails_before_reading_input(self):
        for boundary, letter, message in (
            ("-1", "X", "nonnegative"), ("0", "x", "uppercase ASCII"),
            ("0", "É", "uppercase ASCII"), ("0", "XY", "uppercase ASCII"),
        ):
            with self.subTest(boundary=boundary, letter=letter):
                with contextlib.redirect_stderr(io.StringIO()) as error:
                    with self.assertRaises(SystemExit) as result:
                        main(["missing.txt", "--seed", "4300", "--word-offset", "0",
                              "--length", "1", "--restore-at", boundary,
                              "--restore-letter", letter])
                self.assertEqual(result.exception.code, 2)
                self.assertIn(message, error.getvalue())
                self.assertNotIn("No such file", error.getvalue())

    def test_cli_explicit_hypothesis_is_read_only_and_recovers_control(self):
        clean = "PWRPSYVPMBAZZI"
        damaged = clean[:5] + clean[6:] + "I"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            path.write_text(damaged + "\n", encoding="ascii")
            before = path.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()) as output:
                main([str(path), "--body-start", "1", "--seed", "4300",
                      "--word-offset", "2674", "--length", "14",
                      "--restore-at", "5", "--restore-letter", "Y"])
            report = json.loads(output.getvalue())
            self.assertEqual(report["original_ciphertext_window"], damaged)
            self.assertEqual(report["ciphertext_window"], clean)
            self.assertEqual(report["decoded_candidate"], "SHAREISPAGETTI")
            self.assertFalse(report["hypothetical_source_edit"]["noop"])
            self.assertIn("input file unchanged", report["caution"])
            self.assertEqual(path.read_bytes(), before)

    def test_cli_rejects_nonterminal_i_source_and_labels_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            args = [str(path), "--body-start", "1", "--seed", "4300",
                    "--word-offset", "0", "--length", "5",
                    "--restore-at", "2", "--restore-letter", "I"]
            path.write_text("ABCDX\n", encoding="ascii")
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    main(args)
            self.assertEqual(result.exception.code, 2)
            path.write_text("ABIII\n", encoding="ascii")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                main(args)
            self.assertTrue(json.loads(output.getvalue())["hypothetical_source_edit"]["noop"])
            self.assertEqual(path.read_text(encoding="ascii"), "ABIII\n")


if __name__ == "__main__":
    unittest.main()
