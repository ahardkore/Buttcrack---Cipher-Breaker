"""Tests for the self-rotating alphabet (Chaocipher-style) cipher.

The cipher is two mixed alphabets with the bottom row rotating to the front
after every letter, which collapses to a running sum::

    alpha(c_k) = alpha(c_{k-1}) + T.index(p_k)

so these tests pin down both faces of it:

* the cipher itself -- the author's own worked example (``THAT`` -> ``GZZG``),
  every key spelling, round trips, and the running-sum identity checked against
  an independent implementation of the definition;
* the attacks -- the crib path, which is linear algebra over Z_26 and exact
  (fast suite), and the ciphertext-only circulant fit, which needs thousands of
  letters and is therefore slow-suite only.

The ciphertext-only threshold is a *documented* property of this cipher, not a
shortcoming of the search: at a few hundred letters the transition statistic is
inside the sampling noise, which is exactly why the 409-letter challenge text
needs a crib.
"""

from __future__ import annotations

import os
import random
import unittest

from buttcrack.ciphers import ALL_CIPHERS, get, try_get
from buttcrack.ciphers.base import CrackContext, Family
from buttcrack.ciphers.rotating import (
    DEFAULT_KEY,
    RotatingAlphabet,
    parse_key,
    random_key,
)
from buttcrack.lang import get_model
from buttcrack.text import letters_only

SLOW = os.environ.get("BUTTCRACK_SLOW") == "1"

PROSE = (
    "The railway station at Ashford was crowded with travellers waiting for the delayed "
    "express and the station master walked up and down the platform with his hands behind "
    "his back muttering about the weather and the coal shortage while a young woman in a "
    "grey coat stood near the book stall reading a letter that she had just received and "
    "the porter carried her trunk along the platform towards the guard's van at the rear."
)

MODEL = get_model()

#: The author's example: natural top row, reversed bottom row.
EXAMPLE_KEY = DEFAULT_KEY


def ctx(**hints) -> CrackContext:
    return CrackContext.create(model=MODEL, budget=20.0, workers=2, hints=hints)


