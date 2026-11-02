from __future__ import annotations

import copy
import hashlib
import itertools
import json
import tempfile
import unittest
from pathlib import Path

from scripts import nachtlorn_strip_pairing as probe


def observation(row, left, right):
    return {'body_row': row, 'left': left, 'right': right}


class PairingTests(unittest.TestCase):
    def test_counted_letters_pair_nearest_outward_not_physical_distance(self):
        pairs = probe.pairs_for_row('AB C DE', 7, 3)
        self.assertEqual([(p['left_column'], p['left'], p['right_column'], p['right']) for p in pairs],
                         [(1, 'B', 5, 'D'), (0, 'A', 6, 'E')])
        self.assertEqual([p['pair_index'] for p in pairs], [1, 2])
        self.assertEqual(probe.pairs_for_row('ABC I', 2, 4), [])

    def test_bijection_and_one_bad_row(self):
        pairs = [observation(1, 'A', 'C'), observation(1, 'B', 'D'),
                 observation(2, 'A', 'C'), observation(2, 'B', 'D'),
                 observation(3, 'A', 'D')]
        self.assertFalse(probe.consistent(pairs))
        self.assertEqual([i for i in range(1, 4) if probe.consistent(pairs, i)], [3])
        self.assertIsNone(probe.disjoint_certificate(pairs))
        self.assertTrue(probe.consistent(pairs, 3))

    def test_two_same_row_conflicts_and_certificate_replay(self):
        # Nearest-first A->X and A->Y in row 1; B->X and B->Y in row 2.
        rows = ['AA  XY', 'BB  XY']
        pairs = list(itertools.chain.from_iterable(probe.pairs_for_row(row, i, 3) for i, row in enumerate(rows, 1)))
        cert = probe.disjoint_certificate(pairs)
        self.assertTrue(probe.verify_certificate(rows, 3, cert))
        self.assertEqual([c['involved_rows'] for c in cert], [[1], [2]])
        altered = copy.deepcopy(cert)
        altered[0]['observations'][0]['right'] = 'Z'
        self.assertFalse(probe.verify_certificate(rows, 3, altered))
        altered = copy.deepcopy(cert)
        altered[0]['involved_rows'] = [2]
        self.assertFalse(probe.verify_certificate(rows, 3, altered))
        self.assertFalse(probe.verify_certificate(rows, 3, cert[:1]))

    def test_conflict_graph_matches_exhaustive_reference(self):
        universe = [observation(row, a, b) for row, a, b in itertools.product((1, 2, 3), 'AB', 'XY')]
        for sample in itertools.combinations(universe, 4):
            pairs = list(sample)
            edges = [{a['body_row'], b['body_row']} for a, b in itertools.combinations(pairs, 2)
                     if (a['left'] == b['left'] and a['right'] != b['right'])
                     or (a['left'] != b['left'] and a['right'] == b['right'])]
            expected = any(a.isdisjoint(b) for a, b in itertools.combinations(edges, 2))
            self.assertEqual(probe.disjoint_certificate(pairs) is not None, expected)
            for omitted in (None, 1, 2, 3):
                remaining = [p for p in pairs if p['body_row'] != omitted]
                oracle = all(not probe.conflicts(a, b) for a, b in itertools.combinations(remaining, 2))
                self.assertEqual(probe.consistent(pairs, omitted), oracle)

    def test_input_and_overwrite_guard(self):
        for row, index, guide in (('ab', 1, 2), ('ABC', 0, 1), ('ABC', 1, -1), ('A\tB', 1, 1)):
            with self.assertRaises(ValueError):
                probe.pairs_for_row(row, index, guide)
        with self.assertRaises(ValueError):
            probe.analyze(['I'], 0)
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'source'
            p.write_text('unchanged')
            with self.assertRaises(SystemExit):
                probe.main([str(p), '--output', str(p)])
            self.assertEqual(p.read_text(), 'unchanged')

    def test_published_certificates_and_single_omission_replay(self):
        root = Path(__file__).resolve().parents[1]
        path = root / 'docs/data/nachtlorn-strip-pairing-results.json'
        if not path.exists():
            self.skipTest('source run not yet recorded')
        report = json.loads(path.read_text())
        raw = (root / 'docs/data/nachtlorn-transcript.txt').read_bytes()
        self.assertEqual(report['source_sha256'], hashlib.sha256(raw).hexdigest())
        rows = raw.decode('ascii').splitlines()[8:]
        guide = len(rows[-1].rstrip()) - 1
        self.assertEqual(guide, 48)
        cert = report['disjoint_conflict_certificate']
        self.assertTrue(probe.verify_certificate(rows, guide, cert))
        # Independently reconstruct all observed ordered glyph pairs by slicing.
        row_pairs = []
        for row in rows[:-1]:
            left = [c for c in row[:guide] if 'A' <= c <= 'Z'][::-1]
            right = [c for c in row[guide + 1:] if 'A' <= c <= 'Z']
            row_pairs.append(list(zip(left, right)))
        self.assertEqual([len(p) for p in row_pairs], report['pair_counts_by_full_row'])
        self.assertEqual(sum(map(len, row_pairs)), report['paired_letters'])
        compatible = []
        for omit in range(145):
            remaining = [pair for i, row in enumerate(row_pairs) if i != omit for pair in row]
            left, right = {}, {}
            valid = True
            for a, b in remaining:
                if (a in left and left[a] != b) or (b in right and right[b] != a):
                    valid = False
                    break
                left[a], right[b] = b, a
            if valid:
                compatible.append(omit + 1)
        self.assertEqual(compatible, report['compatible_single_removed_rows'])
        self.assertEqual(report['final_row_pairs_excluded'], 0)


if __name__ == '__main__':
    unittest.main()
