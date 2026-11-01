from __future__ import annotations

import contextlib
import io
import itertools
import json
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.nachtlorn_modular_words import (
    ALPHABETS,
    controls,
    main,
    native_scan,
    projective_directions,
    scan,
)


@unittest.skipUnless(shutil.which("g++"), "g++ is required for the native projection worker")
class NachtlornModularWordsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.worker = Path(cls.directory.name) / "modular-worker"
        source = Path(__file__).resolve().parents[1] / "scripts/nachtlorn_modular_word_probe.cpp"
        subprocess.run([shutil.which("g++"), "-std=c++17", "-O3", "-Wall", "-Wextra", "-Werror",
                        str(source), "-o", str(cls.worker)], check=True, capture_output=True, timeout=60)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    @staticmethod
    def independent_directions(q):
        result = set()
        for vector in itertools.product(range(q), repeat=5):
            if not any(vector):
                continue
            inverse = pow(next(x for x in vector if x), -1, q)
            result.add(tuple(x * inverse % q for x in vector))
        return result

    def test_complete_scalar_equivalence_classes(self):
        for q in (2, 5):
            generated = [tuple(a) for a in projective_directions(q)]
            self.assertEqual(len(generated), (q ** 5 - 1) // (q - 1))
            self.assertEqual(set(generated), self.independent_directions(q))
        directions = list(projective_directions(13))
        self.assertEqual(len(directions), 30941)
        self.assertEqual(len({tuple(a) for a in directions}), 30941)

    def test_native_ranking_matches_independent_exhaustive_oracle(self):
        rng = random.Random(161803)
        for q in (2, 5):
            rows = [[rng.randrange(q) for _ in range(5)] for _ in range(73)]
            expected = []
            for a in self.independent_directions(q):
                counts = [sum(sum(x * v for x, v in zip(row, a)) % q == residue for row in rows)
                          for residue in range(q)]
                expected.append((sum(c * c for c in counts), a, counts))
            expected.sort(key=lambda item: (-item[0], item[1]))
            report = native_scan(self.worker, rows, q)
            self.assertEqual([(r["sum_squares"], tuple(r["coefficients"]), r["histogram"])
                              for r in report["top"]], expected[:8])

    def test_single_exception_mixing_and_sample_reversal_controls(self):
        self.assertEqual(controls(self.worker), {
            "synthetic": True, "rows": 257, "coefficients": [1, 2, 3, 5, 8],
            "outlier_index": 137, "directions": 30941,
            "single_error": True, "affine_mixing": True, "sample_reversal": True})

    def test_fixed_vigenere_shifts_preserve_projection_score_family(self):
        rng = random.Random(141421)
        rows = [[rng.randrange(26) for _ in range(5)] for _ in range(97)]
        key = [ord(c) - 65 for c in "BLOOM"]
        shifted = [[(x - a) % 26 for x, a in zip(row, key)] for row in rows]
        for q in (2, 13):
            before = native_scan(self.worker, [[x % q for x in row] for row in rows], q)
            after = native_scan(self.worker, [[x % q for x in row] for row in shifted], q)
            self.assertEqual([r["sum_squares"] for r in before["top"]],
                             [r["sum_squares"] for r in after["top"]])

    def test_invalid_fields_rows_and_native_input_rejected(self):
        for q, rows in ((4, [[0] * 5] * 3), (13, [[0] * 5]),
                        (13, [[0] * 4] * 3), (13, [[13] * 5] * 3)):
            with self.assertRaises(ValueError):
                native_scan(self.worker, rows, q)
        for raw in ("3 4\n", "3 13\n0 0 0 0 0\n", "2 2\n0 0 0 0 0\n0 0 0 0 0 trailing"):
            process = subprocess.run([str(self.worker)], input=raw, text=True, capture_output=True)
            self.assertEqual(process.returncode, 2)
            self.assertTrue(process.stderr)
        with self.assertRaises(ValueError):
            list(projective_directions(4))

    def test_cli_never_overwrites_either_input(self):
        source = Path(self.directory.name) / "original.txt"
        source.write_bytes(b"unchanged")
        for output in (source, self.worker):
            before = output.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()) as errors, self.assertRaises(SystemExit) as result:
                main([str(source), "--worker", str(self.worker), "--alphabet", "standard",
                      "--output", str(output)])
            self.assertEqual(result.exception.code, 2)
            self.assertIn("must not overwrite", errors.getvalue())
            self.assertEqual(output.read_bytes(), before)

    def test_nulls_are_deterministic_preserve_marginals_and_do_not_change_global_rng(self):
        rng = random.Random(173205)
        source = "".join(rng.choice(ALPHABETS["standard"]) for _ in range(150)) + "I"
        real = native_scan
        calls = []

        def record(worker, rows, q):
            calls.append((q, [row[:] for row in rows]))
            return real(worker, rows, q)

        state = random.getstate()
        with patch("scripts.nachtlorn_modular_words.native_scan", side_effect=record):
            report = scan(source, ALPHABETS["standard"], self.worker, nulls=2, seed=42)
        self.assertEqual(random.getstate(), state)
        self.assertEqual(report["complete_groups"], 30)
        self.assertEqual(report["unconsumed_tail"], "I")
        self.assertEqual(len(report["null_results"]), 2)
        originals = dict(calls[:2])
        for q, rows in calls[2:]:
            for j in range(5):
                self.assertEqual(sorted(row[j] for row in rows), sorted(row[j] for row in originals[q]))
        self.assertEqual(report, scan(source, ALPHABETS["standard"], self.worker, nulls=2, seed=42))

    def test_native_records_are_independently_replayed(self):
        rows = [[i % 2, (i // 2) % 2, (i // 3) % 2, (i // 5) % 2, (i // 7) % 2] for i in range(19)]
        original = native_scan(self.worker, rows, 2)
        for fault in ("histogram", "version"):
            corrupted = json.loads(json.dumps(original))
            if fault == "histogram":
                corrupted["top"][0]["histogram"][0] += 1
            else:
                corrupted["version"] = 0
            with patch("scripts.nachtlorn_modular_words.subprocess.run",
                       return_value=SimpleNamespace(stdout=json.dumps(corrupted))), self.assertRaises(ValueError):
                native_scan(self.worker, rows, 2)


if __name__ == "__main__":
    unittest.main()
