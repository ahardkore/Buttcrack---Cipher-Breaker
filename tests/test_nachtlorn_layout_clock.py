from __future__ import annotations

import hashlib
import itertools
import json
import random
import tempfile
import unittest
from pathlib import Path

from scripts import nachtlorn_layout_clock as probe


def native_batch(rng, method, size):
    if method == "randrange26":
        return [rng.randrange(26) for _ in range(size)]
    if method == "choices26":
        return [int(rng.random() * 26) for _ in range(size)]
    if method == "bits5_mod26":
        return [rng.getrandbits(5) % 26 for _ in range(size)]
    if method == "bits8_mod26":
        return [rng.getrandbits(8) % 26 for _ in range(size)]
    return [b % 26 for b in rng.randbytes(size)]


def plain_recipe(lengths, method, schedule, seed):
    rng = random.Random(seed)
    if schedule == "all_rows_then_indents":
        for size in lengths:
            native_batch(rng, method, size)
        values = [rng.randrange(8) for _ in lengths]
    elif schedule == "row_then_indent":
        values = []
        for size in lengths:
            native_batch(rng, method, size)
            values.append(rng.randrange(8))
    else:
        values = []
        for size in lengths:
            values.append(rng.randrange(8))
            native_batch(rng, method, size)
    return values, rng.getstate()


