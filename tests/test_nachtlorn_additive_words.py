from __future__ import annotations

import contextlib
import io
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.nachtlorn_additive_words import control_rows, controls, main, native_scan, scan


@unittest.skipUnless(shutil.which("g++"), "g++ is required for the additive-check worker")
class NachtlornAdditiveWordsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.worker = Path(cls.directory.name) / "additive-worker"
        source = Path(__file__).resolve().parents[1] / "scripts/nachtlorn_additive_word_probe.cpp"
        subprocess.run([shutil.which("g++"), "-std=c++17", "-O3", "-Wall", "-Wextra", "-Werror",
                        str(source), "-o", str(cls.worker)], check=True, capture_output=True, timeout=60)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    @staticmethod
    def graph_rank(rows):
        # A width-two one-hot matrix is an unoriented bipartite incidence matrix.
        # Negating one side turns it into an oriented incidence matrix, whose
        # rank over either tested field is vertices minus connected components.
        neighbors = [[] for _ in range(52)]
        for a, b in rows:
            neighbors[a].append(26 + b)
            neighbors[26 + b].append(a)
        unseen = set(range(52))
        components = 0
        while unseen:
            components += 1
            stack = [unseen.pop()]
            while stack:
                for vertex in neighbors[stack.pop()]:
                    if vertex in unseen:
                        unseen.remove(vertex)
                        stack.append(vertex)
        return 52 - components

    def test_rank_and_every_coloop_match_independent_graph_oracle(self):
        rng = random.Random(223606)
        rows = [[rng.randrange(26), rng.randrange(26)] for _ in range(80)]
        expected_rank = self.graph_rank(rows)
        expected_exceptions = [i for i in range(len(rows))
                               if self.graph_rank(rows[:i] + rows[i + 1:]) < expected_rank]
        for q in (2, 13):
            report = native_scan(self.worker, rows, q)
            self.assertEqual(report["rank"], expected_rank)
            self.assertEqual(report["coloops"], expected_exceptions)
            self.assertEqual(len(report["witnesses"]), min(8, len(expected_exceptions)))

    def test_single_bridge_is_the_only_exception_in_both_fields(self):
        rows = [[0, 0], [0, 1], [1, 0], [1, 1], [2, 2], [2, 3], [3, 2], [3, 3], [1, 2]]
        for q in (2, 13):
            report = native_scan(self.worker, rows, q)
            self.assertEqual(report["rank"], 7)
            self.assertEqual(report["coloops"], [8])
            self.assertEqual(report["witnesses"][0]["row"], 8)

    def test_hidden_position_alphabet_controls(self):
        report = controls(self.worker)
        self.assertEqual([r["q"] for r in report], [2, 13])
        self.assertTrue(all(r["synthetic"] and r["rank"] == 126 and r["outlier_index"] == 137
                            and r["checksum_witness_replayed"] for r in report))

    def test_relabeling_columns_and_reversing_samples_preserve_the_result(self):
        rows, exception = control_rows(13)
        rng = random.Random(244949)
        permutations = []
        for _ in range(5):
            p = list(range(26))
            rng.shuffle(p)
            permutations.append(p)
        changed = [[permutations[j][row[j]] for j in reversed(range(5))] for row in reversed(rows)]
        original = native_scan(self.worker, rows, 13)
        transformed = native_scan(self.worker, changed, 13)
        self.assertEqual(original["rank"], transformed["rank"])
        self.assertEqual(transformed["coloops"], [len(rows) - 1 - exception])

    def test_invalid_inputs_rejected(self):
        for rows, q in (([[0] * 5] * 2, 3), ([[0] * 5], 13), ([[0] * 17] * 3, 13),
                        ([[26] * 5] * 3, 13), ([[0] * 5, [0] * 4], 2)):
            with self.assertRaises(ValueError):
                native_scan(self.worker, rows, q)
        for text in ("2 3 5\n", "2 13 5\n0 0 0 0 0\n", "2 2 1\n0\n0 trailing"):
            result = subprocess.run([str(self.worker)], input=text, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertTrue(result.stderr)

    def test_cli_cannot_overwrite_source_or_worker(self):
        source = Path(self.directory.name) / "original.txt"
        source.write_bytes(b"unchanged")
        for output in (source, self.worker):
            before = output.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                with self.assertRaises(SystemExit) as failure:
                    main([str(source), "--worker", str(self.worker), "--width", "5", "--output", str(output)])
            self.assertEqual(failure.exception.code, 2)
            self.assertIn("must not overwrite", errors.getvalue())
            self.assertEqual(output.read_bytes(), before)

    def test_all_phases_record_unedited_source_positions_and_leave_rng_alone(self):
        rows, exception = control_rows(13)
        source = "".join(chr(v + 65) for row in rows for v in row) + "I"
        state = random.getstate()
        report = scan(source, self.worker, 5)
        self.assertEqual(random.getstate(), state)
        self.assertEqual(report["case_count"], 10)
        self.assertEqual({(r["q"], r["phase"]) for r in report["cases"]},
                         {(q, phase) for q in (2, 13) for phase in range(5)})
        case = next(r for r in report["cases"] if r["q"] == 13 and r["phase"] == 0)
        self.assertEqual(case["excluded_tail"], "I")
        self.assertEqual(case["coloops"], [exception])
        self.assertEqual(case["exception_groups"][0],
                         {"group_index": exception, "letter_offset": 5 * exception,
                          "source_word": source[5 * exception:5 * exception + 5]})


if __name__ == "__main__":
    unittest.main()
