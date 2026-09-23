"""Tests for :mod:`buttcrack.text` -- normalisation, statistics, layout helpers."""

from __future__ import annotations

import unittest

from buttcrack.text import (
    A26,
    alphabet_mapping,
    apply_mapping,
    best_block_size,
    best_key_length,
    chunk,
    columnar,
    dedupe,
    entropy,
    fold,
    frequencies,
    hamming_distance,
    ic_of_columns,
    index_of_coincidence,
    keyed_alphabet,
    letters_only,
    normalise,
    normalised_hamming,
    relative_frequencies,
    respaced,
    restore_shape,
    strip_space,
    to_bytes,
)

SAMPLE = "The quick brown fox jumps over the lazy dog, and the committee deliberated."

#: Statistical assertions need a few hundred letters to be stable; short samples
#: have wild index-of-coincidence swings and would make the tests flaky.
LONG_SAMPLE = (
    "The archive contains the original manuscripts, three of which were lost during the fire of "
    "eighteen ninety two, and the catalogue that described them was destroyed as well, so the "
    "scholars have had to reconstruct the order of the collection from the letters of the "
    "librarians who worked there at the time. Every secret society in the city maintains at least "
    "one archive of forbidden documents, and the committee has decided to postpone the railway "
    "conference until further notice is issued by the board of directors."
)


class TestNormalisation(unittest.TestCase):
    def test_letters_only_drops_everything_else(self):
        self.assertEqual(letters_only("Attack at dawn! 04:30"), "ATTACKATDAWN")

    def test_letters_only_keeps_only_the_given_alphabet(self):
        self.assertEqual(letters_only("cafe 12", "ABCDEF"), "CAFE")

    def test_normalise_folds_accents(self):
        # Escapes rather than literals: the test file itself must not depend on
        # the locale's encoding.
        self.assertEqual(normalise("Caf\u00e9 na\u00efve"), "CAFENAIVE")
        self.assertEqual(normalise("Stra\u00dfe"), "STRASSE")
        self.assertEqual(normalise("\u00feing"), "THING")

    def test_fold_preserves_case_and_punctuation(self):
        # fold() is about scripts, not case: only the accents move.
        self.assertEqual(fold("Hello, World!"), "Hello, World!")
        self.assertEqual(fold("\u00c9cole"), "Ecole")

    def test_strip_space(self):
        self.assertEqual(strip_space("a b\tc\nd"), "abcd")

    def test_chunk_groups_and_separates(self):
        self.assertEqual(chunk("ATTACKATDAWN", 5), "ATTAC KATDA WN")
        self.assertEqual(chunk("ATTACK", 4, "-"), "ATTA-CK")


class TestStatistics(unittest.TestCase):
    def test_frequencies_counts_letters(self):
        counts = frequencies("AABBC")
        self.assertEqual((counts["A"], counts["B"], counts["C"]), (2, 2, 1))

    def test_relative_frequencies_sums_to_one(self):
        rel = relative_frequencies(SAMPLE)
        self.assertAlmostEqual(sum(rel.values()), 1.0, places=6)

    def test_index_of_coincidence_separates_english_from_random(self):
        english_ic = index_of_coincidence(letters_only(LONG_SAMPLE))
        flat_ic = index_of_coincidence(A26 * 4)
        self.assertGreater(english_ic, 0.058)
        self.assertLess(flat_ic, 0.045)

    def test_ic_of_columns_peaks_at_the_true_period(self):
        from buttcrack.ciphers import get

        stream = get("vigenere").prepare(
            get("vigenere").encrypt(
                LONG_SAMPLE.replace(",", "").replace(".", ""),
                "SECRET",
            )
        )
        length, quality = best_key_length(stream, 14)
        # IC finds the period or a multiple of it; the engine sweeps every length
        # on short texts precisely because IC alone is not exact.
        self.assertIn(length, (6, 12))
        self.assertGreater(quality, 0.0)
        self.assertGreater(ic_of_columns(stream, 6), ic_of_columns(stream, 5))

    def test_entropy_of_uniform_text_is_maximal(self):
        self.assertAlmostEqual(entropy("abcd"), 2.0, places=6)
        self.assertAlmostEqual(entropy("aaaa"), 0.0, places=6)

    def test_hamming_distance_counts_differing_bits(self):
        self.assertEqual(hamming_distance(b"\x00\x00", b"\x01\x03"), 3)
        self.assertEqual(hamming_distance(b"same", b"same"), 0)

    def test_normalised_hamming_is_small_for_english_blocks(self):
        data = to_bytes(letters_only(SAMPLE))
        value = normalised_hamming(data, 4)
        self.assertGreater(value, 0.0)
        self.assertLess(value, 6.0)

    def test_best_block_size_finds_a_period_of_the_xor_key(self):
        from buttcrack.ciphers import get

        ct = get("xor_repeating").encrypt(
            "The package will be delivered to the safe house before midnight tonight by the courier.", "KEY"
        )
        size, score = best_block_size(to_bytes(ct), 16)
        # A multiple of the true key length scores at least as well as the key
        # length itself, so the honest assertion is "some period of 3".
        self.assertEqual(size % 3, 0)
        self.assertLess(score, 3.0)  # random bytes sit near 4.5


class TestAlphabetTools(unittest.TestCase):
    def test_keyed_alphabet_puts_the_keyword_first(self):
        self.assertEqual(keyed_alphabet("ZEBRA"), "ZEBRACDFGHIJKLMNOPQSTUVWXY")

    def test_keyed_alphabet_ignores_non_letters(self):
        self.assertEqual(keyed_alphabet("zebra!"), "ZEBRACDFGHIJKLMNOPQSTUVWXY")

    def test_alphabet_mapping_and_apply(self):
        mapping = alphabet_mapping(A26, keyed_alphabet("ZEBRA"))
        self.assertEqual(apply_mapping("ABC", mapping), "ZEB")
        self.assertEqual(apply_mapping("ZEB", mapping, invert=True), "ABC")

    def test_dedupe_preserves_order(self):
        self.assertEqual(list(dedupe("BANANA")), ["B", "A", "N"])

    def test_columnar_splits_into_rows(self):
        self.assertEqual(columnar("ABCDEFG", 3), [["A", "B", "C"], ["D", "E", "F"], ["G"]])


class TestLayout(unittest.TestCase):
    def test_restore_shape_reapplies_case_and_spacing(self):
        self.assertEqual(restore_shape("ATTACKATDAWN", "Xxxxxx xx xxxx"), "Attack at dawn")
        self.assertEqual(restore_shape("HELLOWORLD", "Hello, world!"), "Hello, world!")

    def test_restore_shape_gives_up_on_a_length_mismatch(self):
        self.assertIsNone(restore_shape("TOOLONG", "Ab cd"))

    def test_respaced_inserts_word_breaks(self):
        from buttcrack.lang import get_model

        words = get_model().segment("thequickbrownfox")[1]
        self.assertEqual(respaced("thequickbrownfox", words), "the quick brown fox")


if __name__ == "__main__":
    unittest.main()
