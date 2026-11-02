from __future__ import annotations

import hashlib
import json
import math
import random
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None

if np is not None:
    from scripts import nachtlorn_book_fullscan as scan


@unittest.skipIf(np is None, 'optional numpy research dependency missing')
class FullBookScanTests(unittest.TestCase):
    def test_fft_all_offsets_match_direct_scores(self):
        rng = random.Random(133)
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        for size, train, full in ((17, 3, 8), (50, 10, 19), (43, 29, 40), (20, 20, 20)):
            book = ''.join(rng.choices(alphabet, k=size))
            cipher = ''.join(rng.choices(alphabet, k=train))
            got = scan.fft_scores(book, cipher, full)
            wanted = [scan.direct_score(cipher, book[i:i + train]) for i in range(size - full + 1)]
            np.testing.assert_allclose(got, wanted, rtol=0, atol=1e-10)

    def test_running_key_synthetic_control_recovers_training_and_holdout(self):
        rng = random.Random(98765)
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        book = ''.join(rng.choices(alphabet, k=1800))
        paragraph = ('THELANTERNBURNEDLOWINTHEHALLASWEWALKEDTOWARDTHEOPENWINDOW'
                     'THESEAWASSILENTANDTHESKYHADGROWNDARKBUTTHELIGHTSTILLCAME'
                     'THROUGHTHECURTAINANDRESTEDUPONTHEOLDWOODENTABLE')
        plaintext = (paragraph * 4)[:500]
        start = 771
        cipher = ''.join(chr(65 + ((ord(a) - 65 + ord(b) - 65) % 26))
                         for a, b in zip(plaintext, book[start:start + len(plaintext)]))
        result = scan.analyze(book, cipher, train_length=300)
        self.assertEqual(result['training_selected_book_offset'], start)
        self.assertTrue(result['heldout_screen_pass'])
        self.assertEqual(scan.decrypt(cipher, book[start:start + len(cipher)]), plaintext)
        self.assertEqual(result['decoded_sha256'], hashlib.sha256(plaintext.encode()).hexdigest())

    def test_threshold_is_prespecified_and_weight_normalization(self):
        self.assertEqual(scan.THRESHOLD, 0.1)
        self.assertTrue(math.isclose(sum(math.exp(w) / 26 for w in scan.WEIGHTS), 1, abs_tol=1e-14))
        self.assertEqual(scan.decrypt('ABC', 'BCD'), 'ZZZ')
        self.assertTrue(math.isclose(scan.direct_score('ABC', 'BCD'), 3 * scan.WEIGHTS[25]))

    def test_invalid_and_source_overwrite_guards(self):
        for text in ('', 'abc', 'A B'):
            with self.assertRaises(ValueError):
                scan.as_numbers(text)
        with self.assertRaises(ValueError):
            scan.decrypt('ABC', 'AB')
        with self.assertRaises(ValueError):
            scan.fft_scores('ABC', 'AB', 4)
        with self.assertRaises(ValueError):
            scan.analyze('ABCDE', 'ABC', train_length=3)
        with tempfile.TemporaryDirectory() as directory:
            source, book = Path(directory) / 'source', Path(directory) / 'book'
            source.write_text('source')
            book.write_text('book')
            for dest in (source, book):
                with self.assertRaises(SystemExit):
                    scan.main([str(source), '--book', str(book), '--output', str(dest)])
            self.assertEqual((source.read_text(), book.read_text()), ('source', 'book'))

    def test_actual_recorded_winner_direct_replay(self):
        root = Path(__file__).resolve().parents[1]
        report_path = root / 'docs/data/nachtlorn-book-runningkey-fullscan.json'
        book_path = root / 'scratch/nachtlorn-ulysses4300.txt'
        if not report_path.exists() or not book_path.exists():
            self.skipTest('recorded result or optional book absent')
        report = json.loads(report_path.read_text())
        raw = (root / 'docs/data/nachtlorn-transcript.txt').read_bytes()
        book_raw = book_path.read_bytes()
        self.assertEqual(report['source_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(report['book_sha256'], hashlib.sha256(book_raw).hexdigest())
        cipher = scan.source_stream(raw)
        book = scan.ascii_letters(book_raw.decode('utf8'))
        start, train = report['training_selected_book_offset'], report['training_letters']
        self.assertEqual(report['offsets_scored'], len(book) - len(cipher) + 1)
        direct = scan.direct_score(cipher[:train], book[start:start + train])
        self.assertAlmostEqual(direct, report['direct_score_sum'], places=9)
        suffix = scan.direct_score(cipher[train:], book[start + train:start + len(cipher)]) / (len(cipher) - train)
        self.assertAlmostEqual(suffix, report['heldout_llr_nats_per_letter'], places=12)
        self.assertEqual(report['heldout_screen_pass'], suffix >= scan.THRESHOLD)
        plain = scan.decrypt(cipher, book[start:start + len(cipher)])
        self.assertEqual(report['decoded_sha256'], hashlib.sha256(plain.encode()).hexdigest())


if __name__ == '__main__':
    unittest.main()
