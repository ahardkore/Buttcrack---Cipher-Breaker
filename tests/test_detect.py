"""Tests for cipher identification -- the engine's triage step."""

from __future__ import annotations

import unittest

from buttcrack.ciphers import get
from buttcrack.detect import characterise, charset_summary, identify

PLAINTEXT = (
    "The archive contains the original manuscripts, three of which were lost during the fire of "
    "eighteen ninety two, and the catalogue that described them was destroyed as well, so the "
    "scholars have had to reconstruct the order of the collection from the letters of the "
    "librarians who worked there at the time."
)
KEY = "SECRET"


def ct(name: str, key=None) -> str:
    return get(name).encrypt(PLAINTEXT, key if key is not None else get(name).info.example_key)


class TestCharacterise(unittest.TestCase):
    def test_english_statistics(self):
        stats = characterise(PLAINTEXT)
        self.assertEqual(stats.length, len(PLAINTEXT))
        self.assertGreater(stats.ic, 0.058)
        self.assertGreater(stats.confidence, 0.62)
        self.assertTrue(stats.is_letter_text)
        self.assertGreater(stats.upper, 0)
        self.assertGreater(stats.lower, 0)

    def test_substitution_keeps_ic_and_ruins_fitness(self):
        stats = characterise(ct("substitution"))
        self.assertGreater(stats.ic, 0.058)
        self.assertLess(stats.fitness, -5.0)
        self.assertLess(stats.confidence, 0.62)

    def test_vigenere_flattens_ic(self):
        stats = characterise(ct("vigenere", KEY))
        self.assertLess(stats.ic, 0.055)

    def test_transposition_keeps_the_distribution(self):
        stats = characterise(ct("columnar", "SPIES"))
        self.assertGreater(stats.ic, 0.058)
        self.assertLess(stats.chi2_per_char, 1.5)

    def test_character_sets_are_described(self):
        self.assertIn("a-z", charset_summary("hello world"))
        self.assertIn("0-9", charset_summary("abc123"))
        self.assertIn("non-ascii", charset_summary("\u00e9\u00ff\u2014"))

    def test_stats_serialise(self):
        import json

        payload = json.dumps(characterise(PLAINTEXT).as_dict())
        self.assertIn("index_of_coincidence", payload)


