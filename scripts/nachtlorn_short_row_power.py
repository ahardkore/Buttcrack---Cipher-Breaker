#!/usr/bin/env python3
"""R30: synthetic-only power gate for a short book-running-key search."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.nachtlorn_book_frequency import ascii_letters  # noqa: E402
from scripts.nachtlorn_book_fullscan import analyze, decrypt  # noqa: E402

STARTS = (0, 14911, 62017, 118913, 208117, 320113, 510019, 810017)
PHRASES = (
    'The lantern burned low while rain fell softly on the window.',
    'Beyond the river a small village lay beneath the quiet hills.',
    'She placed the old letter carefully inside the wooden box.',
    'At dawn the birds were singing in the garden behind the house.',
    'The silver boat moved slowly across the water in the morning.',
    'He closed the door and listened to the wind among the trees.',
    'A candle on the table cast a shadow along the empty wall.',
    'The children waited patiently until the train had stopped.',
)
LENGTH = 36
TRAIN = 25


def make_control(book: str, phrase: str, offset: int) -> tuple[str, str]:
    plaintext = ascii_letters(phrase)[:LENGTH]
    if len(plaintext) != LENGTH or type(offset) is not int or offset < 0 or offset + LENGTH > len(book):
        raise ValueError('a 36-letter synthetic phrase and in-range book offset required')
    key = book[offset:offset + LENGTH]
    if any(not 'A' <= c <= 'Z' for c in key):
        raise ValueError('uppercase book required')
    cipher = ''.join(chr(65 + (ord(p) + ord(k) - 130) % 26) for p, k in zip(plaintext, key))
    return plaintext, cipher


def run_control(book: str, phrase: str, offset: int) -> dict:
    plain, cipher = make_control(book, phrase, offset)
    fit = analyze(book, cipher, TRAIN)
    chosen = fit['training_selected_book_offset']
    reconstructed = decrypt(cipher, book[chosen:chosen + LENGTH])
    return {'synthetic': True, 'planted_book_offset': offset, 'selected_book_offset': chosen,
            'eligible_offsets': fit['offsets_scored'], 'training_llr_nats_per_letter': fit['training_llr_nats_per_letter'],
            'heldout_llr_nats_per_letter': fit['heldout_llr_nats_per_letter'],
            'heldout_screen_pass': fit['heldout_screen_pass'], 'exact_plaintext_recovered': reconstructed == plain,
            'planted_plaintext_sha256': hashlib.sha256(plain.encode()).hexdigest(),
            'reconstructed_sha256': hashlib.sha256(reconstructed.encode()).hexdigest(),
            'fft_direct_absolute_error': fit['fft_direct_absolute_error']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--book', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.book.resolve() == args.output.resolve():
        parser.error('output must not overwrite book')
    try:
        raw_book = args.book.read_bytes()
        book = ascii_letters(raw_book.decode('utf8'))
        results = [run_control(book, phrase, start) for phrase, start in zip(PHRASES, STARTS)]
    except (OSError, UnicodeError, ValueError, ArithmeticError) as error:
        parser.error(str(error))
    gate = all(r['exact_plaintext_recovered'] and r['heldout_screen_pass'] for r in results)
    report = {'hypothesis': 'R30', 'book_sha256': hashlib.sha256(raw_book).hexdigest(),
              'book_letters': len(book), 'synthetic_only': True, 'controls': results,
              'control_gate_passed': gate,
              'actual_source_search_authorized': gate,
              'actual_source_search_performed': False,
              'scope': 'Synthetic sensitivity only. Failure does not exclude a real short message or other selection methods; a pass would not prove a final outlier.'}
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'controls': len(results), 'exact_recoveries': sum(r['exact_plaintext_recovered'] for r in results),
                      'heldout_passes': sum(r['heldout_screen_pass'] for r in results),
                      'gate_passed': gate, 'actual_source_search_performed': False}))


if __name__ == '__main__':
    main()
