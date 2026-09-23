"""Tests for the cipher implementations and the registry.

The centrepiece is :meth:`TestRoundTrips.test_every_cipher_round_trips`: every
registered cipher, using the example key from its own ``CipherInfo``, must
decrypt its own encryption back to the normalised plaintext.  That one test is
what caught a Bifid whose coordinate fractionation was interleaved instead of
concatenated -- which made it the identity cipher.
"""

from __future__ import annotations

import unittest

from buttcrack.ciphers import (
    ALL_CIPHERS,
    BY_NAME,
    attack_ciphers,
    by_family,
    get,
    layer_ciphers,
    try_get,
)
from buttcrack.ciphers.base import CrackContext, Family
from buttcrack.lang import get_model
from buttcrack.text import letters_only

PLAINTEXT = (
    "The archive contains the original manuscripts, three of which were lost during the "
    "fire of eighteen ninety two, and the catalogue that described them was destroyed as "
    "well, so the scholars have had to reconstruct the order of the collection."
)
MODEL = get_model()


def ctx(**hints) -> CrackContext:
    return CrackContext.create(model=MODEL, budget=10.0, workers=1, hints=hints)


class TestRegistry(unittest.TestCase):
    def test_names_are_unique(self):
        names = [c.info.name for c in ALL_CIPHERS]
        self.assertEqual(len(names), len(set(names)))

    def test_every_name_resolves(self):
        for cipher in ALL_CIPHERS:
            self.assertIs(get(cipher.info.name), cipher)

    def test_aliases_resolve_and_are_not_single_characters(self):
        # A bare string in ``aliases=`` silently registers every character of it
        # as an alias; that typo is worth a regression test.
        for alias, cipher in BY_NAME.items():
            self.assertGreater(len(alias), 1, f"alias {alias!r} for {cipher.info.name}")
            self.assertIs(try_get(alias), cipher)

    def test_common_spellings_are_understood(self):
        for alias, expected in [
            ("ROT13", "rot13"),
            ("rot-13", "rot13"),
            ("hex", "base16"),
            ("b64", "base64"),
            ("vig", "vigenere"),
            ("morse_code", "morse"),
            ("railfence", "rail_fence"),
            ("simple substitution", "substitution"),
        ]:
            self.assertEqual(get(alias).info.name, expected, alias)

    def test_unknown_cipher_raises_with_a_useful_message(self):
        with self.assertRaises(KeyError) as caught:
            get("enigma")
        self.assertIn("enigma", str(caught.exception))
        self.assertIsNone(try_get("enigma"))

    def test_metadata_is_sane(self):
        for cipher in ALL_CIPHERS:
            info = cipher.info
            with self.subTest(cipher=info.name):
                self.assertIsInstance(info.family, Family)
                self.assertGreater(info.cost, 0.0)
                self.assertGreaterEqual(info.min_length, 1)
                # ``None`` means "not enumerable" (keyword-length keys).
                self.assertTrue(info.keyspace is None or info.keyspace >= 1)
                self.assertTrue(info.title)
                self.assertTrue(info.description)
                if info.keyed:
                    self.assertIsNotNone(info.example_key)

    def test_layers_are_a_subset_of_all_ciphers(self):
        names = {c.info.name for c in ALL_CIPHERS}
        for layer in layer_ciphers():
            self.assertIn(layer.info.name, names)
            self.assertTrue(layer.info.layer)

    def test_attack_ciphers_are_ciphers_plus_codes(self):
        # Encoding layers are peeled, never attacked -- except codes, whose
        # decoding *is* the answer ("morse" is not a layer to strip, it is the
        # cipher that was used).
        for cipher in attack_ciphers():
            with self.subTest(cipher=cipher.info.name):
                self.assertTrue(
                    not cipher.info.layer or cipher.info.family is Family.CODE,
                )
        names = {c.info.name for c in attack_ciphers()}
        self.assertIn("morse", names)
        self.assertIn("a1z26", names)
        self.assertNotIn("base64", names)
        self.assertNotIn("base16", names)

    def test_families_cover_every_cipher(self):
        grouped = by_family()
        self.assertEqual(
            sum(len(v) for v in grouped.values()),
            len(ALL_CIPHERS),
        )

    def test_attack_ciphers_are_ordered_by_cost(self):
        costs = [c.info.cost for c in attack_ciphers()]
        self.assertEqual(costs, sorted(costs))


