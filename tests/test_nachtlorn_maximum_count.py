from __future__ import annotations

import hashlib
import itertools
import json
import math
import tempfile
import unittest
from collections import Counter
from fractions import Fraction
from pathlib import Path

from scripts import nachtlorn_maximum_count as diagnostic


class MaximumCountTests(unittest.TestCase):
    def test_binomial_integer_tail_matches_direct_sum(self):
        for base in range(2, 8):
            for n in range(0, 16):
                for k in range(n + 2):
                    wanted = Fraction(sum(math.comb(n, j) * (base - 1) ** (n - j)
                                          for j in range(k, n + 1)), base ** n)
                    self.assertEqual(diagnostic.binomial_upper_tail(n, k, base), wanted)

    def test_union_bound_against_all_small_sequences(self):
        for base in (2, 3, 4):
            for n in range(1, 8):
                words = list(itertools.product(range(base), repeat=n))
                for k in range(1, n + 1):
                    observed = sum(max(Counter(w).values()) >= k for w in words)
                    exact = Fraction(observed, len(words))
                    union = min(Fraction(1), base * diagnostic.binomial_upper_tail(n, k, base))
                    self.assertLessEqual(exact, union)

    def test_boundaries_and_invalid_inputs(self):
        self.assertEqual(diagnostic.binomial_upper_tail(0, 0, 26), 1)
        self.assertEqual(diagnostic.binomial_upper_tail(5, 6, 26), 0)
        self.assertEqual(diagnostic.decimal_value(Fraction(1, 4)), '0.25')
        for args in ((-1, 1, 26), (1, -1, 26), (1, 1, 1), (True, 1, 26)):
            with self.assertRaises(ValueError):
                diagnostic.binomial_upper_tail(*args)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source'
            path.write_text('unchanged')
            with self.assertRaises(SystemExit):
                diagnostic.main([str(path), '--output', str(path)])
            self.assertEqual(path.read_text(), 'unchanged')

    def test_recorded_histogram_and_bound_independent_direct_sum(self):
        root = Path(__file__).resolve().parents[1]
        result = root / 'docs/data/nachtlorn-maximum-count-null.json'
        if not result.exists():
            self.skipTest('source result not yet recorded')
        report = json.loads(result.read_text())
        raw = (root / 'docs/data/nachtlorn-transcript.txt').read_bytes()
        self.assertEqual(report['source_sha256'], hashlib.sha256(raw).hexdigest())
        rows = raw.decode('ascii').splitlines()[8:]
        text = ''.join(c for row in rows for c in row if 'A' <= c <= 'Z')
        hist = Counter(text)
        self.assertEqual(report['counts_A_to_Z'], [hist[c] for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'])
        self.assertEqual((report['max_glyphs'], report['max_count']), (['E'], 412))
        n, k = len(text), report['max_count']
        # Independent floating log-sum, not the exact integer recurrence.
        tail = math.fsum(math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                                  - i * math.log(26) + (n - i) * math.log(25 / 26))
                         for i in range(k, n + 1))
        self.assertTrue(math.isclose(float(report['specified_glyph_binomial_upper_tail_decimal']), tail, rel_tol=1e-10))
        self.assertTrue(math.isclose(float(report['maximum_26_glyph_union_bound_decimal']), 26 * tail, rel_tol=1e-10))
        self.assertEqual(report['page1_max_glyph_counts'], {'E': sum(row.count('E') for row in rows[:61])})
        self.assertEqual(report['page2_max_glyph_counts'], {'E': sum(row.count('E') for row in rows[61:])})


if __name__ == '__main__':
    unittest.main()
