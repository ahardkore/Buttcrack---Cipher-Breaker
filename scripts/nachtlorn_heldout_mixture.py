#!/usr/bin/env python3
"""R27: held-out page-wise English/uniform mixture under an unknown substitution.

The mixture is an exploratory marginal model, not plaintext or outlier recovery.
NumPy is an optional research dependency; the source is never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.nachtlorn_book_fullscan import FREQUENCIES  # noqa: E402
from scripts.nachtlorn_strip_counts import parse_rows  # noqa: E402

REPLICATES = 10_000
SEED = 20261102
PAGE1_ROWS = 61


def counts(text: str) -> np.ndarray:
    if not text or any(not 'A' <= c <= 'Z' for c in text):
        raise ValueError('nonempty uppercase ASCII letters required')
    a = np.frombuffer(text.encode('ascii'), dtype=np.uint8) - 65
    return np.bincount(a, minlength=26).astype(np.int64)


def fit_predict(train: np.ndarray, heldout: np.ndarray) -> dict:
    """Vectorized MLE; rows of 26 counts, alphabetical glyph tie-breaking."""
    train, heldout = np.asarray(train), np.asarray(heldout)
    if (train.ndim != 2 or train.shape[1] != 26 or heldout.shape != train.shape
            or not np.issubdtype(train.dtype, np.integer) or not np.issubdtype(heldout.dtype, np.integer)
            or np.any(train < 0) or np.any(heldout < 0) or np.any(train.sum(axis=1) == 0)
            or np.any(heldout.sum(axis=1) == 0)):
        raise ValueError('nonnegative integer matrices with 26 positive-total columns required')
    probs = np.asarray(FREQUENCIES, dtype=np.float64)
    english_order = np.argsort(-probs, kind='stable')
    delta = 26 * probs[english_order] / probs.sum() - 1
    cipher_order = np.argsort(-train, axis=1, kind='stable')
    train_sorted = np.take_along_axis(train, cipher_order, axis=1)
    held_sorted = np.take_along_axis(heldout, cipher_order, axis=1)
    # Concave log likelihood: derivative decreases monotonically in alpha.
    left = np.zeros(len(train), dtype=np.float64)
    right = np.ones(len(train), dtype=np.float64)
    for _ in range(50):
        mid = (left + right) / 2
        derivative = np.sum(train_sorted * delta / (1 + mid[:, None] * delta), axis=1)
        left = np.where(derivative > 0, mid, left)
        right = np.where(derivative > 0, right, mid)
    alpha = (left + right) / 2
    derivative_zero = np.sum(train_sorted * delta, axis=1)
    # Equal counts have mathematically zero derivative; tolerate roundoff.
    alpha = np.where(derivative_zero <= train.sum(axis=1) * 1e-14, 0, alpha)
    alpha = np.where(np.sum(train_sorted * delta / (1 + delta), axis=1) >= 0, 1, alpha)
    weights = np.log1p(alpha[:, None] * delta)
    return {'alpha': alpha, 'train_llr': np.sum(train_sorted * weights, axis=1) / train.sum(axis=1),
            'heldout_llr': np.sum(held_sorted * weights, axis=1) / heldout.sum(axis=1),
            'cipher_order': cipher_order, 'english_order': english_order}


def analyze(raw: bytes) -> dict:
    rows = parse_rows(raw)
    if len(rows) != 146 or any(sum('A' <= c <= 'Z' for c in row) != 60 for row in rows[:145]) or sum('A' <= c <= 'Z' for c in rows[-1]) != 36 or not rows[-1].rstrip().endswith('I'):
        raise ValueError('registered 145 full rows and final 36-letter row ending I required')
    first = ''.join(c for row in rows[:PAGE1_ROWS] for c in row if 'A' <= c <= 'Z')
    second = ''.join(c for row in rows[PAGE1_ROWS:] for c in row if 'A' <= c <= 'Z')
    train, held = counts(first), counts(second)
    actual = fit_predict(train[None, :], held[None, :])
    real_score = float(actual['heldout_llr'][0])
    rng = np.random.default_rng(SEED)
    uniform = np.full(26, 1 / 26)
    n1, n2 = int(train.sum()), int(held.sum())
    null_a_train = rng.multinomial(n1, uniform, size=REPLICATES)
    null_a_held = rng.multinomial(n2, uniform, size=REPLICATES)
    null_a_scores = fit_predict(null_a_train, null_a_held)['heldout_llr']
    pooled = train + held
    null_b_train = rng.multivariate_hypergeometric(pooled, n1, size=REPLICATES)
    null_b_scores = fit_predict(null_b_train, pooled - null_b_train)['heldout_llr']

    def calibration(scores: np.ndarray) -> dict:
        at_least = int(np.count_nonzero(scores >= real_score))
        return {'replicates': REPLICATES, 'at_least_actual': at_least,
                'plus_one_upper_tail_rate': (at_least + 1) / (REPLICATES + 1),
                'null_mean_heldout_llr': float(np.mean(scores))}

    cipher_order = actual['cipher_order'][0]
    english_order = actual['english_order']
    mapping = {chr(65 + int(c)): chr(65 + int(e)) for c, e in zip(cipher_order, english_order)}
    alpha = float(actual['alpha'][0])
    return {'hypothesis': 'R27', 'source_sha256': hashlib.sha256(raw).hexdigest(), 'source_bytes': len(raw),
            'page1_rows': PAGE1_ROWS, 'page1_letters': n1, 'page2_letters': n2,
            'page1_counts_A_to_Z': train.tolist(), 'page2_counts_A_to_Z': held.tolist(),
            'model': 'independent-letter uniform/English-frequency mixture with one unknown fixed bijection',
            'training_selected_cipher_to_english': mapping, 'training_alpha': alpha,
            'training_llr_nats_per_letter': float(actual['train_llr'][0]),
            'heldout_llr_nats_per_letter': real_score,
            'heldout_positive_and_uniform_tail_at_most_001': bool(real_score > 0 and (np.count_nonzero(null_a_scores >= real_score) + 1) / (REPLICATES + 1) <= 0.01),
            'random_generator': 'numpy.random.default_rng PCG64', 'numpy_version': np.__version__, 'seed': SEED,
            'null_uniform': calibration(null_a_scores), 'null_conditional_pooled_counts': calibration(null_b_scores),
            'limits': 'A mixture fit, likelihood ratio, or conditional null is not a recovered key, plaintext, population, final outlier, proof of generator or global significance correction. Model excludes changing substitutions and sparse/local content.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        parser.error('output must not overwrite source')
    try:
        report = analyze(args.path.read_bytes())
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('page1_letters', 'page2_letters', 'training_alpha',
                      'training_llr_nats_per_letter', 'heldout_llr_nats_per_letter', 'null_uniform',
                      'null_conditional_pooled_counts', 'heldout_positive_and_uniform_tail_at_most_001')}))


if __name__ == '__main__':
    main()