class TestRoundTrips(unittest.TestCase):
    def test_example_from_the_published_description(self):
        cipher = get("rotating")
        self.assertEqual(cipher.encrypt("THAT", EXAMPLE_KEY), "GZZG")

    def test_registry_entry(self):
        cipher = get("rotating")
        self.assertIsInstance(cipher, RotatingAlphabet)
        self.assertEqual(cipher.info.family, Family.WHEEL)
        self.assertIn(cipher, ALL_CIPHERS)
        self.assertIs(try_get("chaocipher"), cipher)
        self.assertIs(try_get("rotating_alphabet"), cipher)

    def test_round_trips_with_random_keys(self):
        cipher = get("rotating")
        rng = random.Random(20261013)
        for _ in range(5):
            key = random_key(rng)
            self.assertEqual(cipher.decrypt(cipher.encrypt(PROSE, key), key), PROSE.upper())

    def test_key_spellings_agree(self):
        cipher = get("rotating")
        top, bottom = parse_key(EXAMPLE_KEY)
        spellings = [
            f"{top}|{bottom}",
            f"{top},{bottom}",
            f"{top}{bottom}",
            (top, bottom),
        ]
        first = cipher.encrypt(PROSE, spellings[0])
        for spelling in spellings[1:]:
            self.assertEqual(cipher.encrypt(PROSE, spelling), first)

    def test_malformed_keys_are_rejected(self):
        cipher = get("rotating")
        for bad in ("ABC|DEF", "ABCDEFGHIJKLMNOPQRSTUVWXYZ|ABCDEFGHIJKLMNOPQRSTUVWXYA", "nonsense"):
            with self.assertRaises(ValueError):
                cipher.encrypt("TEST", bad)

    def test_running_sum_identity(self):
        """``alpha(c_k) - alpha(c_{k-1}) = T.index(p_k)`` -- the whole attack surface."""
        cipher = get("rotating")
        rng = random.Random(5)
        top, bottom = parse_key(random_key(rng))
        plaintext = letters_only(PROSE, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        ciphertext = cipher.encrypt(plaintext, f"{top}|{bottom}")
        alpha = {ch: bottom.index(ch) for ch in bottom}
        previous = 0
        for index, (c, p) in enumerate(zip(ciphertext, plaintext)):
            value = alpha[c]
            difference = (value - previous) % 26
            self.assertEqual(difference, top.index(p), f"letter {index}")
            previous = value

    def test_rotating_the_necklace_rotates_the_ciphertext(self):
        """The necklace is what matters: rotating B moves every output r positions along it.

        The sender's key and the recovered one can therefore differ by exactly
        this rotation -- a recovered key is a representative of the class, and it
        still decrypts the message and re-encrypts it to the same ciphertext.
        """
        cipher = get("rotating")
        top, bottom = parse_key(EXAMPLE_KEY)
        radius = 7
        rotated = bottom[radius:] + bottom[:radius]
        plaintext = letters_only(PROSE, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        first = cipher.encrypt(plaintext, f"{top}|{bottom}")
        second = cipher.encrypt(plaintext, f"{top}|{rotated}")
        expected = "".join(bottom[(bottom.index(ch) + radius) % 26] for ch in first)
        self.assertEqual(second, expected)


class TestLikelihood(unittest.TestCase):
    def test_flat_text_with_peaked_differences_scores_positive(self):
        cipher = get("rotating")
        long_text = letters_only(PROSE * 6, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        ciphertext = cipher.encrypt(long_text, EXAMPLE_KEY)
        self.assertGreater(cipher.likelihood(ciphertext, ctx()), 0.3)

    def test_prose_does_not_claim_the_running_sum_shape(self):
        cipher = get("rotating")
        long_text = letters_only(PROSE * 6, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self.assertEqual(cipher.likelihood(long_text, ctx()), 0.0)

    def test_short_text_says_nothing(self):
        cipher = get("rotating")
        self.assertEqual(cipher.likelihood("SHORTTEXT", ctx()), 0.0)


class TestCribAttack(unittest.TestCase):
    """Known plaintext is the decisive path: interval sums leave no freedom."""

    def setUp(self):
        self.cipher = get("rotating")
        self.rng = random.Random(31337)
        self.key = random_key(self.rng)
        self.plaintext = letters_only(PROSE * 3, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")[:900]
        self.ciphertext = self.cipher.encrypt(self.plaintext, self.key)

    def test_a_crib_recovers_the_plaintext_exactly(self):
        hits = list(self.cipher.crack(self.ciphertext, ctx(crib=self.plaintext[:200])))
        self.assertTrue(hits, "the crib attack produced nothing")
        best = max(hits, key=lambda h: h.fitness)
        # The first letter is the message's start offset: it is the one letter
        # ciphertext-only cryptanalysis cannot reach, crib or no crib.
        self.assertEqual(best.plaintext[1:], self.plaintext[1:])
        self.assertEqual(self.cipher.encrypt(best.plaintext, best.key), self.ciphertext)

    def test_a_mid_message_crib_works_too(self):
        hits = list(self.cipher.crack(self.ciphertext, ctx(crib=self.plaintext[300:600])))
        self.assertTrue(hits)
        best = max(hits, key=lambda h: h.fitness)
        # A crib that starts mid-message cannot recover the letter before it
        # (that is the start-offset letter again), so compare from the second.
        self.assertEqual(best.plaintext[1:], self.plaintext[301:])

    def test_a_wrong_crib_is_not_reported_as_a_solution(self):
        wrong = letters_only(
            "The catalogue of the collection was destroyed in the fire and the scholars "
            "have had to reconstruct the order from the surviving correspondence",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        )[:200]
        hits = list(self.cipher.crack(self.ciphertext, ctx(crib=wrong)))
        for hit in hits:
            self.assertLess(hit.fitness, -4.6, "a wrong crib must not grade as language")


class TestShortMessages(unittest.TestCase):
    def test_a_short_message_is_honestly_out_of_reach(self):
        """409 letters is inside the noise: nothing may claim to solve it.

        This is the boundary the user's own challenge text sits on, so it is
        worth a test rather than a footnote: below the threshold the cipher is
        unbroken, and a candidate that graded as English would be a false alarm.
        """
        cipher = get("rotating")
        rng = random.Random(409)
        key = random_key(rng)
        plaintext = letters_only(PROSE * 2, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")[:409]
        ciphertext = cipher.encrypt(plaintext, key)
        budget = CrackContext.create(model=MODEL, budget=20.0, workers=2)
        for hit in cipher.crack(ciphertext, budget):
            self.assertLess(
                hit.fitness,
                -4.6,
                "409 letters is below the information threshold; a 'solve' would be a lie",
            )


@unittest.skipUnless(SLOW, "the ciphertext-only attack is a multi-thousand-letter search")
class TestCiphertextOnlySlow(unittest.TestCase):
    def test_long_message_falls_to_the_circulant_fit(self):
        cipher = get("rotating")
        rng = random.Random(99)
        key = random_key(rng)
        corpus = letters_only(
            open("examples/english_samples.txt", encoding="utf-8").read() * 5, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        )
        plaintext = corpus[:8000]
        ciphertext = cipher.encrypt(plaintext, key)
        hits = [
            h
            for h in cipher.crack(ciphertext, ctx())
            if "ciphertext" in str(h.notes.get("method"))
        ]
        self.assertTrue(hits, "the statistical attack produced nothing")
        best = max(hits, key=lambda h: h.fitness)
        self.assertGreater(best.fitness, -4.6, "the recovered reading should grade as English")
        self.assertEqual(best.plaintext[1:], plaintext[1:])


if __name__ == "__main__":
    unittest.main()
