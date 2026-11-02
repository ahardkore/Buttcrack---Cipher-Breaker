#!/usr/bin/env python3
"""R25: train on 6000 symbols, then check held-out running-key plaintext.

Numerical FFT scores rank every eligible Ulysses start for one C-K model;
no English fragment is used to select the result. NumPy is optional research
infrastructure and is not an application dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.nachtlorn_book_frequency import ascii_letters, source_stream  # noqa: E402

# Fixed standard English letter-frequency profile, normalized before scoring.
FREQUENCIES = (8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966, 0.153, 0.772, 4.025, 2.406,
               6.749, 7.507, 1.929, 0.095, 5.987, 6.327, 9.056, 2.758, 0.978, 2.360, 0.150, 1.974, 0.074)
TOTAL = sum(FREQUENCIES)
WEIGHTS = tuple(math.log(26 * p / TOTAL) for p in FREQUENCIES)
THRESHOLD = 0.10
TRAIN = 6000


def as_numbers(text: str) -> np.ndarray:
    if not text or any(not 'A' <= c <= 'Z' for c in text):
        raise ValueError('nonempty ASCII uppercase alphabet required')
    return np.frombuffer(text.encode('ascii'), dtype=np.uint8) - 65


def decrypt(cipher: str, key: str) -> str:
    c, k = as_numbers(cipher), as_numbers(key)
    if len(c) != len(k):
        raise ValueError('cipher and key must be equal length')
    values = (c.astype(np.int16) - k.astype(np.int16)) % 26 + 65
    return values.astype(np.uint8).tobytes().decode('ascii')


def direct_score(cipher: str, key: str) -> float:
    text = decrypt(cipher, key)
    return math.fsum(WEIGHTS[ord(c) - 65] for c in text)


def fft_scores(book: str, train_cipher: str, full_length: int) -> np.ndarray:
    """Return training score sums for starts with room for the full ciphertext."""
    key = as_numbers(book)
    train = as_numbers(train_cipher)
    if type(full_length) is not int or not len(train) <= full_length <= len(key):
        raise ValueError('full length must contain the training prefix and fit in book')
    convolution_length = len(key) + len(train) - 1
    nfft = 1 << (convolution_length - 1).bit_length()
    valid = len(key) - full_length + 1
    totals = np.zeros(valid, dtype=np.float64)
    weights = np.asarray(WEIGHTS)
    for symbol in np.unique(train):
        # score for a training ciphertext glyph versus each running-key glyph.
        weight_by_key = weights[(int(symbol) - np.arange(26)) % 26]
        book_weights = weight_by_key[key]
        reversed_mask = (train[::-1] == symbol).astype(np.float64)
        corr = np.fft.irfft(np.fft.rfft(book_weights, nfft) * np.fft.rfft(reversed_mask, nfft), nfft)
        totals += corr[len(train) - 1:len(train) - 1 + valid]
    return totals


def analyze(book: str, cipher: str, train_length: int = TRAIN) -> dict:
    as_numbers(cipher)
    if type(train_length) is not int or not 1 <= train_length < len(cipher):
        raise ValueError('nonempty training and held-out segments required')
    scores = fft_scores(book, cipher[:train_length], len(cipher))
    # Audit all candidates numerically close to the FFT maximum, then use
    # independently evaluated scalar scores for their final order.
    fft_max = float(scores.max())
    near = np.flatnonzero(scores >= fft_max - 1e-5)
    rescored = [(direct_score(cipher[:train_length], book[int(i):int(i) + train_length]), int(i)) for i in near]
    training, start = min(rescored, key=lambda item: (-item[0], item[1]))
    delta = abs(training - float(scores[start]))
    if delta > 1e-5:
        raise ArithmeticError('FFT maximum fails direct score check')
    recovered = decrypt(cipher, book[start:start + len(cipher)])
    heldout = math.fsum(WEIGHTS[ord(c) - 65] for c in recovered[train_length:]) / (len(cipher) - train_length)
    result = {'model': 'P=(C-K) mod 26; A0; contiguous forward book, full body',
              'offsets_scored': int(len(scores)), 'training_letters': train_length,
              'heldout_letters': len(cipher) - train_length, 'training_selected_book_offset': start,
              'training_llr_nats_per_letter': training / train_length,
              'fft_score_sum': float(scores[start]), 'direct_score_sum': training,
              'fft_direct_absolute_error': delta, 'near_tied_offsets_rescored': int(len(near)),
              'heldout_llr_nats_per_letter': heldout, 'heldout_threshold_nats': THRESHOLD,
              'heldout_screen_pass': heldout >= THRESHOLD,
              'decoded_sha256': hashlib.sha256(recovered.encode()).hexdigest(),
              'warning': 'Screen is not a solution or an outlier rule. A failed chosen candidate does not exclude all other offsets or a short embedded message; numerical FFT ranking is not a formal exact certificate.'}
    if result['heldout_screen_pass']:
        result['decoded_preview'] = recovered[:160]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--book', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.path.resolve(), args.book.resolve()):
        parser.error('output must not overwrite inputs')
    try:
        raw, raw_book = args.path.read_bytes(), args.book.read_bytes()
        cipher = source_stream(raw)
        book = ascii_letters(raw_book.decode('utf-8'))
        report = analyze(book, cipher)
    except (OSError, UnicodeError, ValueError, ArithmeticError) as error:
        parser.error(str(error))
    report.update({'hypothesis': 'R25', 'numpy_version': np.__version__,
                   'source_sha256': hashlib.sha256(raw).hexdigest(), 'book_sha256': hashlib.sha256(raw_book).hexdigest(),
                   'book_normalization': 'whole pinned file; original ASCII letters only, uppercased',
                   'book_letters': len(book), 'source_letters': len(cipher),
                   'weights': list(WEIGHTS)})
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('offsets_scored', 'training_selected_book_offset',
                       'training_llr_nats_per_letter', 'heldout_llr_nats_per_letter', 'heldout_screen_pass')}))


if __name__ == '__main__':
    main()
