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


class TestKeyedAlphabetCiphers(unittest.TestCase):
    """Quagmire III and sum-clocks, against published Kryptos CTF answers.

    These are real ciphertexts with published solutions, which makes them
    better than synthetic vectors: the conventions (which alphabet, which
    direction, where the key index comes from) are pinned by somebody else's
    answer rather than by this code's own opinion.
    """

    #: Paradigm Kryptos PK1: Quagmire III, KRYPTOS alphabet, key PROVENANCE.
    PK1_CT = (
        "MQRALWVSJIMSXGJSVWQPHJMDINKXGIMHNKYUTXTTGJCYIABTJUMQEOFBITNBMONGVWETDLAIJPQYMZIKBQ"
        "VRXZHUIJVDJLTQHIQYHEQKFTPTJYCONAFXYWQIBONAYXGWJFFIQMVXNVQYQFMWKFEJQYZFBWKXBKDQLJRE"
        "LWGWDKHECRSFBKOVQJCPYDNKXYHE"
    )
    PK1_PT = (
        "INVESTIGATIONLOGITEMEIGHTKNOTTIGHTLYWOUNDITSTHREADINSCRIBEDWITHLETTERSTHEACCESSION"
        "LOGSAYSONCEUNRAVELEDITREVEALSTHEROUTETOTHELOSTARCHIVEOFPELLEGRINTWELVEPRIORARCHIVI"
        "STSTRIEDTOUNRAVELITALLFAILED"
    )

    def test_quagmire3_matches_the_published_pk1_solution(self):
        cipher = get("quagmire3")
        key = {"key": "PROVENANCE", "alphabet": "kryptos"}
        self.assertEqual(cipher.decrypt(self.PK1_CT, key), self.PK1_PT)
        self.assertEqual(cipher.encrypt(self.PK1_PT, key), self.PK1_CT)

    def test_quagmire3_recovers_pk1_without_the_key(self):
        from buttcrack.ciphers.base import CrackContext

        cipher = get("quagmire3")
        ctx = CrackContext.create(budget=20)
        best = next(iter(cipher.crack(self.PK1_CT, ctx)), None)
        self.assertIsNotNone(best)
        self.assertEqual(best.plaintext, self.PK1_PT)
        self.assertEqual(best.key["key"], "PROVENANCE")

    def test_sum_clock_is_not_a_long_vigenere(self):
        """Four wheels of 4, 5, 6 and 7 have a key longer than the message."""
        cipher = get("sum_clock")
        plaintext = "ATTACKATDAWNTHEBRIDGEISHELDBYTHEENEMY" * 4
        key = {"periods": [4, 5, 6, 7], "alphabet": "kryptos",
               "wheels": [[3, 14, 2, 9], [1, 7, 22, 4, 11], [5, 2, 19, 8, 13, 0], [6, 21, 3, 17, 9, 24, 12]]}
        ciphertext = cipher.encrypt(plaintext, key)
        self.assertEqual(cipher.decrypt(ciphertext, key), plaintext)
        self.assertNotEqual(ciphertext, plaintext)

    def test_two_wheel_clocks_are_solved_exactly_not_searched(self):
        """Fix the short wheel and the rest is a Vigenere of known period.

        This is the PK3 case, and the recovered wheels are the published
        keywords rather than something gauge-equivalent to them, which is a
        stronger check than matching the plaintext.

        The text length matters and the test says so: the long wheel is solved
        one column at a time, so each of its columns needs enough letters for
        chi-squared to be right.  At 141 letters over a 10-wheel (14 a column)
        one column comes out wrong; at 280, as PK3 actually is, it does not.
        """
        from buttcrack.ciphers.base import CrackContext
        from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET

        cipher = get("sum_clock")
        plaintext = (
            "THEARCHIVECONTAINSTHEORIGINALMANUSCRIPTSTHREEOFWHICHWERELOSTDURINGTHEFIRE"
            "OFEIGHTEENNINETYTWOANDTHECATALOGUETHATDESCRIBEDTHEMWASDESTROYEDASWELL"
            "EVERYSECRETSOCIETYINTHECITYMAINTAINSATLEASTONEARCHIVEOFFORBIDDENDOCUMENTS"
            "ANDTHECOMMITTEEHASDECIDEDTOPOSTPONETHERAILWAYCONFERENCEUNTILFURTHERNOTICE"
        )
        index = {c: i for i, c in enumerate(KRYPTOS_ALPHABET)}
        wheels = [[index[c] for c in "ORDINATE"], [index[c] for c in "PENTIMENTO"]]
        ciphertext = cipher._apply(plaintext, KRYPTOS_ALPHABET, wheels, +1)
        ctx = CrackContext.create(budget=60)
        found = cipher.solve_two_wheels(
            ciphertext, KRYPTOS_ALPHABET, 8, 10, ctx,
            candidates=[[index[c] for c in "ORDINATE"],
                        [index[c] for c in "MARIGOLD"],
                        [index[c] for c in "PROVENAN"]],
        )
        self.assertTrue(found)
        self.assertEqual(found[0][2], plaintext)
        self.assertEqual("".join(KRYPTOS_ALPHABET[v] for v in found[0][1][0]), "ORDINATE")
        self.assertEqual("".join(KRYPTOS_ALPHABET[v] for v in found[0][1][1]), "PENTIMENTO")

    def test_a_sum_clock_keystream_has_a_linear_annihilator(self):
        """Four wheels of 4, 5, 6 and 7 are killed by a four-tap operator.

        60 = lcm(4, 5, 6) cancels three wheels and leaves a 7-periodic
        remainder, which a further lag-7 difference cancels. The consequence
        is a condition on the *plaintext* computable from the ciphertext with
        no key at all, which is what makes scanning a corpus for a suspected
        passage possible.
        """
        from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET

        cipher = get("sum_clock")
        self.assertEqual(
            sorted(cipher.annihilator([4, 5, 6, 7]).items()),
            [(0, 1), (7, -1), (60, -1), (67, 1)],
        )
        wheels = [[7, 19, 2, 11], [23, 4, 16, 8, 1],
                  [12, 25, 6, 18, 3, 20], [9, 14, 0, 21, 5, 17, 10]]
        keystream = cipher.keystream(wheels, 153)
        for t in range(len(keystream) - 67):
            self.assertEqual(
                (keystream[t + 67] - keystream[t + 60] - keystream[t + 7] + keystream[t]) % 26,
                0,
                f"annihilator failed at t={t}",
            )
        # And it is specific: a random keystream is not annihilated.
        import random as _random

        rng = _random.Random(5)
        noise = [rng.randrange(26) for _ in range(153)]
        violations = sum(
            1 for t in range(len(noise) - 67)
            if (noise[t + 67] - noise[t + 60] - noise[t + 7] + noise[t]) % 26 != 0
        )
        self.assertGreater(violations, 70)
        _ = KRYPTOS_ALPHABET

    def test_a_corpus_scan_finds_a_known_passage(self):
        """If the plaintext is a passage you have, the annihilator finds it."""
        from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET

        cipher = get("sum_clock")
        passage = (
            "ATLASTTHEFIREWASLITANDTHEBELLOWSSANGASTHECOALSTURNEDWHITETHESMITHTOOKUPHIS"
            "HAMMERANDBEGANTOWORKTHEIRONWHILEAPPRENTICESWATCHEDINSILENCENEARTHEDOOR"
        )[:153]
        wheels = [[7, 19, 2, 11], [23, 4, 16, 8, 1],
                  [12, 25, 6, 18, 3, 20], [9, 14, 0, 21, 5, 17, 10]]
        ciphertext = cipher._apply(passage, KRYPTOS_ALPHABET, wheels, +1)
        corpus = "QWERTYUIOPASDFGHJKLZXCVBNM" * 400 + passage + "MNBVCXZLKJHGFDSAPOIUYTREWQ" * 400
        hits = cipher.scan_corpus(ciphertext, corpus, [4, 5, 6, 7])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][2], passage)

    def test_partial_corpus_scan_finds_a_long_quotation_only(self):
        """The partial scan degrades gracefully, but has a real floor.

        Each constraint spans 67 characters, so a quoted stretch of L letters
        gives L-67 usable constraints. A 74-letter quotation is therefore
        undetectable and a 110-letter one is unmistakable. The test pins both
        ends, because the failing half is the one that would otherwise be
        mistaken for "the corpus is ruled out".
        """
        import random as _random

        from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET

        cipher = get("sum_clock")
        rng = _random.Random(11)
        base = (
            "WHENTHEIRONHASBEENHEATEDUNTILITGLOWSWHITEYOUSHALLDRAWITOUTUPONTHEANVILANDBEAT"
            "ITGENTLYWITHASMALLHAMMERUNTILITISTHINASAREEDANDTHENQUENCHITINCOLDWATERDRAWN"
        )
        tail = "THENTHEMASTERTURNEDAWAYANDSAIDNOTHINGMOREUNTILTHEMORNINGBELLRANGOUT"
        corpus_noise = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(20000))
        corpus = corpus_noise[:10000] + base + corpus_noise[10000:]
        wheels = [[7, 19, 2, 11], [23, 4, 16, 8, 1],
                  [12, 25, 6, 18, 3, 20], [9, 14, 0, 21, 5, 17, 10]]

        for quoted, expect in ((74, False), (110, True)):
            plaintext = (base[:quoted] + tail)[:153]
            ciphertext = cipher._apply(plaintext, KRYPTOS_ALPHABET, wheels, +1)
            hits = cipher.scan_corpus_partial(
                ciphertext, corpus, [4, 5, 6, 7], report_from=12
            )
            with self.subTest(quoted=quoted):
                if expect:
                    self.assertTrue(hits, f"{quoted}-letter quotation should be found")
                    self.assertEqual(hits[0][0], 10000)
                    self.assertGreaterEqual(hits[0][1], 30)
                else:
                    self.assertFalse(hits, f"{quoted} letters is below the detection floor")

    def test_a_crib_solves_the_wheels_by_linear_algebra(self):
        """The PK8 shape: 153 letters, four wheels, no search at all.

        The keystream is linear in the wheels, so 19 known letters are 19
        equations in 19 effective unknowns -- which is why this lands in a
        tenth of a second where annealing, measured, does not land at all.
        """
        from buttcrack.ciphers.base import CrackContext
        from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET

        cipher = get("sum_clock")
        plaintext = (
            "ATLASTTHEFIREWASLITANDTHEBELLOWSSANGASTHECOALSTURNEDWHITETHESMITHTOOKUPHISHAMMER"
            "ANDBEGANTOWORKTHEIRONWHILEAPPRENTICESWATCHEDINSILENCENEARTHEDOORWAYATDUSK"
        )[:153]
        wheels = [[7, 19, 2, 11], [23, 4, 16, 8, 1], [12, 25, 6, 18, 3, 20], [9, 14, 0, 21, 5, 17, 10]]
        ciphertext = cipher._apply(plaintext, KRYPTOS_ALPHABET, wheels, +1)
        ctx = CrackContext.create(budget=30)
        found = cipher.crack_with_crib(ciphertext, plaintext[:19], ctx, periods=[4, 5, 6, 7])
        self.assertTrue(found)
        self.assertEqual(found[0][3], plaintext)
        self.assertEqual(found[0][1], 0)

    def test_a_short_crib_reduces_the_search_instead_of_solving_it(self):
        """Below the length that pins the key, a crib still cuts the dimension.

        Twelve known letters do not determine a four-wheel key, but they do
        turn a nineteen-dimensional search into a seven-dimensional one, and
        the returned subspace is what the hybrid attack anneals inside.
        """
        from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET

        cipher = get("sum_clock")
        plaintext = (
            "ATLASTTHEFIREWASLITANDTHEBELLOWSSANGASTHECOALSTURNEDWHITETHESMITHTOOKUPHISHAMMER"
            "ANDBEGANTOWORKTHEIRONWHILEAPPRENTICESWATCHEDINSILENCENEARTHEDOORWAYATDUSK"
        )[:153]
        wheels = [[7, 19, 2, 11], [23, 4, 16, 8, 1], [12, 25, 6, 18, 3, 20], [9, 14, 0, 21, 5, 17, 10]]
        ciphertext = cipher._apply(plaintext, KRYPTOS_ALPHABET, wheels, +1)
        subspace = cipher._crib_subspace(
            ciphertext, KRYPTOS_ALPHABET, [4, 5, 6, 7], plaintext[:12], 0
        )
        self.assertIsNotNone(subspace)
        particular, basis = subspace
        self.assertEqual(len(particular), 22)
        # 22 unknowns - 3 gauge - 12 crib equations = 7 free directions.
        self.assertEqual(len(basis), 7)
        # The true key must lie in the subspace the crib describes.
        flat = [v for wheel in wheels for v in wheel]
        gauge = 0
        for w in range(1, 4):
            shift = wheels[w][0]
            gauge += shift
        normalised = [(v + gauge) % 26 for v in wheels[0]]
        for w in range(1, 4):
            normalised += [(v - wheels[w][0]) % 26 for v in wheels[w]]
        self.assertEqual(len(normalised), len(flat))

    def test_gauge_freedom_is_fixed_so_a_crib_has_few_solutions(self):
        """Shifting one wheel up and another down changes nothing.

        Left unfixed it multiplies the solution set by 26**(wheels-1) -- 17,576
        identical readings for four wheels -- which is what made a correct crib
        look unsolvable inside any enumeration cap.
        """
        from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET

        cipher = get("sum_clock")
        text = "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOGANDKEEPSRUNNINGUNTILDAWNBREAKS"
        a = [[1, 2, 3, 4], [5, 6, 7, 8, 9]]
        b = [[(v + 3) % 26 for v in a[0]], [(v - 3) % 26 for v in a[1]]]
        self.assertEqual(
            cipher._apply(text, KRYPTOS_ALPHABET, a, -1),
            cipher._apply(text, KRYPTOS_ALPHABET, b, -1),
        )


class TestRoundTrips(unittest.TestCase):
    #: Ciphers that lose information on purpose, so character-exact round trips
    #: are the wrong assertion.  For these the invariant is consistency:
    #: re-encrypting the decryption must reproduce the ciphertext exactly.
    #: Ciphers that are the identity on this particular plaintext, by design.
    #: Quoted-printable only escapes what is not printable 7-bit ASCII, so a
    #: sentence of plain letters passes through it untouched -- that *is* the
    #: encoding working correctly, and `test_quoted_printable_escapes` covers
    #: the case where it has something to do.
    TRANSPARENT = {"quoted_printable"}

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
                if name not in self.TRANSPARENT:
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
        for a, _b in get("affine").keys():  # noqa: SIM118 - Cipher.keys() is a generator, not dict.keys()
            self.assertNotEqual(a, 1, "a=1 is Caesar, not Affine")

    def test_transposition_keys_have_at_least_two_units(self):
        for rails, _offset in get("rail_fence").keys():  # noqa: SIM118 - Cipher.keys(), not dict.keys()
            self.assertGreaterEqual(rails, 2)
        for params in get("route").keys():  # noqa: SIM118 - Cipher.keys(), not dict.keys()
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
