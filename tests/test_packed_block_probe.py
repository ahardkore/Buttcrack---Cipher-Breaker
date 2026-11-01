from __future__ import annotations

import contextlib
import io
import random
import tempfile
import unittest
from pathlib import Path

from scripts.packed_block_probe import block_letters, controls, main, phase_maps, predict, scan


def reference(rng, width, method, order, count):
    """Expand every digit, even for a huge block; do not use fast prefix division."""
    output = ""
    bound = 26 ** width
    while len(output) < count:
        if method == "randrange":
            number = rng.randrange(bound)
        elif method == "bits-mod":
            number = rng.getrandbits(bound.bit_length()) % bound
        elif method == "float-scaled":
            number = int(rng.random() * bound)
        else:
            numerator = int(rng.random() * (2 ** 53))
            number = numerator * bound // (2 ** 53)
        digits = []
        for _ in range(width):
            digits.append("ABCDEFGHIJKLMNOPQRSTUVWXYZ"[number % 26])
            number //= 26
        output += "".join(digits[::-1] if order == "big" else digits)
    return output[:count]


def toy_source():
    rng = random.Random(4300)
    for _ in range(3):
        rng.getrandbits(32)
    carrier = block_letters(rng, 5, "randrange", "big", 3000)
    return "".join(chr(65 + (ord(c) - 65 + 1 + i % 5) % 26)
                   for i, c in enumerate(carrier))


class PackedBlockProbeTests(unittest.TestCase):
    def test_native_reference_small_blocks_and_consumption(self):
        for width in (2, 5, 12, 26, 60):
            for method in ("randrange", "bits-mod", "float-scaled", "rational53"):
                for order in ("big", "little"):
                    with self.subTest(width=width, method=method, order=order):
                        a, b = random.Random(12345), random.Random(12345)
                        actual = block_letters(a, width, method, order, 121)
                        self.assertEqual(actual, reference(b, width, method, order, 121))
                        self.assertEqual(a.getstate(), b.getstate())

    def test_fast_prefix_matches_full_expansion_of_huge_integer(self):
        for method in ("randrange", "bits-mod", "rational53"):
            for order in ("big", "little"):
                with self.subTest(method=method, order=order):
                    a, b = random.Random(6789), random.Random(6789)
                    self.assertEqual(block_letters(a, 8736, method, order, 120),
                                     reference(b, 8736, method, order, 120))
                    self.assertEqual(a.getstate(), b.getstate())

    def test_phase_maps_enforce_both_directions(self):
        self.assertIsNone(phase_maps("AB", "AA", 1))
        self.assertIsNone(phase_maps("AA", "AB", 1))
        self.assertEqual(phase_maps("ABCD", "WXYZ", 1),
                         [{"W": "A", "X": "B", "Y": "C", "Z": "D"}])
        self.assertEqual(predict("AAAAA", phase_maps("BCDEF", "AAAAA")), "BCDEF")

    def test_unobserved_training_symbol_remains_unknown(self):
        maps = phase_maps("BCD", "ABC", 1)
        self.assertEqual(predict("ABD", maps), "BC?")

    def test_invalid_parameters_rejected(self):
        for width, method, order, count in ((0, "randrange", "big", 1),
                                          (5, "bad", "big", 1),
                                          (5, "randrange", "bad", 1),
                                          (5, "randrange", "big", 0),
                                          (8736, "float-scaled", "big", 120)):
            with self.assertRaises(ValueError):
                block_letters(random.Random(0), width, method, order, count)
        with self.assertRaises(ValueError):
            phase_maps("A", "AA")
        with self.assertRaises(ValueError):
            predict("A", [])
        with self.assertRaises(ValueError):
            scan("abc", [4300])
        with self.assertRaises(ValueError):
            scan("ABC", [4300], prefix=1, train=3)

    def test_four_training_only_controls_recover_entire_heldout_carrier(self):
        results = controls()
        self.assertEqual(len(results), 4)
        self.assertTrue(all(r["passed"] for r in results))
        self.assertTrue(all(r["training_prediction_classes"] == 1 for r in results))
        self.assertGreater(results[0]["training_fits"], 1)  # Initial rejection aliases.
        self.assertTrue(all(r["heldout_letters"] == 5736 for r in results))
        self.assertTrue(all(r["synthetic"] for r in results))

    def test_heldout_change_does_not_change_learned_maps_or_prediction(self):
        original = toy_source()
        changed = original[:2500] + chr(65 + (ord(original[2500]) - 64) % 26) + original[2501:]
        reports = [scan(text, [4300], widths=(5,), offset_max=4, prefix=60, train=2000)
                   for text in (original, changed)]
        winners = [next(r for r in report["prediction_records"]
                        if r["method"] == "randrange" and r["order"] == "big"
                        and r["raw_word_offset"] == 3) for report in reports]
        self.assertEqual(winners[0]["mismatch_positions"], [])
        self.assertEqual(winners[1]["mismatch_positions"], [2500])
        self.assertEqual(winners[0]["phase_maps"], winners[1]["phase_maps"])
        self.assertEqual(winners[0]["prediction_sha256"], winners[1]["prediction_sha256"])
        self.assertEqual(winners[1]["heldout_unknown"], 0)

    def test_training_conflict_rejects_prefix_only_match(self):
        original = toy_source()
        changed = original[:100] + chr(65 + (ord(original[100]) - 64) % 26) + original[101:]
        report = scan(changed, [4300], widths=(5,), offset_max=4, prefix=60, train=300)
        self.assertGreaterEqual(report["prefix_matches"], 1)
        self.assertFalse(any(r["method"] == "randrange" and r["order"] == "big"
                             and r["raw_word_offset"] == 3
                             for r in report["prediction_records"]))

    def test_global_rng_state_is_unchanged(self):
        state = random.getstate()
        scan(toy_source(), [4300], widths=(5,), offset_max=1, prefix=60, train=300)
        self.assertEqual(random.getstate(), state)

    def test_cli_cannot_overwrite_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.txt"
            path.write_bytes(b"original")
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main([str(path), "--output", str(path)])
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(path.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
