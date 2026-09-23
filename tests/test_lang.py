"""Tests for the language model: the thing every verdict in Buttcrack rests on."""

from __future__ import annotations

import unittest

from buttcrack.lang import (
    CERTAIN_CONFIDENCE,
    FITNESS_BAD,
    FITNESS_GOOD,
    FRAGMENT_CAP,
    SOLVED_CONFIDENCE,
    get_model,
    ramp,
)
from buttcrack.text import letters_only

ENGLISH = (
    "The archive contains the original manuscripts, three of which were lost during the fire of "
    "eighteen ninety two, and the catalogue that described them was destroyed as well, so the "
    "scholars have had to reconstruct the order of the collection from the letters of the "
    "librarians who worked there at the time."
)
RANDOM = "QXZJVKWBPZGMYFTLRQXNJVDHWCKZSMPGTRQXJLVBNZDWKQSPMGYTFRLXVJZBQNCDWPM"
#: Degenerate text: plausible quadgrams by repetition, but only three letters.
DEGENERATE = "NESSNENESNESENENESENENESENENNESSNN"


class TestModelLoading(unittest.TestCase):
    def test_model_is_cached(self):
        self.assertIs(get_model(), get_model())

    def test_model_ships_with_its_data(self):
        model = get_model()
        self.assertGreater(model.ngram_count(4), 100_000)
        self.assertEqual(model.ngram_count(2), 676)
        self.assertGreater(len(model.words), 10_000)
        self.assertIn("the", model.words)
        self.assertGreater(model.words["the"], model.words["zymurgy"] if "zymurgy" in model.words else 0)

    def test_model_records_its_provenance(self):
        meta = get_model().meta
        self.assertGreater(meta["quadgrams_distinct"], 100_000)
        self.assertGreater(meta["dictionary_words"], 10_000)
        self.assertIn("sources", meta)  # attribution for the corpus data
        self.assertIn("built_at", meta)

    def test_monogram_reference_is_a_distribution(self):
        ref = get_model().monogram_reference()
        self.assertAlmostEqual(sum(ref.values()), 1.0, places=3)
        self.assertGreater(ref["E"], ref["Z"])

    def test_thresholds_are_ordered(self):
        self.assertGreater(FITNESS_GOOD, FITNESS_BAD)
        self.assertGreater(CERTAIN_CONFIDENCE, SOLVED_CONFIDENCE)
        self.assertGreater(SOLVED_CONFIDENCE, FRAGMENT_CAP)

    def test_ramp_maps_endpoints_and_clamps(self):
        self.assertEqual(ramp(1.0, 1.0, 0.0), 1.0)
        self.assertEqual(ramp(0.0, 1.0, 0.0), 0.0)
        self.assertEqual(ramp(0.5, 1.0, 0.0), 0.5)
        self.assertEqual(ramp(99.0, 1.0, 0.0), 1.0)
        self.assertEqual(ramp(-99.0, 1.0, 0.0), 0.0)


class TestScoring(unittest.TestCase):
    def setUp(self):
        self.model = get_model()

    def test_english_outranks_random_on_every_view(self):
        good = self.model.score(ENGLISH)
        bad = self.model.score(RANDOM)
        self.assertGreater(good.fitness, bad.fitness)
        self.assertGreater(good.words, bad.words)
        self.assertGreater(good.confidence, bad.confidence)

    def test_english_is_solved_and_certain(self):
        score = self.model.score(ENGLISH)
        self.assertTrue(score.solved)
        self.assertTrue(score.certain)
        self.assertGreater(score.confidence, CERTAIN_CONFIDENCE)

    def test_random_is_not_solved(self):
        score = self.model.score(RANDOM)
        self.assertFalse(score.solved)
        self.assertLess(score.confidence, SOLVED_CONFIDENCE)

    def test_chi_squared_separates_english_from_random(self):
        good = self.model.chi_squared(letters_only(ENGLISH), per_char=True)
        bad = self.model.chi_squared(RANDOM, per_char=True)
        self.assertLess(good, 1.0)
        self.assertGreater(bad, 5.0)

    def test_ngram_score_punishes_shuffled_letters(self):
        stream = letters_only(ENGLISH)
        shuffled = stream[::-1]
        self.assertGreater(self.model.ngram_score(stream), self.model.ngram_score(shuffled))

    def test_repetitive_text_is_rejected_by_the_variety_check(self):
        score = self.model.score(DEGENERATE)
        self.assertLess(score.confidence, SOLVED_CONFIDENCE)
        english = self.model.score(ENGLISH[: len(DEGENERATE) * 2])
        self.assertGreater(english.confidence, score.confidence)

    def test_a_short_fragment_cannot_claim_a_solve(self):
        for fragment in ("SOONO", "NESSN", "ESENE"):
            with self.subTest(fragment=fragment):
                self.assertLessEqual(self.model.score(fragment).confidence, FRAGMENT_CAP)

    def test_short_but_real_text_is_still_solved(self):
        self.assertTrue(self.model.score("ATTACKATDAWN").solved)

    def test_empty_input_is_scored_not_crashed(self):
        for text in ("", "12345", "!!!"):
            with self.subTest(text=text):
                score = self.model.score(text)
                self.assertLessEqual(score.confidence, SOLVED_CONFIDENCE)

    def test_search_fitness_is_bounded_for_long_input(self):
        # search_fitness expects an already-normalised stream -- that is what the
        # hill climbers hand it -- and only ever scores a window of it.
        long_text = letters_only(ENGLISH) * 40
        value = self.model.search_fitness(long_text)
        self.assertGreater(value, FITNESS_BAD)
        self.assertLess(value, 0.0)
        short = self.model.search_fitness(letters_only(ENGLISH))
        # Same window, so nearly the same score -- the point is that 40x the text
        # does not change the answer or the cost.
        self.assertAlmostEqual(value, short, delta=0.2)

    def test_score_is_case_and_punctuation_insensitive(self):
        a = self.model.score(ENGLISH).confidence
        b = self.model.score(ENGLISH.upper().replace(",", "").replace(".", "")).confidence
        self.assertAlmostEqual(a, b, places=2)

    def test_as_dict_is_plain_data(self):
        import json

        payload = json.dumps(self.model.score(ENGLISH).as_dict())
        self.assertIn("confidence", payload)


class TestSegmentation(unittest.TestCase):
    def setUp(self):
        self.model = get_model()

    def test_segment_recovers_word_breaks(self):
        _total, words = self.model.segment("thequickbrownfox")
        self.assertEqual(words[:4], ["the", "quick", "brown", "fox"])

    def test_segment_handles_a_real_sentence(self):
        stream = letters_only(ENGLISH)[:60].lower()
        _total, words = self.model.segment(stream)
        self.assertEqual("".join(words), stream)
        self.assertGreater(len(words), 5)

    def test_word_coverage_reports_the_words_it_found(self):
        _score, coverage, words = self.model.word_coverage(letters_only(ENGLISH))
        self.assertGreater(coverage, 0.5)
        self.assertIn("archive", [w.lower() for w in words])

    def test_start_quality_rewards_a_common_opening_word(self):
        with_the = self.model.score("THEARCHIVECONTAINSTHEORIGINALMANUSCRIPTS")
        without = self.model.score("XQARCHIVECONTAINSTHEORIGINALMANUSCRIPTS")
        self.assertGreater(with_the.start_quality, without.start_quality)


if __name__ == "__main__":
    unittest.main()
