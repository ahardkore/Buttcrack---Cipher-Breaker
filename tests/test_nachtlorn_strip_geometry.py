from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import nachtlorn_strip_counts as counts
from scripts import nachtlorn_strip_geometry as geometry


def grouped(indent, size):
    return ' ' * indent + ' '.join('X' * min(5, size - start) for start in range(0, size, 5))


class StripGeometryTests(unittest.TestCase):
    def test_formula_replays_synthetic_grouped_rows(self):
        for indent in range(8):
            for length in (1, 4, 5, 6, 10, 11, 36, 60):
                row = grouped(indent, length)
                positions = [i for i, c in enumerate(row) if c == 'X']
                self.assertEqual(positions, geometry.predict_positions(indent, length))
                result = geometry.analyze([row], 48)
                self.assertEqual(result['exact_position_matches'], 1)
                self.assertEqual(result['count_matches'], 1)

    def test_extra_gap_breaks_geometry_even_if_counts_can_coincide(self):
        result = geometry.analyze(['ABCDE  FGHIJ'], 0)
        self.assertEqual(result['rows'][0]['first_mismatch_letter_index'], 5)
        self.assertFalse(result['rows'][0]['exact_position_match'])
        self.assertEqual(result['count_matches'], 1)

    def test_glyph_replacement_preserves_fixed_guide_counts(self):
        rows = [' ABCDE FGHIJ', '  ABCDE I']
        replaced = [''.join('Z' if c != ' ' else c for c in row) for row in rows]
        replaced[-1] = replaced[-1][:-1] + 'I'
        self.assertEqual(counts.count_strips(rows), counts.count_strips(replaced))
        self.assertEqual(geometry.analyze(rows, 8), geometry.analyze(replaced, 8))

    def test_invalid_arguments_and_source_guard(self):
        for args in ((-1, 1, 5), (0, 0, 5), (0, 1, 0), (True, 1, 5)):
            with self.assertRaises(ValueError):
                geometry.predict_positions(*args)
        for rows, guide in (([], 0), (['a'], 0), (['ABC'], -1)):
            with self.assertRaises(ValueError):
                geometry.analyze(rows, guide)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source'
            path.write_text('unchanged')
            with self.assertRaises(SystemExit):
                geometry.main([str(path), '--output', str(path)])
            self.assertEqual(path.read_text(), 'unchanged')

    def test_recorded_source_geometry_and_counterfactual(self):
        root = Path(__file__).resolve().parents[1]
        result = root / 'docs/data/nachtlorn-strip-geometry.json'
        if not result.exists():
            self.skipTest('source computation not yet recorded')
        report = json.loads(result.read_text())
        raw = (root / 'docs/data/nachtlorn-transcript.txt').read_bytes()
        self.assertEqual(report['source_sha256'], hashlib.sha256(raw).hexdigest())
        rows = counts.parse_rows(raw)
        self.assertEqual((report['guide_column'], report['exact_position_matches'], report['count_matches']),
                         (48, 146, 146))
        self.assertEqual(report['rows'], geometry.analyze(rows, 48)['rows'])
        count_report = json.loads((root / 'docs/data/nachtlorn-strip-counts.json').read_text())
        for r, c in zip(report['rows'], count_report['rows']):
            self.assertTrue(r['exact_position_match'])
            self.assertEqual(r['predicted_counts'], {k: c[k] for k in ('below', 'on', 'above')})
        # Change every other letter; retain only the final I as the guide.
        changed = [''.join(chr(65 + (ord(c) - 65 + 1) % 26) if c != ' ' else c for c in row) for row in rows]
        changed[-1] = changed[-1][:-1] + 'I'
        self.assertNotEqual(rows, changed)
        self.assertEqual(counts.count_strips(rows), counts.count_strips(changed))
        self.assertEqual(geometry.analyze(rows, 48), geometry.analyze(changed, 48))


if __name__ == '__main__':
    unittest.main()
