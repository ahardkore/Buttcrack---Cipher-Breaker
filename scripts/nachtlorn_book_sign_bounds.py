#!/usr/bin/env python3
"""R29: exact running-key training bounds for K-C and C+K."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.nachtlorn_book_exact_bound import FREQUENCIES, SCALE, TRAIN, upper_weights  # noqa: E402
from scripts.nachtlorn_book_frequency import ascii_letters, source_stream  # noqa: E402

MODES = ('K-C', 'C+K')


def score(cipher: str, key: str, mode: str, weights: list[int]) -> int:
    if (not cipher or len(cipher) != len(key) or mode not in MODES or len(weights) != 26
            or any(not 'A' <= c <= 'Z' for c in cipher + key)):
        raise ValueError('equal nonempty uppercase segments, registered mode and 26 weights required')
    return sum(weights[((ord(k) - ord(c)) if mode == 'K-C' else (ord(c) + ord(k) - 130)) % 26]
               for c, k in zip(cipher, key))


def run_worker(worker: Path, book: str, training: str, full_length: int, *, all_scores: bool = False):
    if not book or not training or any(not 'A' <= c <= 'Z' for c in book + training):
        raise ValueError('uppercase book and training letters required')
    if type(full_length) is not int or not len(training) <= full_length <= len(book):
        raise ValueError('full ciphertext must fit and contain training')
    weights = upper_weights()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)
        (path / 'book').write_text(book, encoding='ascii')
        (path / 'training').write_text(training, encoding='ascii')
        command = [str(worker.resolve()), str(path / 'book'), str(path / 'training')]
        if all_scores:
            command.append('--all')
        result = subprocess.run(command, input=f"{full_length}\n{' '.join(map(str, weights))}\n",
                                capture_output=True, text=True, check=True, timeout=600)
    if all_scores:
        values = [tuple(map(int, line.split())) for line in result.stdout.splitlines()]
        if len(values) != len(book) - full_length + 1 or any(len(v) != 2 for v in values):
            raise ValueError('invalid worker score count')
        return values
    report = json.loads(result.stdout)
    if report['windows'] != len(book) - full_length + 1 or [r['operation'] for r in report['models']] != list(MODES):
        raise ValueError('worker metadata mismatch')
    for r in report['models']:
        start = r['first_maximum_offset']
        if not 0 <= start < report['windows'] or r['maximum_integer_upper_sum'] != score(training, book[start:start + len(training)], r['operation'], weights):
            raise ValueError('worker maximum witness fails scalar replay')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--book', type=Path, required=True)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.path.resolve(), args.book.resolve(), args.worker.resolve()):
        parser.error('output must not overwrite inputs or worker')
    try:
        raw, raw_book = args.path.read_bytes(), args.book.read_bytes()
        cipher = source_stream(raw)
        book = ascii_letters(raw_book.decode('utf8'))
        if len(cipher) != 8736:
            raise ValueError('registered full body must contain 8736 letters')
        result = run_worker(args.worker, book, cipher[:TRAIN], len(cipher))
    except (OSError, UnicodeError, ValueError, ArithmeticError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    for r in result['models']:
        start = r['first_maximum_offset']
        segment = book[start:start + TRAIN]
        r['maximum_mean_upper_bound_nats'] = r['maximum_integer_upper_sum'] / (SCALE * TRAIN)
        r['all_training_scores_negative'] = r['maximum_integer_upper_sum'] < 0
        r['witness_scalar_float_llr_mean'] = math.fsum(
            math.log(26 * FREQUENCIES[((ord(k) - ord(c)) if r['operation'] == 'K-C' else (ord(c) + ord(k) - 130)) % 26] / sum(FREQUENCIES))
            for c, k in zip(cipher[:TRAIN], segment)) / TRAIN
    result.update({'hypothesis': 'R29', 'source_sha256': hashlib.sha256(raw).hexdigest(),
                   'book_sha256': hashlib.sha256(raw_book).hexdigest(), 'worker_sha256': hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                   'source_letters': len(cipher), 'book_letters': len(book), 'training_letters': TRAIN,
                   'upper_integer_weights': upper_weights(), 'scale': SCALE,
                   'scope': 'Only the two listed arithmetic operations, full-body-eligible contiguous starts and first 6000 letters. Negative upper scores do not rule out short payloads or other models.'})
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['models']))


if __name__ == '__main__':
    main()
