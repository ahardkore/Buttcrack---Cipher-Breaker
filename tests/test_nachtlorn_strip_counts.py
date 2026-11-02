from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts import nachtlorn_strip_counts as strips


class StripCountTests(unittest.TestCase):
    def test_known_hand_counts_and_spaces(self):
        report = strips.count_strips([' AB CD E', '  A I'])
        self.assertEqual(report['axis']['zero_based_source_column'], 4)
        self.assertEqual([(r['below'], r['on'], r['above']) for r in report['rows']],
                         [(2, 1, 2), (1, 1, 0)])
        self.assertEqual(report['rows'][0]['signed_range'], [-2, 2])
        self.assertEqual([r['letters'] for r in report['rows']], [5, 2])

    def test_zero_on_space_not_counted(self):
        report = strips.count_strips(['AB CD', '  I'])
        self.assertEqual((report['rows'][0]['below'], report['rows'][0]['on'], report['rows'][0]['above']),
                         (2, 0, 2))
        self.assertEqual(report['rows'][0]['letters'], 4)

    def test_indent_changes_physical_position_not_letter_order(self):
        a = strips.count_strips(['ABC D', '   I'])['rows'][0]
        b = strips.count_strips([' ABC D', '   I'])['rows'][0]
        self.assertEqual(a['letters'], b['letters'])
        self.assertEqual((a['below'], a['on'], a['above']), (3, 0, 1))
        self.assertEqual((b['below'], b['on'], b['above']), (2, 1, 1))

    def test_exact_range_uniqueness_and_extrema_handle_ties(self):
        rows = [{'body_row': 1, 'below': 2, 'above': 3},
                {'body_row': 2, 'below': 2, 'above': 3},
                {'body_row': 3, 'below': 1, 'above': 0},
                {'body_row': 4, 'below': 4, 'above': 3}]
        summary = strips.summarize_ranges(rows)
        self.assertEqual(summary['distinct_count_ranges'], 3)
        self.assertEqual(summary['unique_count_range_rows'], [3, 4])
        self.assertEqual(summary['above_minimum_rows'], [3])
        self.assertEqual(summary['above_maximum_rows'], [1, 2, 4])
        with self.assertRaises(ValueError):
            strips.summarize_ranges([])

    def test_trailing_spaces_do_not_move_terminal_guide(self):
        self.assertEqual(strips.count_strips(['ABC', ' I  '])['axis']['zero_based_source_column'], 1)

    def test_rejects_bad_rows_and_missing_guide(self):
        for rows in ([], ['abc', 'I'], ['ABC', 'J'], ['A\tB', 'I'], ['', 'I']):
            with self.assertRaises(ValueError):
                strips.count_strips(rows)
        with self.assertRaises(ValueError):
            strips.parse_rows(b'too short')

    def test_source_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'source'
            path.write_text('unchanged')
            with self.assertRaises(SystemExit):
                strips.main([str(path), '--output', str(path)])
            self.assertEqual(path.read_text(), 'unchanged')

    def test_published_rows_replayed_by_independent_slicing(self):
        root = Path(__file__).resolve().parents[1]
        result = root / 'docs/data/nachtlorn-strip-counts.json'
        if not result.exists():
            self.skipTest('source reproduction has not yet been recorded')
        report = json.loads(result.read_text())
        raw = (root / 'docs/data/nachtlorn-transcript.txt').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), report['source_sha256'])
        rows = raw.decode('ascii').splitlines()[8:]
        guide = rows[-1].rstrip().rindex('I')
        self.assertEqual(guide, 48)
        self.assertEqual(len(rows), 146)
        for row, record in zip(rows, report['rows']):
            count = lambda s: sum('A' <= c <= 'Z' for c in s)  # noqa: E731
            self.assertEqual((record['below'], record['on'], record['above']),
                             (count(row[:guide]), count(row[guide:guide + 1]), count(row[guide + 1:])))
            self.assertEqual(record['letters'], count(row))
        patterns = Counter((r['indent'], r['below'], r['on'], r['above']) for r in report['rows'][:-1])
        self.assertEqual(patterns, {(0, 40, 1, 19): 19, (1, 40, 0, 20): 20,
                                    (2, 39, 1, 20): 17, (3, 38, 1, 21): 18,
                                    (4, 37, 1, 22): 16, (5, 36, 1, 23): 16,
                                    (6, 35, 1, 24): 22, (7, 35, 0, 25): 17})
        self.assertEqual((report['rows'][-1]['below'], report['rows'][-1]['on'],
                          report['rows'][-1]['above']), (35, 1, 0))
        self.assertEqual(report['range_summary_all_rows'], strips.summarize_ranges(report['rows']))
        self.assertEqual(report['range_summary_all_rows']['unique_count_range_rows'], [146])
        self.assertEqual(report['range_summary_all_rows']['above_minimum_rows'], [146])
        self.assertEqual(report['range_summary_nonfinal_rows']['unique_count_range_rows'], [])
        self.assertEqual(report['range_summary_nonfinal_rows']['above_minimum'], 19)
        self.assertEqual(report['range_summary_nonfinal_rows']['above_minimum_rows'],
                         [r['body_row'] for r in report['rows'][:-1] if r['indent'] == 0])


if __name__ == '__main__':
    unittest.main()
