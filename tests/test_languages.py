"""Tests for the six shipped language models and language-aware solving.

English keeps its large, dictionary-equipped model; the five additions are
n-gram-only.  What has to hold:

* every model loads from the packaged data and scores its own language best
  (``detect_language`` ranks fitness views only, because the English
  dictionary view mis-ranks siblings -- French and Italian share enough
  vocabulary to cover half of each other's words);
* English's data is unchanged by the additions: the counts the existing suite
  relies on still hold, byte for byte;
* the engine accepts ``language=`` and ``solve_auto`` picks a language that
  can actually read the text.
"""

from __future__ import annotations

import os
import unittest

from buttcrack.ciphers import get
from buttcrack.engine import solve, solve_auto
from buttcrack.lang import LANGUAGES, detect_language, get_model, resolve_language
from buttcrack.selftest import LANGUAGE_SAMPLES
from buttcrack.text import letters_only

SLOW = os.environ.get("BUTTCRACK_SLOW") == "1"


class TestRegistry(unittest.TestCase):
    def test_six_languages(self):
        self.assertEqual(set(LANGUAGES), {"english", "french", "german", "italian", "latin", "spanish"})

    def test_english_is_probed_first(self):
        # Probing order in solve_auto: English first, so the common case pays
        # for exactly one probe.
        self.assertEqual(next(iter(LANGUAGES)), "english")

    def test_resolve_language_accepts_names_and_aliases(self):
        self.assertEqual(resolve_language("english"), "english")
        self.assertEqual(resolve_language("French"), "french")
        self.assertEqual(resolve_language("es"), "spanish")
        self.assertEqual(resolve_language("de-DE"), "german")

    def test_resolve_language_rejects_unknown(self):
        with self.assertRaises(ValueError):
            resolve_language("klingon")


class TestModelLoading(unittest.TestCase):
    def test_every_model_loads_with_tables(self):
        for name in LANGUAGES:
            with self.subTest(language=name):
                model = get_model(name)
                self.assertEqual(model.language, name)
                for order in (2, 3, 4):
                    self.assertGreater(model.ngram_count(order), 100, f"{name} {order}-grams missing")

    def test_models_are_cached_per_language(self):
        self.assertIs(get_model("french"), get_model("french"))
        self.assertIsNot(get_model("french"), get_model("german"))

    def test_english_data_is_unchanged(self):
        """The additions must not touch the English model the suite relies on.

        These are the counts of the original, dictionary-equipped build; if
        they move, the English files were rebuilt instead of left alone.
        """
        model = get_model("english")
        self.assertEqual(model.ngram_count(2), 676)
        self.assertEqual(model.ngram_count(3), 16_935)
        self.assertEqual(model.ngram_count(4), 258_337)
        meta = model.meta
        self.assertGreater(meta["quadgrams_distinct"], 100_000)
        self.assertGreater(len(model.words), 10_000)

    def test_only_english_has_a_dictionary(self):
        for name in LANGUAGES:
            with self.subTest(language=name):
                expected = name == "english"
                self.assertEqual(get_model(name).has_dictionary, expected)
                if expected:
                    self.assertGreater(len(get_model(name).words), 0)

    def test_ngram_floor_is_a_penalty_for_every_order(self):
        for name in LANGUAGES:
            model = get_model(name)
            with self.subTest(language=name):
                for order in (2, 3, 4):
                    self.assertLess(model.ngram_floor(order), 0.0)
                # Asking for an order the model does not carry falls back to
                # the highest one it has rather than exploding.
                self.assertAlmostEqual(model.ngram_floor(6), model.ngram_floor(4))


