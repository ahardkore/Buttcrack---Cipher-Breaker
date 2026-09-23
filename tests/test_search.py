"""Tests for the search machinery: hill climbing, restarts, parallel workers."""

from __future__ import annotations

import random
import time
import unittest

from buttcrack.ciphers import get
from buttcrack.lang import get_model
from buttcrack.search import (
    climb,
    frequency_seed,
    parallel_restarts,
    restart_search,
    restarts_for,
    swap,
)
from buttcrack.text import A26, keyed_alphabet, letters_only

MODEL = get_model()
PLAINTEXT = (
    "The archive contains the original manuscripts, three of which were lost during the fire of "
    "eighteen ninety two, and the catalogue that described them was destroyed as well, so the "
    "scholars have had to reconstruct the order of the collection from the letters of the "
    "librarians who worked there at the time."
)
SUBSTITUTION = get("substitution")
ALPHABET = keyed_alphabet("ZEBRASCDFGHIJKLMNOPQTUVWXY")


def _worker(payload):
    """Top-level so it can be pickled, exactly like the real cipher workers."""
    value, delay = payload
    time.sleep(delay)
    return (value, value * 2)


class TestHelpers(unittest.TestCase):
    def test_swap_exchanges_two_positions(self):
        self.assertEqual(swap(["A", "B", "C"], 0, 2), ["C", "B", "A"])

    def test_frequency_seed_maps_the_commonest_letter_to_e(self):
        ciphertext = SUBSTITUTION.prepare(SUBSTITUTION.encrypt(PLAINTEXT, ALPHABET))
        seed = frequency_seed(ciphertext)
        self.assertEqual(sorted(seed), sorted(A26))
        commonest = max(set(ciphertext), key=ciphertext.count)
        self.assertEqual(seed[A26.index(commonest)], "E")

    def test_shorter_texts_get_more_restarts(self):
        # The opposite of the naive expectation: long texts converge on the first
        # frequency-seeded climb, short ones have flat landscapes and need many.
        self.assertGreater(restarts_for(100), restarts_for(4000))
        self.assertEqual(restarts_for(1600), restarts_for(4000))
        for length in (1, 20, 150, 600, 100_000):
            with self.subTest(length=length):
                self.assertGreaterEqual(restarts_for(length), 4)
                self.assertLessEqual(restarts_for(length), 64)


class TestClimb(unittest.TestCase):
    def test_climbing_improves_the_fitness(self):
        ciphertext = SUBSTITUTION.prepare(SUBSTITUTION.encrypt(PLAINTEXT, ALPHABET))
        rng = random.Random(1234)
        start = list(A26)
        baseline = MODEL.search_fitness(
            "".join(ciphertext).translate(str.maketrans(A26, "".join(start)))
        )
        key, fit, evals = climb(
            ciphertext,
            MODEL.search_fitness,
            rng=rng,
            start=start,
            max_evals=2000,
        )
        self.assertGreater(fit, baseline)
        self.assertGreater(evals, 1)
        self.assertEqual(sorted(key), sorted(A26))

    def test_climb_stops_at_the_deadline(self):
        ciphertext = SUBSTITUTION.prepare(SUBSTITUTION.encrypt(PLAINTEXT, ALPHABET))
        started = time.time()
        climb(
            ciphertext,
            MODEL.search_fitness,
            rng=random.Random(7),
            max_evals=200_000,
            deadline=time.time() + 0.2,
        )
        self.assertLess(time.time() - started, 3.0)


class TestRestartSearch(unittest.TestCase):
    def test_recovers_a_substitution_key(self):
        from buttcrack.ciphers.substitution import inverse_alphabet

        ciphertext = SUBSTITUTION.prepare(SUBSTITUTION.encrypt(PLAINTEXT, ALPHABET))
        truth = inverse_alphabet(ALPHABET)  # climb keys decrypt, so invert
        key, plain, fit, conf, evals, used = restart_search(
            ciphertext,
            fitness=MODEL.search_fitness,
            confidence=lambda t: MODEL.score(t).confidence,
            apply_key=lambda text, k: text.translate(str.maketrans(A26, "".join(k))),
            restarts=8,
            rng=random.Random(20260923),
            max_evals=9000,
            seeds=[frequency_seed(ciphertext)],
        )
        self.assertEqual(letters_only(plain), letters_only(PLAINTEXT))
        self.assertGreater(conf, 0.86)
        # Letters the ciphertext never exercises are unconstrained -- a message
        # without a J says nothing about where J maps to -- so compare only the
        # positions the text actually pins down.
        for letter in set(ciphertext):
            self.assertEqual(key[A26.index(letter)], truth[A26.index(letter)], letter)
        self.assertGreaterEqual(used, 1)
        self.assertGreater(evals, 0)

    def test_always_takes_at_least_one_shot(self):
        # A time slice that expired before the attack started must not produce
        # nothing: restart 0 is the frequency-seeded climb and is always run.
        ciphertext = SUBSTITUTION.prepare(SUBSTITUTION.encrypt(PLAINTEXT, ALPHABET))
        key, plain, _fit, _conf, _evals, used = restart_search(
            ciphertext,
            fitness=MODEL.search_fitness,
            confidence=lambda t: MODEL.score(t).confidence,
            apply_key=lambda text, k: text.translate(str.maketrans(A26, "".join(k))),
            restarts=8,
            rng=random.Random(1),
            max_evals=9000,
            deadline=time.time() - 1.0,
            seeds=[frequency_seed(ciphertext)],
        )
        self.assertEqual(used, 1)
        self.assertEqual(letters_only(plain), letters_only(PLAINTEXT))
        self.assertEqual(len(key), 26)


class TestParallelRestarts(unittest.TestCase):
    def test_serial_path_runs_every_payload(self):
        payloads = [(i, 0.0) for i in range(4)]
        self.assertEqual(sorted(parallel_restarts(_worker, payloads, 1)), [(i, i * 2) for i in range(4)])

    def test_parallel_path_matches_the_serial_path(self):
        payloads = [(i, 0.01) for i in range(4)]
        serial = sorted(parallel_restarts(_worker, payloads, 1))
        parallel = sorted(parallel_restarts(_worker, payloads, 2))
        self.assertEqual(serial, parallel)

    def test_a_deadline_keeps_the_results_that_arrived(self):
        # One instant payload and one that will never finish in time: the instant
        # one must survive rather than being thrown away with the batch.
        payloads = [(1, 0.0), (2, 5.0)]
        started = time.time()
        results = parallel_restarts(_worker, payloads, 2, deadline=time.time() + 0.5)
        self.assertIn((1, 2), results)
        self.assertLess(time.time() - started, 4.0)

    def test_a_broken_worker_falls_back_to_serial(self):
        def exploding(payload):
            raise RuntimeError("no pool here")

        with self.assertRaises(RuntimeError):
            parallel_restarts(exploding, [(1, 0.0)], 1)


if __name__ == "__main__":
    unittest.main()
