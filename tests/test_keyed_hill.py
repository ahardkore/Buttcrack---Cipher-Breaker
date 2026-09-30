"""Tests for the keyed-alphabet Hill attack (Hill behind a Quagmire III).

The cipher this covers is the shape of the Paradigm Kryptos CTF's PK7:
a Quagmire III of period 6 followed by a 3x3 Hill matrix, both doing their
arithmetic in the KRYPTOS alphabet's index space rather than in A-Z.  Two
properties are worth pinning down, because losing either one silently turns the
attack back into noise:

* the arithmetic happens in *keyed* indices (``A`` is 7 in the Kryptos
  alphabet, not 0), and
* rows are scored with one shift per *phase*, so the Quagmire's
  position-dependent constant cannot smear the histogram a row is judged on.

The PK7 case is also a regression test against the repository's own corpus: the
ciphertext is the published one and the recovered key re-encrypts to it exactly.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from buttcrack.ciphers import get
from buttcrack.ciphers.base import CrackContext
from buttcrack.detect import _block_repeat_tells, identify
from buttcrack.lang import get_model
from buttcrack.text import letters_only

ROOT = Path(__file__).resolve().parent.parent
MODEL = get_model()

#: Paradigm Kryptos PK7, as published.
PK7 = (
    "FNRHTKRHSEDEJMBOWBDSCSDDXLICXULMBYQXWTGUIVNDYZBEQLVHFFFIDAKDCCJKWGOOUESCYELYMRAKIUJ"
    "CUSEAXUQTYKOBVYDYMRBYWOTQEESCQSMDYDQJNPSWRSUOFMFJDYXSHCXNHVJVBYMZOZOATHTEOVLOQWZITH"
    "TEAFMKGLASTBZRDMFRJPKWJOXZXPJCBOVAZEPKAEJPPSIUJODXTXERWTLTTYMRENBJGTNMLBDJMYJDDLRCX"
    "CQCHYMJMHBEOLXEUFNJKBPRSHTEYXB"
)
PK7_PLAINTEXT = (
    "THREEWEEKSINWERISEBEFORETHESUNANDEACHNEEDLEISDONEBYNOONTHEWHITESMITHSHOWSMEHISTECHNI"
    "QUEFORPURIFYINGHISMETALBEFOREDRAWINGITINTOAFINEWIREHEHASMEREPEATTHESAMESTEPFOURTIMES"
    "WITHSLIGHTVARIATIONSSTILLMYHANDFALTERSIAMPATIENTBUTIKNOWTHISISNOTMYCALLINGIHAVEMADEP"
    "EACEWITHITANDWILLGOHOMESOON"
)
PK7_KEY = {"matrix": "ALCHEMIST", "key": "ANNEAL", "alphabet": "kryptos"}

PROSE = (
    "The apprentice kept a diary of the workshop, recording the temper of the metal and "
    "the colour of the coals each morning, because the master never wrote anything down "
    "and expected every lesson to be remembered exactly as it had been given to him."
)


def ctx(budget: float = 20.0, **hints) -> CrackContext:
    return CrackContext.create(model=MODEL, budget=budget, workers=1, hints=hints)


class TestKeyedHillCipher(unittest.TestCase):
    """The cipher itself: keyed indices, and the Quagmire layer in front."""

    def setUp(self) -> None:
        self.cipher = get("keyed_hill")

    def test_round_trip(self):
        plain = letters_only(PROSE).upper()
        cipher = self.cipher.encrypt(plain, PK7_KEY)
        # Hill pads to a whole block; compare on the padded prefix.
        self.assertTrue(self.cipher.decrypt(cipher, PK7_KEY).startswith(plain))

    def test_keyed_indices_are_not_az(self):
        """The same matrix over A-Z is a different cipher, not a relabelling."""
        plain = letters_only(PROSE).upper()
        keyed = self.cipher.encrypt(plain, PK7_KEY)
        plain_alphabet = self.cipher.encrypt(
            plain, {"matrix": "ALCHEMIST", "key": "ANNEAL", "alphabet": "plain"}
        )
        self.assertNotEqual(keyed, plain_alphabet)

    def test_quagmire_layer_changes_the_output(self):
        plain = letters_only(PROSE).upper()
        with_key = self.cipher.encrypt(plain, PK7_KEY)
        without = self.cipher.encrypt(plain, {"matrix": "ALCHEMIST", "alphabet": "kryptos"})
        self.assertNotEqual(with_key, without)

    def test_singular_matrix_is_reported(self):
        with self.assertRaises(ValueError):
            # Determinant shares a factor with 26, so there is no inverse.
            self.cipher.decrypt(PK7, {"matrix": "AAAAAAAAA", "alphabet": "kryptos"})

    def test_pk7_key_reproduces_the_published_ciphertext(self):
        self.assertEqual(self.cipher.encrypt(PK7_PLAINTEXT, PK7_KEY), PK7)
        self.assertEqual(self.cipher.decrypt(PK7, PK7_KEY), PK7_PLAINTEXT)


class TestKeyedHillAttack(unittest.TestCase):
    """Ciphertext-only recovery, with no hint of alphabet, period or matrix."""

    def setUp(self) -> None:
        self.cipher = get("keyed_hill")

    def test_cracks_pk7_from_ciphertext_alone(self):
        candidates = list(self.cipher.crack(PK7, ctx(budget=30.0)))
        self.assertTrue(candidates, "the attack produced no candidates")
        best = candidates[0]
        self.assertEqual(best.plaintext, PK7_PLAINTEXT)
        self.assertGreaterEqual(best.confidence, 0.86)
        self.assertEqual(best.key["matrix"], "ALCHEMIST")
        self.assertEqual(best.key["key"], "ANNEAL")

    def test_cracks_a_plain_alphabet_instance(self):
        """The alphabet is searched, not assumed: a plain A-Z instance solves too."""
        key = {"matrix": "ALCHEMIST", "key": "ANNEAL", "alphabet": "plain"}
        plain = letters_only(PROSE * 2).upper()
        ciphertext = self.cipher.encrypt(plain, key)
        candidates = list(self.cipher.crack(ciphertext, ctx(budget=30.0)))
        self.assertTrue(candidates)
        self.assertTrue(
            plain.startswith(candidates[0].plaintext[:60]),
            f"recovered {candidates[0].plaintext[:60]!r}",
        )

    def test_a_keyword_of_the_wrong_length_is_rejected(self):
        for word in ("CHEMISTS", "MODULARITY"):
            with self.subTest(keyword=word), self.assertRaises(ValueError):
                self.cipher.encrypt(PROSE, {"matrix": word, "alphabet": "plain"})

    def test_recovers_a_synthetic_2x2_instance(self):
        # The Quagmire period has to be a whole number of blocks for the
        # phase split to model it: 4 letters over 2x2 blocks is two phases.
        key = {"matrix": "HILL", "key": "OAKS", "alphabet": "kryptos"}
        plain = letters_only(PROSE * 2).upper()
        ciphertext = self.cipher.encrypt(plain, key)
        candidates = list(self.cipher.crack(ciphertext, ctx(budget=30.0)))
        self.assertTrue(candidates)
        self.assertTrue(
            plain.startswith(candidates[0].plaintext[:40]),
            f"recovered {candidates[0].plaintext[:40]!r}",
        )

    def test_hinted_key_is_exact(self):
        candidates = list(self.cipher.crack(PK7, ctx(budget=10.0, key=PK7_KEY)))
        self.assertEqual(candidates[0].plaintext, PK7_PLAINTEXT)


class TestBlockRepeatDetection(unittest.TestCase):
    """The identification signal that points at a block cipher in the first place."""

    def test_pk7_shows_aligned_block_repeats(self):
        score, size, reason = _block_repeat_tells(PK7)
        self.assertEqual(size, 3)
        self.assertGreaterEqual(score, 0.5)
        self.assertIn("block grid", reason)

    def test_random_letters_do_not(self):
        import random

        rng = random.Random(7)
        noise = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(279))
        score, _, _ = _block_repeat_tells(noise)
        self.assertLess(score, 0.5)

    def test_identify_names_the_block_ciphers(self):
        hypotheses, _ = identify(PK7)
        names = [h.cipher for h in hypotheses]
        self.assertIn("keyed_hill", names)
        self.assertIn("hill", names)
        # And it should not be buried under the polyalphabetic guesses.
        self.assertLess(names.index("hill"), names.index("vigenere"))


class TestPK7Corpus(unittest.TestCase):
    """The repository's own PK7 record must match the verified decryption."""

    def test_stored_solution_matches(self):
        path = ROOT / "kryptos" / "pk_verified_solutions.json"
        record = json.loads(path.read_text())["PK7"]
        self.assertEqual(record["ciphertext"], PK7)
        self.assertEqual(record["plaintext"], PK7_PLAINTEXT)
        # The record must be reproducible from the key it names.
        self.assertEqual(get("keyed_hill").encrypt(record["plaintext"], PK7_KEY), PK7)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
