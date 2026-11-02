#!/usr/bin/env python3
"""R26: exhaustive integer upper bound for the registered book-key score."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from decimal import ROUND_CEILING, Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.nachtlorn_book_frequency import ascii_letters, source_stream  # noqa: E402

FREQUENCIES = (8167, 1492, 2782, 4253, 12702, 2228, 2015, 6094, 6966, 153, 772, 4025, 2406,
               6749, 7507, 1929, 95, 5987, 6327, 9056, 2758, 978, 2360, 150, 1974, 74)
SCALE = 1000
TRAIN = 6000


def upper_weights() -> list[int]:
    """Round exact decimal frequency LLRs up and independently verify exp bounds."""
    with localcontext() as ctx:
        ctx.prec = 80
        weights = []
        for f in FREQUENCIES:
            ratio = Decimal(26 * f) / Decimal(sum(FREQUENCIES))
            upper = int((Decimal(SCALE) * ratio.ln()).to_integral_value(rounding=ROUND_CEILING))
            # High precision exp is correctly rounded; a 1e-50 safety margin is
            # far above its rounding error for these small positive arguments.
            if (Decimal(upper) / SCALE).exp() <= ratio + Decimal('1e-50'):
                raise ArithmeticError('failed strict upper bound')
            weights.append(upper)
        return weights


def direct_upper(cipher: str, key: str, weights: list[int]) -> int:
    if not cipher or len(cipher) != len(key) or any(not 'A' <= c <= 'Z' for c in cipher + key) or len(weights) != 26:
        raise ValueError('equal nonempty uppercase segments and 26 weights required')
    return sum(weights[(ord(a) - ord(b)) % 26] for a, b in zip(cipher, key))


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
        scores = [int(s) for s in result.stdout.splitlines()]
        if len(scores) != len(book) - full_length + 1:
            raise ValueError('worker returned wrong score count')
        return scores
    result = json.loads(result.stdout)
    if result['windows'] != len(book) - full_length + 1:
        raise ValueError('worker returned wrong window count')
    position = result['first_maximum_offset']
    if not 0 <= position < result['windows']:
        raise ValueError('worker returned invalid offset')
    direct = direct_upper(training, book[position:position + len(training)], weights)
    if direct != result['maximum_integer_upper_sum']:
        raise ValueError('worker maximum witness failed independent scalar replay')
    return result


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
        book = ascii_letters(raw_book.decode('utf-8'))
        if len(cipher) != 8736:
            raise ValueError('registered full body must contain 8736 letters')
        weights = upper_weights()
        result = run_worker(args.worker, book, cipher[:TRAIN], len(cipher))
    except (OSError, UnicodeError, ValueError, ArithmeticError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    result.update({'hypothesis': 'R26', 'source_sha256': hashlib.sha256(raw).hexdigest(),
                   'book_sha256': hashlib.sha256(raw_book).hexdigest(),
                   'worker_sha256': hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                   'source_letters': len(cipher), 'book_letters': len(book), 'training_letters': TRAIN,
                   'frequency_integer_weights': list(FREQUENCIES), 'upper_integer_weights': weights, 'scale': SCALE,
                   'maximum_mean_upper_bound_nats': result['maximum_integer_upper_sum'] / (SCALE * TRAIN),
                   'all_training_scores_negative': result['maximum_integer_upper_sum'] < 0,
                   'method': 'Every per-letter integer score strictly exceeds the exact natural-log likelihood ratio times scale; worker sums integers exhaustively. Upper bound is not a proof of the English language or a final answer.',
                   'scope': 'Only full-body-eligible contiguous book starts, first 6000 letters, fixed A0 C-K, fixed English monogram profile. Negative score does not exclude short payloads or non-English/intermediate plaintext.'})
    # Check against the floating implementation's profile, independently of FFT.
    result['witness_scalar_float_llr_mean'] = math.fsum(
        math.log(26 * FREQUENCIES[(ord(c) - ord(k)) % 26] / sum(FREQUENCIES))
        for c, k in zip(cipher[:TRAIN], book[result['first_maximum_offset']:result['first_maximum_offset'] + TRAIN])
    ) / TRAIN
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('windows', 'maximum_integer_upper_sum', 'first_maximum_offset',
                                              'maximum_mean_upper_bound_nats', 'all_training_scores_negative')}))


if __name__ == '__main__':
    main()
