from __future__ import annotations

import hashlib
import itertools
import json
import random
import tempfile
import unittest
from pathlib import Path

from scripts import nachtlorn_indel_capacity as probe


def brute_run(text, stride, capacity):
    best = 0
    for start in range(len(text)):
        glyphs = set()
        for pos in range(start, len(text), stride):
            glyphs.add(text[pos])
            if len(glyphs) > capacity:
                break
            best = max(best, (pos - start) // stride + 1)
    return best


class IndelCapacityTests(unittest.TestCase):
    def test_capacities_are_exact_under_nonnegative_suffix_relaxation(self):
        self.assertEqual([probe.leading_capacity(64, 14, b) for b in (0, 1)], [8, 7])
        for bias in (0, 1):
            c = probe.leading_capacity(64, 14, bias)
            base = bias * ((26 ** 14 - 1) // 25)
            self.assertLessEqual((c - 1) * 26 ** 13 + base, 2 ** 64 - 1)
            self.assertGreater(c * 26 ** 13 + base, 2 ** 64 - 1)

    def test_sliding_window_matches_exhaustive_brute_force(self):
        for letters in itertools.product('ABC', repeat=7):
            text = ''.join(letters)
            for stride in (1, 2, 3, 8):
                for capacity in (1, 2, 3):
                    result = probe.longest_run(text, stride, capacity)
                    self.assertEqual(result['length'], brute_run(text, stride, capacity))
                    witness = text[result['source_start']:result['source_end'] + 1:stride]
                    self.assertEqual(len(witness), result['length'])
                    self.assertEqual(''.join(sorted(set(witness))), result['distinct_glyphs'])
                    self.assertLessEqual(len(set(witness)), capacity)

    def test_all_small_single_pair_edits_obey_inequality(self):
        # Exhaust all sources, deletion locations, insertion locations and glyphs.
        for letters in itertools.product('ABC', repeat=6):
            source = ''.join(letters)
            for stride, capacity in ((1, 1), (2, 1), (2, 2), (3, 2)):
                r = brute_run(source, stride, capacity)
                for deleted in range(len(source)):
                    partial = source[:deleted] + source[deleted + 1:]
                    for insert in range(len(source)):
                        for glyph in 'ABC':
                            target = partial[:insert] + glyph + partial[insert:]
                            for offset in range(stride):
                                leaders = target[offset::stride]
                                if len(set(leaders)) <= capacity and leaders:
                                    self.assertLessEqual(len(leaders) - 1, 3 * r)
                                    self.assertLessEqual(probe.minimum_pairs(len(leaders), r), 1)

    def test_real_schema_valid_synthetic_pair_survives_bound(self):
        rng = random.Random(231)
        # Any A0 key < 2**64, serialized as 14 fixed-width A0 glyphs.
        def field(value, width):
            out = []
            for _ in range(width):
                out.append(chr(65 + value % 26))
                value //= 26
            self.assertEqual(value, 0)
            return ''.join(reversed(out))
        cells = [(field(rng.getrandbits(32), 7), field(rng.getrandbits(64), 14),
                  field(rng.getrandbits(32), 7)) for _ in range(312)]
        for layout, stride in probe.PROFILES:
            target = (''.join(''.join(cell) for cell in cells) if layout == 'cell_interleaved'
                      else ''.join(cell[col] for col in range(3) for cell in cells))
            source = target[:100] + target[101:]
            source = source[:3000] + 'Z' + source[3000:]
            without_insertion = source[:3000] + source[3001:]
            self.assertEqual(without_insertion[:100] + target[100] + without_insertion[100:], target)
            r = probe.longest_run(source, stride, 8)['length']
            self.assertLessEqual(311, 3 * r)
            self.assertLessEqual(probe.minimum_pairs(312, r), 1)

    def test_certificate_tampering_is_detected(self):
        text = 'ABACCBABCABBAC'
        cert = probe.longest_run(text, 2, 2)
        self.assertTrue(probe.verify_certificate(text, 2, 2, cert))
        for key, value in (('length', cert['length'] + 1), ('source_end', len(text)),
                           ('distinct_glyphs', 'Z'), ('source_start', None)):
            tampered = dict(cert)
            tampered[key] = value
            self.assertFalse(probe.verify_certificate(text, 2, 2, tampered))

    def test_lower_bound_is_minimum_for_the_inequality(self):
        for n in range(1, 50):
            for r in range(1, 50):
                m = probe.minimum_pairs(n, r)
                self.assertLessEqual(n - m, (2 * m + 1) * r)
                if m:
                    self.assertGreater(n - (m - 1), (2 * (m - 1) + 1) * r)

    def test_invalid_inputs_and_overwrite_guard(self):
        for args in (('', 1, 1), ('ABC', 0, 1), ('AbC', 1, 1), ('ABC', 1, 0)):
            with self.assertRaises(ValueError):
                probe.longest_run(*args)
        with self.assertRaises(ValueError):
            probe.analyze('ABC')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source'
            path.write_text('unchanged')
            with self.assertRaises(SystemExit):
                probe.main([str(path), '--output', str(path)])
            self.assertEqual(path.read_text(), 'unchanged')

    def test_recorded_certificate_independently_replayed(self):
        root = Path(__file__).resolve().parents[1]
        result_path = root / 'docs/data/nachtlorn-reset-indel-capacity-results.json'
        if not result_path.exists():
            self.skipTest('source run has not yet been recorded')
        report = json.loads(result_path.read_text())
        raw = (root / 'docs/data/nachtlorn-transcript.txt').read_bytes()
        self.assertEqual(report['source_sha256'], hashlib.sha256(raw).hexdigest())
        text = ''.join(c for row in raw.decode('ascii').splitlines()[8:] for c in row if 'A' <= c <= 'Z')
        self.assertEqual(len(report['profiles']), 4)
        for profile in report['profiles']:
            stride, capacity = profile['source_stride'], profile['leading_capacity']
            certificate = profile['longest_source_run']
            self.assertTrue(probe.verify_certificate(text, stride, capacity, certificate))
            self.assertEqual(certificate['length'], brute_run(text, stride, capacity))
            witness = text[certificate['source_start']:certificate['source_end'] + 1:stride]
            self.assertEqual(len(witness), certificate['length'])
            self.assertEqual(''.join(sorted(set(witness))), certificate['distinct_glyphs'])
            self.assertLessEqual(len(set(witness)), capacity)
            self.assertEqual(profile['necessary_minimum_paired_edits'],
                             probe.minimum_pairs(312, certificate['length']))


if __name__ == '__main__':
    unittest.main()
