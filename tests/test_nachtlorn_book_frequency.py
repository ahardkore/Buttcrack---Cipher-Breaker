from __future__ import annotations

import hashlib
import json
import random
import tempfile
import unittest
from collections import Counter
from itertools import accumulate
from pathlib import Path

from scripts import nachtlorn_book_frequency as probe


def brute(text, width):
    values = [max(Counter(text[i:i + width]).values()) for i in range(len(text) - width + 1)]
    minimum = min(values)
    return {'minimum_window_max_count': minimum, 'first_attaining_offset': values.index(minimum),
            'attaining_windows': values.count(minimum), 'windows_examined': len(values)}


class BookFrequencyTests(unittest.TestCase):
    def test_ascii_normalization_filters_before_uppercasing(self):
        self.assertEqual(probe.ascii_letters('aZßéü 9Kb'), 'AZB')

    def test_rolling_minimum_matches_all_small_bruteforce_windows(self):
        rng = random.Random(918)
        for n in range(1, 42):
            book = ''.join(rng.choice('ABCDE') for _ in range(n))
            for width in range(1, n + 1):
                self.assertEqual(probe.min_window_maximum(book, width), brute(book, width))

    def test_exact_book_length_and_last_window_included(self):
        self.assertEqual(probe.min_window_maximum('AABB', 4)['windows_examined'], 1)
        result = probe.min_window_maximum('AAAAABCD', 4)
        self.assertEqual((result['minimum_window_max_count'], result['first_attaining_offset']), (1, 4))

    def test_planted_secret_substitution_and_transposition_survives(self):
        plaintext = 'AAAABBCCDE'
        encrypted = ''.join({'A': 'Z', 'B': 'Q', 'C': 'R', 'D': 'X', 'E': 'F'}[c] for c in plaintext)
        shuffled = ''.join(reversed(encrypted))
        report = probe.compare('ZZ' + plaintext + 'ZZ', shuffled)
        self.assertFalse(report['all_contiguous_windows_excluded_by_max_count'])
        self.assertEqual(sorted(Counter(shuffled).values()), sorted(Counter(plaintext).values()))
        self.assertEqual(Counter(encrypted), Counter(shuffled))

    def test_bound_for_glyph_changes_and_not_a_sufficiency_claim(self):
        result = probe.compare('AAAA', 'ABCD')
        self.assertEqual(result['minimum_cipher_symbol_substitutions_required'], 3)
        self.assertTrue(result['all_contiguous_windows_excluded_by_max_count'])
        self.assertFalse(probe.compare('AABBCC', 'AABCDE')['all_contiguous_windows_excluded_by_max_count'])
        self.assertNotEqual(sorted(Counter('AABBCC').values()), sorted(Counter('AABCDE').values()))

    def test_invalid_inputs_and_overwrite_guards(self):
        for text, width in (('', 1), ('AbC', 1), ('ABC', 0), ('ABC', 4), ('ABC', True)):
            with self.assertRaises(ValueError):
                probe.min_window_maximum(text, width)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            book = Path(directory) / 'book'
            source.write_text('source')
            book.write_text('book')
            for output in (source, book):
                with self.assertRaises(SystemExit):
                    probe.main([str(source), '--book', str(book), '--output', str(output)])
            self.assertEqual(source.read_text(), 'source')
            self.assertEqual(book.read_text(), 'book')

    def test_recorded_source_and_book_witness(self):
        root = Path(__file__).resolve().parents[1]
        path = root / 'docs/data/nachtlorn-book-frequency-invariant.json'
        book_path = root / 'scratch/nachtlorn-ulysses4300.txt'
        if not path.exists() or not book_path.exists():
            self.skipTest('result or optional pinned book not present')
        report = json.loads(path.read_text())
        source = (root / 'docs/data/nachtlorn-transcript.txt').read_bytes()
        raw_book = book_path.read_bytes()
        self.assertEqual(report['source_sha256'], hashlib.sha256(source).hexdigest())
        self.assertEqual(report['book_sha256'], hashlib.sha256(raw_book).hexdigest())
        book = probe.ascii_letters(raw_book.decode('utf8'))
        self.assertEqual(report['book_letters_sha256'], hashlib.sha256(book.encode()).hexdigest())
        cipher = probe.source_stream(source)
        for case in report['cases']:
            text = cipher[:-1] if case['drop_terminal_i'] else cipher
            self.assertEqual(case['cipher_max_count'], max(Counter(text).values()))
            pos, width = case['first_attaining_offset'], len(text)
            self.assertEqual(case['minimum_window_max_count'], max(Counter(book[pos:pos + width]).values()))
            # Independent proof: every window's E count is at least this bound;
            # a single witness attains it as the maximum over all 26 letters.
            prefix = [0, *accumulate(c == 'E' for c in book)]
            min_e = min(prefix[i + width] - prefix[i] for i in range(len(book) - width + 1))
            self.assertEqual(min_e, case['minimum_window_max_count'])
            self.assertEqual(case['windows_examined'], len(book) - width + 1)
            self.assertEqual(case['minimum_cipher_symbol_substitutions_required'],
                             max(0, case['minimum_window_max_count'] - case['cipher_max_count']))


if __name__ == '__main__':
    unittest.main()