class TestRoundTrips(unittest.TestCase):
    #: Ciphers that lose information on purpose, so character-exact round trips
    #: are the wrong assertion.  For these the invariant is consistency:
    #: re-encrypting the decryption must reproduce the ciphertext exactly.
    LOSSY = {
        "playfair": "double letters are split with X and the length is padded to a pair",
        "bifid": "same 5x5 grid as Playfair, so I and J share a cell",
        "polybius": "same 5x5 grid as Playfair, so I and J share a cell",
        "bacon": "the 24-letter Bacon alphabet merges U/V and I/J",
        "bacon_case": "the 24-letter Bacon alphabet merges U/V and I/J",
    }

    def test_every_cipher_round_trips(self):
        for cipher in ALL_CIPHERS:
            key = cipher.info.example_key
            name = cipher.info.name
            with self.subTest(cipher=name):
                ciphertext = cipher.encrypt(PLAINTEXT, key)
                self.assertNotEqual(
                    letters_only(ciphertext),
                    letters_only(PLAINTEXT),
                    f"{name} did not change the text -- an identity cipher is a bug "
                    "(this is how the broken Bifid was caught)",
                )
                recovered = cipher.decrypt(ciphertext, key)
                if name in self.LOSSY:
                    self.assertEqual(cipher.encrypt(recovered, key), ciphertext)
                else:
                    self.assertEqual(letters_only(recovered), letters_only(PLAINTEXT))

    def test_route_transposition_survives_ragged_grids(self):
        # Every route, several widths, several lengths including messages
        # shorter than one row: the read path must visit each cell exactly once.
        route_cipher = get("route")
        texts = ["AB", "ABCDEFGHI", "ATTACKATDAWN", "WEAREDISCOVEREDFLEEATONCE", PLAINTEXT]
        for route_name in route_cipher.ROUTES:
            for cols in (2, 3, 5, 7, 11, 13):
                for text in texts:
                    with self.subTest(route=route_name, cols=cols, length=len(text)):
                        ct = route_cipher.encrypt(text, {"cols": cols, "route": route_name})
                        back = route_cipher.decrypt(ct, {"cols": cols, "route": route_name})
                        self.assertEqual(letters_only(back), letters_only(text))

    def test_route_transposition_routes_are_distinct(self):
        route_cipher = get("route")
        outputs = {
            r: route_cipher.encrypt(PLAINTEXT, {"cols": 5, "route": r})
            for r in route_cipher.ROUTES
        }
        self.assertEqual(len(set(outputs.values())), len(outputs))

    def test_involutions_are_their_own_inverse(self):
        for name in ("atbash", "rot13"):
            cipher = get(name)
            once = cipher.encrypt(PLAINTEXT, None)
            twice = cipher.encrypt(once, None)
            self.assertNotEqual(once, PLAINTEXT)
            # encrypt() keeps case and punctuation where they were, so applying an
            # involution twice returns the original text rather than its normal
            # form -- which is what makes prose survive a round trip.
            self.assertEqual(twice, PLAINTEXT)
            self.assertEqual(letters_only(once), letters_only(cipher.prepare(once)))

    def test_reverse_is_attacked_rather_than_peeled(self):
        reverse = get("reverse")
        self.assertIn(reverse, attack_ciphers())
        self.assertNotIn(reverse, layer_ciphers())
        self.assertEqual(reverse.decrypt(reverse.encrypt("ATTACK", None), None), "ATTACK")


class TestKnownAnswers(unittest.TestCase):
    """Textbook vectors -- wrong here means wrong everywhere."""

    def test_caesar(self):
        self.assertEqual(get("caesar").encrypt("ATTACKATDAWN", 3), "DWWDFNDWGDZQ")

    def test_rot13(self):
        self.assertEqual(get("rot13").encrypt("HELLO", None), "URYYB")

    def test_atbash(self):
        self.assertEqual(get("atbash").encrypt("ABCXYZ", None), "ZYXCBA")

    def test_vigenere_lemon(self):
        self.assertEqual(get("vigenere").encrypt("ATTACKATDAWN", "LEMON"), "LXFOPVEFRNHR")

    def test_affine_wikipedia(self):
        self.assertEqual(get("affine").encrypt("AFFINECIPHER", {"a": 5, "b": 8}), "IHHWVCSWFRCP")

    def test_rail_fence_three_rails(self):
        self.assertEqual(
            get("rail_fence").encrypt("WEAREDISCOVEREDFLEEATONCE", 3),
            "WECRLTEERDSOEEFEAOCAIVDEN",
        )

    def test_morse(self):
        self.assertEqual(get("morse").encode("SOS"), "... --- ...")
        self.assertEqual(get("morse").decode(".... . .-.. .-.. ---"), "HELLO")

    def test_a1z26(self):
        self.assertEqual(get("a1z26").encode("ABC"), "1 2 3")
        self.assertEqual(letters_only(get("a1z26").decode("8 5 12 12 15")), "HELLO")

    def test_base64_and_hex(self):
        self.assertEqual(get("base64").encode("hello"), "aGVsbG8=")
        self.assertEqual(get("base16").encode("hi"), "6869")
        self.assertEqual(get("binary").encode("hi"), "01101000 01101001")

    def test_polybius_coordinates(self):
        # H is row 2 col 3 and I shares its cell with J in a 5x5 grid.
        self.assertEqual(get("polybius").encode("HI").split()[0], "23")

    def test_bacon_is_five_bits_per_letter(self):
        encoded = get("bacon").encode("AB")
        self.assertEqual(len(encoded.replace(" ", "")), 10)

    def test_playfair_pads_double_letters(self):
        # "HELLO" becomes HELXLO before encryption, so the output is six letters.
        self.assertEqual(len(get("playfair").encrypt("HELLO", "MONARCHY")), 6)

    def test_bifid_is_not_the_identity(self):
        bifid = get("bifid")
        key = {"key": "MONARCHY", "period": 7}
        stream = bifid.prepare("ATTACKATDAWN")
        self.assertNotEqual(bifid.encrypt(stream, key), stream)
        self.assertEqual(bifid.decrypt(bifid.encrypt(stream, key), key), stream)

    def test_xor_single_byte(self):
        xor = get("xor_single")
        self.assertEqual(xor.encrypt("hi", 0x42), "2a2b")


