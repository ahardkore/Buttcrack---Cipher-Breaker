#!/usr/bin/env python3
"""Necessary frequency invariant for a contiguous book excerpt as plaintext.

An arbitrary position transposition and fixed bijective letter substitution
preserve the multiset of letter counts. No guessed key or words are used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROW = re.compile(r' *[A-Z]+(?: +[A-Z]+)* *')


def ascii_letters(text: str) -> str:
    """Keep original ASCII letters only; do not expand non-ASCII on uppercasing."""
    return ''.join(c.upper() for c in text if 'A' <= c <= 'Z' or 'a' <= c <= 'z')


def min_window_maximum(text: str, width: int) -> dict:
    if not re.fullmatch(r'[A-Z]+', text) or type(width) is not int or not 1 <= width <= len(text):
        raise ValueError('uppercase book letters and valid positive window length required')
    counts = [0] * 26
    values = [ord(c) - 65 for c in text]
    for n in values[:width]:
        counts[n] += 1
    minimum, first, ties = max(counts), 0, 1
    for end in range(width, len(values)):
        counts[values[end - width]] -= 1
        counts[values[end]] += 1
        maximum = max(counts)
        if maximum < minimum:
            minimum, first, ties = maximum, end - width + 1, 1
        elif maximum == minimum:
            ties += 1
    return {'minimum_window_max_count': minimum, 'first_attaining_offset': first,
            'attaining_windows': ties, 'windows_examined': len(text) - width + 1}


def compare(book: str, ciphertext: str) -> dict:
    if not re.fullmatch(r'[A-Z]+', ciphertext):
        raise ValueError('uppercase ciphertext required')
    target = max(Counter(ciphertext).values())
    result = min_window_maximum(book, len(ciphertext))
    gap = max(0, result['minimum_window_max_count'] - target)
    return {'letters': len(ciphertext), 'cipher_max_count': target, **result,
            'minimum_cipher_symbol_substitutions_required': gap,
            'all_contiguous_windows_excluded_by_max_count': gap > 0}


def source_stream(raw: bytes) -> str:
    rows = raw.decode('ascii').splitlines()[8:]
    if not rows or any(not ROW.fullmatch(row) for row in rows):
        raise ValueError('expected ASCII body after eight-line preamble')
    stream = ''.join(c for row in rows for c in row if 'A' <= c <= 'Z')
    if not stream.endswith('I'):
        raise ValueError('registered terminal-I comparison requires final I')
    return stream


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--book', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.path.resolve(), args.book.resolve()):
        parser.error('output must not overwrite either source')
    try:
        raw = args.path.read_bytes()
        book_raw = args.book.read_bytes()
        cipher = source_stream(raw)
        book = ascii_letters(book_raw.decode('utf-8'))
        full = compare(book, cipher)
        drop = compare(book, cipher[:-1])
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    report = {'hypothesis': 'R24', 'source_sha256': hashlib.sha256(raw).hexdigest(), 'source_bytes': len(raw),
              'book_sha256': hashlib.sha256(book_raw).hexdigest(), 'book_bytes': len(book_raw),
              'book_normalization': 'Keep original ASCII A-Z/a-z; uppercase after filtering. Whole pinned file, including Gutenberg material.',
              'book_letters': len(book), 'book_letters_sha256': hashlib.sha256(book.encode()).hexdigest(),
              'cases': [{'drop_terminal_i': False, **full}, {'drop_terminal_i': True, **drop}],
              'scope': 'Necessary count invariant only: all contiguous book windows under any fixed bijection and arbitrary transposition. Not a key-recovery, a general cipher exclusion, or an identified outlier.'}
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report['cases']))


if __name__ == '__main__':
    main()