class TestIdentify(unittest.TestCase):
    def top(self, text: str, limit: int = 6) -> list[str]:
        hypotheses, _ = identify(text, limit=limit)
        return [h.cipher for h in hypotheses]

    def test_plain_english_is_recognised_as_plaintext(self):
        self.assertEqual(self.top(PLAINTEXT)[0], "none")

    def test_shift_family(self):
        self.assertEqual(self.top(ct("caesar", 7))[0], "caesar")
        self.assertEqual(self.top(ct("rot13"))[0], "rot13")
        # Atbash is a substitution with a reciprocal alphabet: naming the family
        # is enough, the engine tries all of them anyway.
        self.assertIn("substitution", self.top(ct("atbash")))
        self.assertEqual(self.top(ct("affine"))[0], "substitution")

    def test_polyalphabetic_family(self):
        self.assertEqual(self.top(ct("vigenere", KEY))[0], "vigenere")
        self.assertEqual(self.top(ct("beaufort", "LANTERN"))[0], "vigenere")
        self.assertIn("vigenere", self.top(ct("autokey", "PRIMER")))

    def test_transposition_family(self):
        # The distribution survives a transposition intact, so the family is
        # named; which member it is, is the search's job.
        for name, key in (("columnar", "SPIES"), ("rail_fence", 4), ("skip", 3)):
            with self.subTest(cipher=name):
                self.assertEqual(self.top(ct(name, key))[0], "columnar")
                self.assertIn(name, self.top(ct(name, key)))

    def test_punctuated_ciphertexts_are_identified_too(self):
        # Real ciphertexts arrive with their commas and spaces, and letter
        # statistics must not be defeated by the layout.
        prose = "The quick brown fox jumps over the lazy dog, and the committee deliberated."
        shifted = get("caesar").encrypt(prose, 3)
        self.assertIn(",", shifted)  # layout preserved by the cipher itself
        self.assertTrue(characterise(shifted).is_letter_text)
        self.assertEqual(self.top(shifted)[0], "caesar")

    def test_polygraphic(self):
        self.assertEqual(self.top(ct("playfair", "MONARCHY"))[0], "playfair")

    def test_codes(self):
        self.assertEqual(self.top(get("morse").encode(PLAINTEXT))[0], "morse")
        self.assertEqual(self.top(get("a1z26").encode(PLAINTEXT))[0], "a1z26")
        self.assertEqual(self.top(get("polybius").encode(PLAINTEXT))[0], "polybius")
        self.assertEqual(self.top(get("bacon").encode(PLAINTEXT))[0], "bacon")
        self.assertEqual(self.top(get("binary").encode(PLAINTEXT))[0], "binary")

    def test_encodings(self):
        self.assertEqual(self.top(get("base64").encode(PLAINTEXT))[0], "base64")
        self.assertEqual(self.top(get("base16").encode(PLAINTEXT))[0], "base16")
        self.assertEqual(self.top(get("base58").encode(PLAINTEXT))[0], "base58")
        self.assertEqual(self.top(get("base85").encode(PLAINTEXT))[0], "base85")
        self.assertIn("base32", self.top(get("base32").encode(PLAINTEXT)))
        self.assertIn("url", self.top(get("url").encode(PLAINTEXT)))
        self.assertEqual(self.top(get("decimal_ascii").encode(PLAINTEXT))[0], "decimal_ascii")

    def test_the_outer_layer_of_a_stack_is_the_one_that_is_named(self):
        stacked = get("base64").encode(get("caesar").encrypt(PLAINTEXT, 5))
        self.assertEqual(self.top(stacked)[0], "base64")

    def test_a_structural_format_outranks_letter_statistics(self):
        # base64 of English is letters and digits, and its letter stream looks
        # polyalphabetic.  The format must still win, or the engine wastes its
        # budget hill climbing a Vigenere that was never used.
        hypotheses, _ = identify(get("base64").encode(PLAINTEXT))
        by_name = {h.cipher: h.likelihood for h in hypotheses}
        self.assertGreater(by_name["base64"], by_name.get("vigenere", 0.0))

    def test_binary_is_not_mistaken_for_bacon(self):
        # Both use two symbols; the group width is what separates them.
        self.assertNotIn("bacon", self.top(get("binary").encode(PLAINTEXT)))

    def test_morse_is_not_mistaken_for_base85(self):
        self.assertNotIn("base85", self.top(get("morse").encode(PLAINTEXT)))

    def test_every_hypothesis_explains_itself(self):
        hypotheses, _ = identify(ct("vigenere", KEY))
        for hypothesis in hypotheses:
            with self.subTest(cipher=hypothesis.cipher):
                self.assertGreater(hypothesis.likelihood, 0.0)
                self.assertLessEqual(hypothesis.likelihood, 1.0)
                self.assertGreater(len(hypothesis.reason), 10)

    def test_hypotheses_are_sorted_and_limited(self):
        hypotheses, _ = identify(ct("vigenere", KEY), limit=3)
        self.assertLessEqual(len(hypotheses), 3)
        likes = [h.likelihood for h in hypotheses]
        self.assertEqual(likes, sorted(likes, reverse=True))

    def test_a_ciphers_own_structural_read_is_consulted_even_when_rules_fired(self):
        # The wheel cipher's self-assessment is the sharpest detector in the
        # collection: every 25th letter goes through the same disk, so the
        # columns of a period-25 split are monoalphabetic and it reads 0.9 on a
        # real M-94.  It used to be consulted only when *no* rule had fired, so
        # on a wheel ciphertext -- where the generic "flat IC" rule obligingly
        # named Vigenere -- the M-94 never appeared in the hypotheses at all.
        # The engine orders its attacks by these, so it never attacked the wheel
        # and spent the whole budget on polyalphabetic guesses.
        wheel = get("m94")
        ciphertext = wheel.encrypt(PLAINTEXT, {"order": "YRNCIXDULPTWFZHVMQBOKJEGS", "row": 4})
        hypotheses, _ = identify(ciphertext, limit=999)
        named = {h.cipher: h.likelihood for h in hypotheses}
        self.assertIn("m94", named, f"the wheel's own read was dropped: {named}")
        # Its evidence is split across two readings: the raw text still has the
        # flat IC of a polyalphabetic cipher, so the structural read is halved
        # and the wheel lands mid-list (rank 10 of 22 here) rather than on top.
        # That is exactly why the engine must ask for the whole list.
        self.assertGreater(named["m94"], 0.25)
        # And the evidence still explains itself, like every other hypothesis.
        wheel_hypothesis = next(h for h in hypotheses if h.cipher == "m94")
        self.assertGreater(len(wheel_hypothesis.reason), 10)
        # The period-25 columns are monoalphabetic even though the text as a
        # whole is not -- that gap is what makes the wheel inferable at all.
        self.assertLess(characterise(ciphertext).ic, 0.055)
        from buttcrack.text import ic_of_columns, letters_only

        self.assertGreater(ic_of_columns(letters_only(ciphertext), 25), 0.065)

    def test_real_playfair_clears_the_engines_strong_layer_bar(self):
        # This is the evidence that lets the engine name a cipher it could not
        # solve: real Playfair reads ~0.9 -- past the 0.6 "this text *is* that
        # cipher" bar -- while every failed unciphering it competes with is
        # noise.  If Playfair's tells ever get weaker than this bar, the
        # unsolved report goes back to naming whichever failure scored 0.011
        # instead of the cipher the identifier is 90% sure of.
        from buttcrack.engine import STRONG_LAYER
        from tests.test_engine import PARAGRAPH, enc

        hypotheses, _ = identify(enc("playfair", PARAGRAPH * 3, "MONARCHY"), limit=999)
        read = {h.cipher: h.likelihood for h in hypotheses}
        self.assertGreaterEqual(read.get("playfair", 0.0), STRONG_LAYER, read)
        self.assertGreater(len(next(h for h in hypotheses if h.cipher == "playfair").reason), 10)

    def test_a_cipher_keeps_its_strongest_evidence(self):
        # Several rules can name the same cipher, and the engine turns the
        # hypotheses into a per-cipher lookup table, so a later weaker entry
        # must not overwrite an earlier strong one.
        hypotheses, _ = identify(ct("substitution"))
        substitution = [h for h in hypotheses if h.cipher == "substitution"]
        self.assertEqual(len(substitution), 1, "the same cipher appears twice in the hypotheses")
        self.assertGreater(substitution[0].likelihood, 0.5)

    def test_gibberish_produces_no_confident_answer(self):
        hypotheses, stats = identify("Xk9#Qv2!Lm7$Zr4@Wp8%Ty3^Bn6&Js1*Hd5")
        self.assertLess(stats.confidence, 0.62)
        for hypothesis in hypotheses:
            self.assertLess(hypothesis.likelihood, 0.95)

    def test_empty_input_is_handled(self):
        hypotheses, stats = identify("")
        self.assertEqual(stats.length, 0)
        self.assertIsInstance(hypotheses, list)


if __name__ == "__main__":
    unittest.main()