class TestKeyspaces(unittest.TestCase):
    def test_no_cipher_offers_the_identity_as_a_key(self):
        # An identity key restates the input and would steal credit from the
        # honest "no cipher" answer.
        for name, forbidden in [("caesar", 0), ("rot47", 0), ("xor_single", 0)]:
            cipher = get(name)
            with self.subTest(cipher=name):
                self.assertNotIn(forbidden, list(cipher.keys()))

    def test_affine_leaves_shifts_to_caesar(self):
        for a, _b in get("affine").keys():
            self.assertNotEqual(a, 1, "a=1 is Caesar, not Affine")

    def test_transposition_keys_have_at_least_two_units(self):
        for rails, _offset in get("rail_fence").keys():
            self.assertGreaterEqual(rails, 2)
        for params in get("route").keys():
            self.assertGreaterEqual(params["cols"], 2)
            self.assertIn(params["route"], get("route").ROUTES)

    def test_keyword_ciphers_do_not_pretend_to_have_an_enumerable_keyspace(self):
        # Columnar and substitution are cracked by search, not by sweeping keys.
        for name in ("columnar", "substitution", "keyword_substitution", "playfair", "bifid"):
            with self.subTest(cipher=name), self.assertRaises(NotImplementedError):
                list(get(name).keys())

    def test_keyspaces_match_their_documentation(self):
        self.assertEqual(len(list(get("caesar").keys())), 25)
        self.assertEqual(len(list(get("rot13").keys())), 1)
        self.assertEqual(len(list(get("xor_single").keys())), 255)
        # 11 units coprime to 26 (a == 1 is Caesar, and is left to Caesar) times
        # 26 shifts.
        self.assertEqual(len(list(get("affine").keys())), 11 * 26)


class TestLikelihood(unittest.TestCase):
    def test_likelihoods_are_probabilities(self):
        samples = {
            "english": PLAINTEXT,
            "caesar": get("caesar").encrypt(PLAINTEXT, 7),
            "vigenere": get("vigenere").encrypt(PLAINTEXT, "SECRET"),
            "morse": get("morse").encode(PLAINTEXT),
            "base64": get("base64").encode(PLAINTEXT),
        }
        context = ctx()
        for cipher in ALL_CIPHERS:
            for label, text in samples.items():
                value = cipher.likelihood(text, context)
                with self.subTest(cipher=cipher.info.name, sample=label):
                    self.assertGreaterEqual(value, 0.0)
                    self.assertLessEqual(value, 1.0)

    def test_the_right_family_ranks_highest(self):
        context = ctx()
        vigenere_ct = get("vigenere").encrypt(PLAINTEXT, "SECRET")
        caesar_ct = get("caesar").encrypt(PLAINTEXT, 7)
        self.assertGreater(
            get("vigenere").likelihood(vigenere_ct, context),
            get("columnar").likelihood(vigenere_ct, context),
        )
        self.assertGreater(
            get("caesar").likelihood(caesar_ct, context),
            get("vigenere").likelihood(caesar_ct, context),
        )


class TestPrescreen(unittest.TestCase):
    def test_prescreen_prefers_the_true_key(self):
        cipher = get("caesar")
        context = ctx()
        ct = cipher.encrypt(PLAINTEXT, 7)
        true_score = cipher.prescreen(cipher.decrypt(ct, 7), context)
        wrong_score = cipher.prescreen(cipher.decrypt(ct, 19), context)
        self.assertLess(true_score, wrong_score)


if __name__ == "__main__":
    unittest.main()
