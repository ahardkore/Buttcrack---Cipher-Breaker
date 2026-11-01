"""Construction evidence must stay distinct from recovered plaintext."""
from __future__ import annotations

import contextlib
import io
import json
import math
import random
import tempfile
import unittest
from pathlib import Path

from scripts.reused_pad_probe import ENGLISH_WEIGHTS, main, pair_likelihoods


def letters(values):
    return "".join(chr(65 + x % 26) for x in values)


class ReusedPadProbeTests(unittest.TestCase):
    def test_single_pair_difference_has_analytic_score_and_shift(self):
        result = pair_likelihoods("Q", "M", 1)["results"]["difference"]
        expected = math.log(26 * sum((w / sum(ENGLISH_WEIGHTS)) ** 2
                                     for w in ENGLISH_WEIGHTS))
        self.assertAlmostEqual(result["log_likelihood_ratio"], expected)
        self.assertEqual(result["fitted_phase_shifts"], [4])
        self.assertEqual(result["modular_counts"][0][4], 1)

    def test_each_phase_is_fitted_independently(self):
        result = pair_likelihoods("ABCDE", "AAAAA")["results"]["difference"]
        self.assertEqual(result["fitted_phase_shifts"], list(range(5)))
        self.assertAlmostEqual(result["phase_scores"][0], result["phase_scores"][4])

    def test_uniform_counts_are_shift_invariant_and_score_negative(self):
        alphabet = letters(range(26))
        report = pair_likelihoods("A" * 26, alphabet, 1)
        for result in report["results"].values():
            self.assertEqual(result["modular_counts"], [[1] * 26])
            self.assertLess(result["log_likelihood_ratio"], 0)

    def test_native_same_and_opposite_sign_controls_with_phase_shifts(self):
        rng = random.Random(20261101)
        n = 10000
        first = rng.choices(range(26), weights=ENGLISH_WEIGHTS, k=n)
        second = rng.choices(range(26), weights=ENGLISH_WEIGHTS, k=n)
        key = [rng.randrange(26) for _ in range(n)]
        shifts = [2, 8, 4, 20, 0]
        left = letters(a + k for a, k in zip(first, key))
        for sign, operation, other in ((1, "difference", "sum"), (-1, "sum", "difference")):
            with self.subTest(sign=sign):
                right = letters(b + sign * k + shifts[i % 5]
                                for i, (b, k) in enumerate(zip(second, key)))
                result = pair_likelihoods(left, right)["results"]
                self.assertGreater(result[operation]["log_likelihood_ratio"], 0)
                self.assertGreater(result[operation]["log_likelihood_ratio"],
                                   result[other]["log_likelihood_ratio"])
                self.assertEqual(result[operation]["fitted_phase_shifts"],
                                 [(-s if sign == 1 else s) % 26 for s in shifts])

    def test_shift_of_first_window_does_not_change_optimized_scores(self):
        rng = random.Random(713)
        a = [rng.randrange(26) for _ in range(400)]
        b = letters(rng.randrange(26) for _ in a)
        before = pair_likelihoods(letters(a), b)
        after = pair_likelihoods(letters(x + 7 for x in a), b)
        for operation in ("difference", "sum"):
            self.assertAlmostEqual(before["results"][operation]["log_likelihood_ratio"],
                                   after["results"][operation]["log_likelihood_ratio"])

    def test_invalid_windows_and_phases_are_rejected(self):
        for first, second, phases in (("", "", 1), ("a", "A", 1), ("É", "A", 1),
                                      ("A B", "ABC", 1), ("AA", "A", 1),
                                      ("AA", "AA", 0), ("AA", "AA", 3)):
            with self.subTest(first=first, second=second, phases=phases), self.assertRaises(ValueError):
                pair_likelihoods(first, second, phases)

    def test_cli_is_read_only_and_matches_direct_function(self):
        text = "BLOOM\nFind the outlier.\n\n  ABCDE FGHIJ\n KLMNO PQRST\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cipher.txt"
            path.write_text(text, encoding="ascii")
            before = path.read_bytes()
            for options in ([], ["--body-start", "4"]):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main([str(path), "--second-start", "10",
                                           "--pairs", "10", *options]), 0)
                report = json.loads(output.getvalue())
                self.assertEqual(report["results"], pair_likelihoods("ABCDEFGHIJ", "KLMNOPQRST")["results"])
                self.assertIn("not recovered plaintext", report["caution"])
                self.assertEqual(report["second_start"], 10)
            self.assertEqual(path.read_bytes(), before)

    def test_cli_bad_arguments_fail_before_file_access(self):
        for options in (["--first-start", "-1"], ["--second-start", "-1"],
                        ["--pairs", "0"], ["--phases", "11"], ["--body-start", "0"]):
            with self.subTest(options=options):
                with contextlib.redirect_stderr(io.StringIO()) as error, self.assertRaises(SystemExit) as result:
                    main(["missing.txt", "--second-start", "10", "--pairs", "10", *options])
                self.assertEqual(result.exception.code, 2)
                self.assertNotIn("No such file", error.getvalue())

    def test_cli_out_of_range_window_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cipher.txt"
            path.write_text("ABCDE FGHIJ\n", encoding="ascii")
            with contextlib.redirect_stderr(io.StringIO()) as error, self.assertRaises(SystemExit):
                main([str(path), "--second-start", "8", "--pairs", "5"])
            self.assertIn("beyond the letter stream", error.getvalue())

    def test_cli_explicit_body_rejects_non_ciphertext(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cipher.txt"
            path.write_text("Heading\nABCDE FGHIJ\n", encoding="ascii")
            with contextlib.redirect_stderr(io.StringIO()) as error, self.assertRaises(SystemExit):
                main([str(path), "--second-start", "5", "--pairs", "5", "--body-start", "1"])
            self.assertIn("non-uppercase", error.getvalue())


if __name__ == "__main__":
    unittest.main()
