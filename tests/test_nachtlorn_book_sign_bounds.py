from __future__ import annotations

import hashlib
import json
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import nachtlorn_book_sign_bounds as probe

ROOT = Path(__file__).resolve().parents[1]


class SignBoundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('g++'):
            raise unittest.SkipTest('C++ compiler required for native research controls')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.worker = Path(cls.tmp.name) / 'worker'
        subprocess.run(['g++', '-O3', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        str(ROOT / 'scripts/nachtlorn_book_sign_worker.cpp'), '-o', str(cls.worker)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_native_scores_against_independent_scalar(self):
        rng = random.Random(842)
        for n, training, full in ((17, 3, 8), (50, 10, 19), (43, 29, 40), (20, 20, 20)):
            book = ''.join(rng.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=n))
            cipher = ''.join(rng.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=training))
            weights = probe.upper_weights()
            def direct(start, mode, book=book, training=training, weights=weights, cipher=cipher):
                key = book[start:start + training]
                if mode == 0:
                    return sum(weights[(ord(k) - ord(c)) % 26] for c, k in zip(cipher, key))
                return sum(weights[(ord(c) + ord(k) - 130) % 26] for c, k in zip(cipher, key))
            expected = [(direct(i, 0), direct(i, 1)) for i in range(n - full + 1)]
            self.assertEqual(probe.run_worker(self.worker, book, cipher, full, all_scores=True), expected)
            report = probe.run_worker(self.worker, book, cipher, full)
            for mode, record in enumerate(report['models']):
                scores = [r[mode] for r in expected]
                self.assertEqual(record['maximum_integer_upper_sum'], max(scores))
                self.assertEqual(record['first_maximum_offset'], scores.index(max(scores)))
                self.assertEqual(record['maximizing_offsets'], scores.count(max(scores)))

    def test_synthetic_messages_recover_both_signs(self):
        rng = random.Random(98765)
        book = ''.join(rng.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=1800))
        paragraph = ('THELANTERNBURNEDLOWINTHEHALLASWEWALKEDTOWARDTHEOPENWINDOW'
                     'THESEAWASSILENTANDTHESKYHADGROWNDARKBUTTHELIGHTSTILLCAME'
                     'THROUGHTHECURTAINANDRESTEDUPONTHEOLDWOODENTABLE')
        plain = (paragraph * 4)[:500]
        start = 771
        for mode in probe.MODES:
            cipher = ''.join(chr(65 + ((ord(k) - ord(p)) if mode == 'K-C' else (ord(p) - ord(k))) % 26)
                             for p, k in zip(plain, book[start:start + len(plain)]))
            report = probe.run_worker(self.worker, book, cipher[:300], len(cipher))
            result = next(r for r in report['models'] if r['operation'] == mode)
            self.assertEqual(result['first_maximum_offset'], start)
            self.assertGreater(result['maximum_integer_upper_sum'], 0)

    def test_invalid_and_overwrite_guards(self):
        for args in (('', 'AB', 2), ('abc', 'AB', 2), ('ABC', 'AB', 4), ('ABC', '', 2)):
            with self.assertRaises(ValueError):
                probe.run_worker(self.worker, *args)
        with self.assertRaises(ValueError):
            probe.score('A', 'A', 'invalid', probe.upper_weights())
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a', Path(d) / 'b'
            a.write_text('source')
            b.write_text('book')
            for dest in (a, b, self.worker):
                with self.assertRaises(SystemExit):
                    probe.main([str(a), '--book', str(b), '--worker', str(self.worker), '--output', str(dest)])
            self.assertEqual((a.read_text(), b.read_text()), ('source', 'book'))

    def test_recorded_witness_and_source_replay(self):
        path = ROOT / 'docs/data/nachtlorn-book-sign-bounds.json'
        book_path = ROOT / 'scratch/nachtlorn-ulysses4300.txt'
        if not path.exists() or not book_path.exists():
            self.skipTest('source result or optional book absent')
        raw, book_raw = (ROOT / 'docs/data/nachtlorn-transcript.txt').read_bytes(), book_path.read_bytes()
        report = json.loads(path.read_text())
        self.assertEqual(report['source_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(report['book_sha256'], hashlib.sha256(book_raw).hexdigest())
        cipher, book = probe.source_stream(raw), probe.ascii_letters(book_raw.decode('utf8'))
        self.assertEqual(report['windows'], len(book) - len(cipher) + 1)
        for r in report['models']:
            start, n = r['first_maximum_offset'], report['training_letters']
            self.assertEqual(r['maximum_integer_upper_sum'], probe.score(cipher[:n], book[start:start + n], r['operation'], probe.upper_weights()))
            self.assertEqual(r['all_training_scores_negative'], r['maximum_integer_upper_sum'] < 0)


if __name__ == '__main__':
    unittest.main()
