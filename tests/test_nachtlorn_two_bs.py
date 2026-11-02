from __future__ import annotations

import hashlib
import itertools
import json
import math
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from scripts import nachtlorn_two_bs as probe


class TwoBsTests(unittest.TestCase):
    def test_literal_rule_and_axis_boundary(self):
        for row, guide, expected in [('BBAAA', 3, True), ('ABBAA', 3, True),
                                     ('BBBAA', 4, False), ('BAAAA', 4, False),
                                     ('AABBA', 3, False), ('ABABA', 3, False),
                                     ('AAAAA', 3, False)]:
            self.assertEqual(probe.inspect(row, guide)['matches_rule'], expected)

    def test_spaces_count_as_columns_not_slots(self):
        r = probe.inspect(' B B A', 4)
        self.assertEqual((r['b_left'], r['b_on'], r['b_right'], r['left_slots']), (2, 0, 0, 2))
        self.assertTrue(r['matches_rule'])

    def test_exact_null_probability_against_enumeration(self):
        for n in range(2, 10):
            for left in range(n + 1):
                samples = [''.join('B' if i in pair else 'A' for i in range(n))
                           for pair in itertools.combinations(range(n), 2)]
                successes = sum(probe.inspect(row, left)['matches_rule'] for row in samples)
                report = probe.inspect(samples[0], left)
                self.assertEqual(Fraction(successes, len(samples)),
                                 Fraction(report['conditional_expected_match_numerator'],
                                          report['conditional_expected_match_denominator']))

    def test_total_count_condition_not_diluted(self):
        for row in ('AAAAAA', 'BAAAAA', 'BBBAAA'):
            r = probe.inspect(row, 4)
            self.assertFalse(r['matches_rule'])
            self.assertEqual(r['conditional_expected_match_numerator'], 0)

    def test_input_validation_and_source_guard(self):
        for row, guide in (('', 0), ('A\tB', 0), ('a', 0), ('AB', -1), ('AB', True)):
            with self.assertRaises(ValueError):
                probe.inspect(row, guide)
        with self.assertRaises(ValueError):
            probe.analyze(['I'], 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source'
            path.write_text('unchanged')
            with self.assertRaises(SystemExit):
                probe.main([str(path), '--output', str(path)])
            self.assertEqual(path.read_text(), 'unchanged')

    def test_published_source_independent_slice_replay(self):
        root = Path(__file__).resolve().parents[1]
        path = root / 'docs/data/nachtlorn-two-bs-results.json'
        if not path.exists():
            self.skipTest('source execution not yet recorded')
        report = json.loads(path.read_text())
        raw = (root / 'docs/data/nachtlorn-transcript.txt').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), report['source_sha256'])
        rows = raw.decode('ascii').splitlines()[8:]
        guide = len(rows[-1].rstrip()) - 1
        self.assertEqual(guide, 48)
        matches = []
        expectation = Fraction(0)
        for i, (row, result) in enumerate(zip(rows, report['rows']), 1):
            below, on, above = row[:guide].count('B'), row[guide:guide + 1].count('B'), row[guide + 1:].count('B')
            self.assertEqual((result['b_left'], result['b_on'], result['b_right']), (below, on, above))
            self.assertEqual(result['matches_rule'], (below, on, above) == (2, 0, 0))
            if i <= 145:
                if (below, on, above) == (2, 0, 0):
                    matches.append(i)
                if below + on + above == 2:
                    slots = sum('A' <= c <= 'Z' for c in row[:guide])
                    expectation += Fraction(math.comb(slots, 2), math.comb(60, 2))
        self.assertEqual(matches, report['full_row_matches'])
        self.assertEqual(len(matches), report['full_row_match_count'])
        null = report['conditional_null']
        self.assertEqual(expectation, Fraction(null['exact_expected_matches_numerator'],
                                                null['exact_expected_matches_denominator']))


if __name__ == '__main__':
    unittest.main()