class TestScoring(unittest.TestCase):
    def test_native_text_scores_high_and_random_scores_low(self):
        for name, sample in LANGUAGE_SAMPLES.items():
            model = get_model(name)
            with self.subTest(language=name):
                self.assertGreaterEqual(model.score(sample).confidence, 0.6)
                self.assertLess(model.score("QXZJVKWBPZGMYFTLRQXNJVDHWCKZS" * 4).confidence, 0.1)

    def test_fitness_orders_native_language_first(self):
        for name, sample in LANGUAGE_SAMPLES.items():
            ranked = detect_language(sample, limit=len(LANGUAGES))
            with self.subTest(language=name):
                self.assertEqual(ranked[0][0], name)
                # The winner must beat English even when English is the one
                # being judged: the English model solves its siblings, so only
                # a clear margin makes the "reads as French" note honest.
                if name != "english":
                    english = dict(ranked)["english"]
                    self.assertGreater(ranked[0][1], english)


class TestEngineLanguage(unittest.TestCase):
    """The engine has to take its model from ``language=``, not default."""

    def test_solve_honours_language(self):
        sample = LANGUAGE_SAMPLES["french"]
        ciphertext = get("caesar").encrypt(sample, 11)
        report = solve(ciphertext, budget=6.0, language="french")
        self.assertTrue(report.solved)
        self.assertEqual(report.language, "french")
        self.assertEqual(letters_only(report.plaintext), sample)

    def test_report_defaults_to_english(self):
        report = solve(get("caesar").encrypt("HELLOWORLD" * 4, 3), budget=4.0)
        self.assertEqual(report.language, "english")
        self.assertIsNone(report.language_detected)

    def test_english_judging_foreign_text_gets_a_note(self):
        """The shipped English model *solves* French; the report must say so.

        Before the multi-language work the solve was silent about this: the
        confidence was English-calibrated and the word respacing meaningless,
        with nothing to tell the user a better model existed.
        """
        sample = LANGUAGE_SAMPLES["french"]
        ciphertext = get("caesar").encrypt(sample, 11)
        report = solve(ciphertext, budget=6.0, language="english")
        self.assertTrue(report.solved)
        self.assertEqual(report.language_detected, "french")
        self.assertIn("--language french", report.notes.get("language", ""))

    def test_language_as_dict_field(self):
        sample = LANGUAGE_SAMPLES["spanish"]
        ciphertext = get("caesar").encrypt(sample, 11)
        payload = solve(ciphertext, budget=6.0, language="spanish").as_dict()
        self.assertEqual(payload["language"], "spanish")
        self.assertIn("language_detected", payload)


class TestSolveAuto(unittest.TestCase):
    def test_auto_picks_the_language_that_reads_the_text(self):
        sample = LANGUAGE_SAMPLES["french"]
        ciphertext = get("caesar").encrypt(sample, 7)
        report = solve_auto(ciphertext, budget=10.0)
        self.assertTrue(report.solved)
        self.assertEqual(report.language, "french")
        self.assertEqual(letters_only(report.plaintext), sample)

    def test_auto_keeps_english_english(self):
        sample = LANGUAGE_SAMPLES["english"]
        ciphertext = get("vigenere").encrypt(sample, "LANTERN")
        # Auto's probes are wall-clock slices (min(4, budget/12) each, English
        # first), and this solve needs ~0.8s of calm-machine search.  On a CI
        # runner ~1.4x slower, a 10s budget gives the English probe a 1s slice
        # -- just short -- and the ranking then hands the remainder to a
        # foreign model whose smaller table converged to a false optimum
        # inside its own slice.  48 puts the probe at its 4s cap: ~3.6x margin
        # over what the solve needs on that runner, and the early exit still
        # fires on the first probe, so the happy path costs ~1s.
        report = solve_auto(ciphertext, budget=48.0)
        self.assertTrue(report.solved)
        self.assertEqual(report.language, "english")


@unittest.skipUnless(SLOW, "full-strength auto detection is a search, not a unit test")
class TestSolveAutoSlow(unittest.TestCase):
    def test_auto_on_a_harder_cipher(self):
        # Vigenere under a foreign model: probes cannot solve it outright, so
        # auto has to rank by what the partial readings looked like.
        sample = LANGUAGE_SAMPLES["german"]
        ciphertext = get("vigenere").encrypt(sample, "SOMMERHAUS")
        report = solve_auto(ciphertext, budget=40.0)
        self.assertTrue(report.solved)
        self.assertEqual(letters_only(report.plaintext), sample)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
