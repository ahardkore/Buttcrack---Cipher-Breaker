from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import numpy as np
except ImportError:
    np = None

if np is not None:
    from scripts import nachtlorn_short_row_power as probe
    from scripts.nachtlorn_book_fullscan import direct_score


@unittest.skipIf(np is None, 'optional numpy research dependency missing')
class ShortRowPowerTests(unittest.TestCase):
    def test_control_encrypts_and_recovers_exactly(self):
        book = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' * 4
        phrase = 'The little lantern shone brightly through the morning fog.'
        plaintext, cipher = probe.make_control(book, phrase, 7)
        self.assertEqual(len(plaintext), 36)
        self.assertEqual(probe.decrypt(cipher, book[7:43]), plaintext)
        with patch.object(probe, 'analyze', return_value={
            'training_selected_book_offset': 7, 'offsets_scored': len(book) - 35,
            'training_llr_nats_per_letter': 0.5, 'heldout_llr_nats_per_letter': 0.4,
            'heldout_screen_pass': True, 'fft_direct_absolute_error': 0.0,
        }):
            report = probe.run_control(book, phrase, 7)
        self.assertTrue(report['exact_plaintext_recovered'])
        self.assertTrue(report['heldout_screen_pass'])

    def test_short_phrase_invalid_offset_and_guard(self):
        for book, phrase, offset in (('A' * 100, 'short', 0), ('A' * 30, 'A' * 36, 0),
                                     ('A' * 100, 'A' * 36, -1), ('A' * 100, 'A' * 36, True)):
            with self.assertRaises(ValueError):
                probe.make_control(book, phrase, offset)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'book'
            path.write_text('unchanged')
            with self.assertRaises(SystemExit):
                probe.main(['--book', str(path), '--output', str(path)])
            self.assertEqual(path.read_text(), 'unchanged')

    def test_recorded_synthetic_winners_scalar_replay(self):
        root = Path(__file__).resolve().parents[1]
        result = root / 'docs/data/nachtlorn-short-row-power-controls.json'
        book_path = root / 'scratch/nachtlorn-ulysses4300.txt'
        if not result.exists() or not book_path.exists():
            self.skipTest('source result or optional book not present')
        report = json.loads(result.read_text())
        raw = book_path.read_bytes()
        self.assertEqual(report['book_sha256'], hashlib.sha256(raw).hexdigest())
        book = probe.ascii_letters(raw.decode('utf8'))
        self.assertTrue(report['synthetic_only'])
        self.assertFalse(report['actual_source_search_performed'])
        self.assertEqual(len(report['controls']), 8)
        self.assertEqual(report['control_gate_passed'],
                         all(r['exact_plaintext_recovered'] and r['heldout_screen_pass'] for r in report['controls']))
        for result, phrase, start in zip(report['controls'], probe.PHRASES, probe.STARTS):
            plain, cipher = probe.make_control(book, phrase, start)
            pos = result['selected_book_offset']
            self.assertEqual(result['eligible_offsets'], len(book) - 35)
            self.assertEqual(result['planted_book_offset'], start)
            self.assertEqual(result['planted_plaintext_sha256'], hashlib.sha256(plain.encode()).hexdigest())
            self.assertAlmostEqual(result['training_llr_nats_per_letter'],
                                   direct_score(cipher[:25], book[pos:pos + 25]) / 25, places=12)
            self.assertAlmostEqual(result['heldout_llr_nats_per_letter'],
                                   direct_score(cipher[25:], book[pos + 25:pos + 36]) / 11, places=12)
            predicted = probe.decrypt(cipher, book[pos:pos + 36])
            self.assertEqual(result['exact_plaintext_recovered'], predicted == plain)


if __name__ == '__main__':
    unittest.main()
