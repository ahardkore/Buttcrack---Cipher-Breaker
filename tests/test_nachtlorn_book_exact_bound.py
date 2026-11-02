from __future__ import annotations

import hashlib
import json
import math
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import nachtlorn_book_exact_bound as bound

ROOT = Path(__file__).resolve().parents[1]


class BoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('g++'):
            raise unittest.SkipTest('C++ compiler required for native research controls')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.worker = Path(cls.tmp.name) / 'worker'
        subprocess.run(['g++', '-O3', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        str(ROOT / 'scripts/nachtlorn_book_bound_worker.cpp'), '-o', str(cls.worker)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_weight_bounds_against_independent_float(self):
        weights = bound.upper_weights()
        self.assertEqual(len(weights), 26)
        for weight, f in zip(weights, bound.FREQUENCIES):
            true = math.log(26 * f / sum(bound.FREQUENCIES))
            self.assertGreater(weight / 1000, true)
            self.assertLess(weight / 1000 - true, 0.00100000001)

    def test_native_all_offsets_against_independent_scalar_oracle(self):
        rng = random.Random(177)
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        for n, train, full in ((20, 3, 5), (50, 11, 21), (31, 30, 31), (7, 7, 7)):
            book = ''.join(rng.choices(alphabet, k=n))
            cipher = ''.join(rng.choices(alphabet, k=train))
            weights = bound.upper_weights()
            expected = [sum(weights[(ord(c) - ord(k)) % 26] for c, k in zip(cipher, book[i:i + train]))
                        for i in range(n - full + 1)]
            self.assertEqual(bound.run_worker(self.worker, book, cipher, full, all_scores=True), expected)
            best = bound.run_worker(self.worker, book, cipher, full)
            self.assertEqual(best['maximum_integer_upper_sum'], max(expected))
            self.assertEqual(best['first_maximum_offset'], expected.index(max(expected)))
            self.assertEqual(best['maximizing_offsets'], expected.count(max(expected)))

    def test_ties_and_final_eligible_start(self):
        result = bound.run_worker(self.worker, 'AAAAAA', 'AA', 4)
        self.assertEqual((result['windows'], result['first_maximum_offset'], result['maximizing_offsets']), (3, 0, 3))
        scores = bound.run_worker(self.worker, 'BBBBAAA', 'AA', 3, all_scores=True)
        self.assertEqual(len(scores), 5)

    def test_synthetic_english_like_plaintext_recovery(self):
        rng = random.Random(98765)
        book = ''.join(rng.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=1800))
        paragraph = ('THELANTERNBURNEDLOWINTHEHALLASWEWALKEDTOWARDTHEOPENWINDOW'
                     'THESEAWASSILENTANDTHESKYHADGROWNDARKBUTTHELIGHTSTILLCAME'
                     'THROUGHTHECURTAINANDRESTEDUPONTHEOLDWOODENTABLE')
        plain = (paragraph * 4)[:500]
        start = 771
        cipher = ''.join(chr(65 + ((ord(a) - 65 + ord(b) - 65) % 26))
                         for a, b in zip(plain, book[start:start + len(plain)]))
        result = bound.run_worker(self.worker, book, cipher[:300], len(cipher))
        self.assertEqual(result['first_maximum_offset'], start)
        self.assertGreater(result['maximum_integer_upper_sum'], 0)

    def test_invalid_input_and_overwrite_guards(self):
        for book, cipher, length in (('', 'AB', 2), ('aBC', 'AB', 2), ('ABC', 'AB', 4), ('ABC', '', 2)):
            with self.assertRaises(ValueError):
                bound.run_worker(self.worker, book, cipher, length)
        with tempfile.TemporaryDirectory() as d:
            source, book = Path(d) / 'source', Path(d) / 'book'
            source.write_text('source')
            book.write_text('book')
            for dest in (source, book, self.worker):
                with self.assertRaises(SystemExit):
                    bound.main([str(source), '--book', str(book), '--worker', str(self.worker), '--output', str(dest)])
            self.assertEqual((source.read_text(), book.read_text()), ('source', 'book'))

    def test_recorded_source_witness_independently_replayed(self):
        report_path = ROOT / 'docs/data/nachtlorn-book-runningkey-exact-bound.json'
        book_path = ROOT / 'scratch/nachtlorn-ulysses4300.txt'
        if not report_path.exists() or not book_path.exists():
            self.skipTest('recorded source result or optional book absent')
        result = json.loads(report_path.read_text())
        raw, book_raw = (ROOT / 'docs/data/nachtlorn-transcript.txt').read_bytes(), book_path.read_bytes()
        self.assertEqual(result['source_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['book_sha256'], hashlib.sha256(book_raw).hexdigest())
        cipher, book = bound.source_stream(raw), bound.ascii_letters(book_raw.decode('utf8'))
        self.assertEqual(result['windows'], len(book) - len(cipher) + 1)
        offset, training = result['first_maximum_offset'], result['training_letters']
        self.assertEqual(result['maximum_integer_upper_sum'],
                         bound.direct_upper(cipher[:training], book[offset:offset + training], bound.upper_weights()))
        self.assertEqual(result['upper_integer_weights'], bound.upper_weights())
        self.assertEqual(result['all_training_scores_negative'], result['maximum_integer_upper_sum'] < 0)
        previous = json.loads((ROOT / 'docs/data/nachtlorn-book-runningkey-fullscan.json').read_text())
        self.assertEqual(offset, previous['training_selected_book_offset'])
        for upper, r25_weight in zip(result['upper_integer_weights'], previous['weights']):
            self.assertGreater(upper / result['scale'], r25_weight)
        self.assertGreater(result['maximum_mean_upper_bound_nats'], previous['training_llr_nats_per_letter'])


if __name__ == '__main__':
    unittest.main()
