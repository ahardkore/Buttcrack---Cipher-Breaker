from __future__ import annotations

import hashlib
import itertools
import json
import math
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None

if np is not None:
    from scripts import nachtlorn_heldout_mixture as model


@unittest.skipIf(np is None, 'optional numpy research dependency missing')
class HeldoutMixtureTests(unittest.TestCase):
    def test_order_and_alpha_against_permutation_and_grid_oracles(self):
        train = np.array([[70, 48, 25, 12] + [3] * 22], dtype=np.int64)
        held = np.array([[45, 23, 17, 8] + [2] * 22], dtype=np.int64)
        result = model.fit_predict(train, held)
        probs = np.array(model.FREQUENCIES) / sum(model.FREQUENCIES)
        alpha = result['alpha'][0]
        order, english = result['cipher_order'][0], result['english_order']
        q = (1 - alpha) / 26 + alpha * probs[english]
        ll = float(np.sum(train[0, order] * np.log(26 * q)))
        for perm in itertools.permutations(range(4)):
            alternate = order.copy()
            alternate[:4] = order[list(perm)]
            candidate = float(np.sum(train[0, alternate] * np.log(26 * q)))
            self.assertGreaterEqual(ll + 1e-9, candidate)
        grid_best = max(float(np.sum(train[0, order] * np.log1p(a * (26 * probs[english] - 1))))
                        for a in np.linspace(0, 1, 1001))
        self.assertGreaterEqual(ll + 1e-9, grid_best)
        self.assertAlmostEqual(result['heldout_llr'][0],
                               float(np.sum(held[0, order] * np.log(26 * q)) / held.sum()), places=12)

    def test_alpha_zero_and_alphabetical_tie(self):
        uniform = np.full((1, 26), 10, dtype=np.int64)
        result = model.fit_predict(uniform, uniform)
        self.assertEqual(result['alpha'][0], 0)
        self.assertEqual(result['heldout_llr'][0], 0)
        self.assertEqual(result['cipher_order'][0].tolist(), list(range(26)))

    def test_planted_mixture_predicts_independent_page(self):
        rng = np.random.default_rng(701)
        english = np.array(model.FREQUENCIES) / sum(model.FREQUENCIES)
        q = 0.6 * english + 0.4 / 26
        permutation = rng.permutation(26)
        q = q[permutation]
        first = rng.multinomial(10000, q)[None, :]
        second = rng.multinomial(10000, q)[None, :]
        r = model.fit_predict(first, second)
        self.assertGreater(r['heldout_llr'][0], 0.05)
        self.assertGreater(r['alpha'][0], 0.4)
        self.assertLess(r['alpha'][0], 0.8)

    def test_random_generators_reproducible_and_conditional_totals(self):
        pooled = np.arange(1, 27, dtype=np.int64)
        a = np.random.default_rng(model.SEED).multivariate_hypergeometric(pooled, 200, size=30)
        b = np.random.default_rng(model.SEED).multivariate_hypergeometric(pooled, 200, size=30)
        np.testing.assert_array_equal(a, b)
        self.assertTrue(np.all(a.sum(axis=1) == 200))
        self.assertTrue(np.all(a <= pooled))
        np.testing.assert_array_equal(a + (pooled - a), np.broadcast_to(pooled, a.shape))

    def test_invalid_and_overwrite_guard(self):
        for v in ('', 'ABC ', 'abc'):
            with self.assertRaises(ValueError):
                model.counts(v)
        for a, b in ((np.zeros((1, 26), dtype=int), np.ones((1, 26), dtype=int)),
                     (np.ones((1, 25), dtype=int), np.ones((1, 25), dtype=int)),
                     (np.ones((1, 26)), np.ones((1, 26)))):
            with self.assertRaises(ValueError):
                model.fit_predict(a, b)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'source'
            p.write_text('unchanged')
            with self.assertRaises(SystemExit):
                model.main([str(p), '--output', str(p)])
            self.assertEqual(p.read_text(), 'unchanged')

    def test_recorded_page_counts_and_predictions_replayed(self):
        root = Path(__file__).resolve().parents[1]
        result = root / 'docs/data/nachtlorn-heldout-mixture-results.json'
        if not result.exists():
            self.skipTest('actual source experiment not yet recorded')
        report = json.loads(result.read_text())
        raw = (root / 'docs/data/nachtlorn-transcript.txt').read_bytes()
        self.assertEqual(report['source_sha256'], hashlib.sha256(raw).hexdigest())
        rows = raw.decode('ascii').splitlines()[8:]
        def histogram(rows):
            result = [0] * 26
            for row in rows:
                for c in row:
                    if 'A' <= c <= 'Z':
                        result[ord(c) - 65] += 1
            return result
        first, second = histogram(rows[:61]), histogram(rows[61:])
        self.assertEqual((sum(first), sum(second)), (3660, 5076))
        self.assertEqual((first, second), (report['page1_counts_A_to_Z'], report['page2_counts_A_to_Z']))
        mapping, alpha = report['training_selected_cipher_to_english'], report['training_alpha']
        self.assertEqual(set(mapping), set('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
        self.assertEqual(set(mapping.values()), set('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
        weights = [math.log1p(alpha * (26 * model.FREQUENCIES[ord(mapping[chr(65 + i)]) - 65]
                                        / sum(model.FREQUENCIES) - 1)) for i in range(26)]
        self.assertAlmostEqual(sum(n * w for n, w in zip(first, weights)) / sum(first),
                               report['training_llr_nats_per_letter'], places=12)
        self.assertAlmostEqual(sum(n * w for n, w in zip(second, weights)) / sum(second),
                               report['heldout_llr_nats_per_letter'], places=12)
        for key in ('null_uniform', 'null_conditional_pooled_counts'):
            null = report[key]
            self.assertEqual(null['replicates'], 10000)
            self.assertEqual(null['plus_one_upper_tail_rate'], (null['at_least_actual'] + 1) / 10001)


if __name__ == '__main__':
    unittest.main()