class LayoutClockTests(unittest.TestCase):
    def test_tracing_preserves_native_values_and_states(self):
        for seed, method in itertools.product((0, 43, 4300), probe.METHODS):
            traced, plain = probe.TracedRandom(seed), random.Random(seed)
            for size in (0, 1, 3, 7, 31, 60, 36):
                self.assertEqual(probe.letter_batch(traced, method, size), native_batch(plain, method, size))
                self.assertEqual(traced.getstate(), plain.getstate())
                self.assertEqual(traced.randrange(8), plain.randrange(8))
                self.assertEqual(traced.getstate(), plain.getstate())

    def test_native_rejections_are_counted_not_assumed_fixed(self):
        for bound in (8, 26):
            traced, manual = probe.TracedRandom(4300), random.Random(4300)
            attempts, expected = 0, []
            for _ in range(146):
                while True:
                    value = manual.getrandbits(bound.bit_length())
                    attempts += 1
                    if value < bound:
                        expected.append(value)
                        break
            actual = [traced.randrange(bound) for _ in range(146)]
            self.assertEqual(actual, expected)
            self.assertEqual(traced.words, attempts)
            self.assertEqual(traced.getstate(), manual.getstate())
            self.assertGreater(attempts, 146)
        indent_rng = probe.TracedRandom(4300)
        for _ in range(146):
            indent_rng.randrange(8)
        self.assertEqual(indent_rng.words, 323)

    def test_bit_float_and_byte_word_consumption(self):
        for size in (0, 1, 3, 4, 5, 36, 60):
            for method in probe.METHODS[1:]:
                rng = probe.TracedRandom(19)
                probe.letter_batch(rng, method, size)
                expected = (size + 3) // 4 if method == "row_randbytes_mod26" else size * (2 if method == "choices26" else 1)
                self.assertEqual(rng.words, expected)
                plain = random.Random(19)
                for _ in range(expected):
                    plain.getrandbits(32)
                self.assertEqual(rng.getstate(), plain.getstate())

    def test_all_schedules_match_independent_plain_random_recipes(self):
        lengths = [1, 7, 31, 60, 36, 9]
        for seed, method, schedule in itertools.product((11, 4300), probe.METHODS, probe.SCHEDULES):
            result = probe.simulate(lengths, method, schedule, seed=seed)
            values, state = plain_recipe(lengths, method, schedule, seed)
            self.assertEqual(result["predicted_indents"], values)
            digest = hashlib.sha256(json.dumps(state, separators=(",", ":")).encode()).hexdigest()
            self.assertEqual(result["final_state_sha256"], digest)

    def test_synthetic_schedule_recovery_retains_truth_and_aliases(self):
        lengths = [3, 7, 17, 60, 36, 5, 60, 23]
        for method, schedule in itertools.product(probe.METHODS, probe.SCHEDULES):
            observed, _state = plain_recipe(lengths, method, schedule, 123)
            result = probe.scan(lengths, observed, seed=123)
            compatible = [c for c in result["cases"] if c["exact_layout_match"]]
            self.assertTrue(any(c["method"] == method and c["schedule"] == schedule for c in compatible))
            self.assertEqual(sum(len(g["members"]) for g in result["prediction_groups"]), 15)

    def test_different_bit_widths_are_clock_aliases_not_letter_aliases(self):
        rng5, rng8 = random.Random(4300), random.Random(4300)
        self.assertNotEqual(probe.letter_batch(rng5, "bits5_mod26", 60),
                            probe.letter_batch(rng8, "bits8_mod26", 60))
        for schedule in probe.SCHEDULES:
            a = probe.simulate([60, 60, 36], "bits5_mod26", schedule)
            b = probe.simulate([60, 60, 36], "bits8_mod26", schedule)
            self.assertEqual(a, b)

    def test_byte_batch_boundaries_matter_for_ragged_rows(self):
        a, b = probe.TracedRandom(43), probe.TracedRandom(43)
        probe.letter_batch(a, "row_randbytes_mod26", 1)
        probe.letter_batch(a, "row_randbytes_mod26", 3)
        probe.letter_batch(b, "row_randbytes_mod26", 4)
        self.assertEqual((a.words, b.words), (2, 1))
        self.assertNotEqual(a.getstate(), b.getstate())

    def test_first_mismatch_and_prefix_are_reported_exactly(self):
        prediction = probe.simulate([3] * 6, "randrange26", "indent_then_row")
        observed = prediction["predicted_indents"][:]
        observed[2] = (observed[2] + 1) % 8
        result = probe.compare(observed, prediction)
        self.assertEqual((result["matches"], result["mismatches"], result["matching_prefix_rows"]), (5, 1, 2))
        self.assertEqual(result["first_mismatches"][0]["body_row"], 3)
        self.assertFalse(result["exact_layout_match"])

    def test_global_random_state_is_unchanged(self):
        before = random.getstate()
        probe.scan([60, 36], [3, 2])
        self.assertEqual(before, random.getstate())

    def test_invalid_parameters_raise_instead_of_rejecting_models(self):
        for lengths, method, schedule in (([], "choices26", "indent_then_row"),
                                          ([0], "choices26", "indent_then_row"),
                                          ([60], "unknown", "indent_then_row"),
                                          ([60], "choices26", "unknown")):
            with self.assertRaises(ValueError):
                probe.simulate(lengths, method, schedule)
        with self.assertRaises(ValueError):
            probe.compare([8], probe.simulate([60], None, "indent_then_row"))
        with self.assertRaises(ValueError):
            probe.letter_batch(random.Random(1), "choices26", -1)

    def test_published_predictions_replay_with_plain_native_random(self):
        root = Path(__file__).resolve().parents[1]
        raw = (root / "docs/data/nachtlorn-transcript.txt").read_bytes()
        report = json.loads((root / "docs/data/nachtlorn-reset-layout-clock-results.json").read_text())
        self.assertEqual(report["source_sha256"], hashlib.sha256(raw).hexdigest())
        rows = raw.decode("ascii").splitlines()[8:]
        lengths = [sum("A" <= c <= "Z" for c in row) for row in rows]
        observed = [len(row) - len(row.lstrip(" ")) for row in rows]
        self.assertEqual(report["row_lengths"], lengths)
        self.assertEqual(report["observed_indents"], observed)
        self.assertTrue(report["baseline"]["exact_layout_match"])
        groups = {g["id"]: g for g in report["prediction_groups"]}
        self.assertEqual((len(report["cases"]), len(groups)), (15, 12))
        for case in report["cases"]:
            expected, state = plain_recipe(lengths, case["method"], case["schedule"], report["seed"])
            self.assertEqual(groups[case["prediction_group"]]["predicted_indents"], expected)
            self.assertEqual(case["matches"], sum(a == b for a, b in zip(observed, expected)))
            self.assertFalse(case["exact_layout_match"])
            digest = hashlib.sha256(json.dumps(state, separators=(",", ":")).encode()).hexdigest()
            self.assertEqual(case["final_state_sha256"], digest)

    def test_source_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.txt"
            path.write_text("unchanged")
            with self.assertRaises(SystemExit):
                probe.main([str(path), "--output", str(path)])
            self.assertEqual(path.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
