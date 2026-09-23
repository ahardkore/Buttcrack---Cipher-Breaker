"""End-to-end tests for the solver: ciphertext in, verdict out.

Fast cases run always.  The expensive ones (Playfair, Bifid, long substitution
searches) run only when ``BUTTCRACK_SLOW=1`` is set, so the default suite stays
under a few seconds:

    BUTTCRACK_SLOW=1 python3 -m unittest discover -s tests
"""

from __future__ import annotations

import os
import time
import unittest

from buttcrack.ciphers import get
from buttcrack.engine import STRONG_LAYER, CandidatePool, Solver, solve
from buttcrack.lang import SOLVED_CONFIDENCE, get_model
from buttcrack.results import Candidate

SLOW = os.environ.get("BUTTCRACK_SLOW") == "1"
BUDGET = 25.0
WORKERS = 2

SENTENCE = (
    "The archive contains the original manuscripts, three of which were lost during the fire of "
    "eighteen ninety two, and the catalogue that described them was destroyed as well."
)
PARAGRAPH = (
    "The council of Venice has decreed that all merchant vessels must pay the new harbour tax "
    "before entering the lagoon, and the guild of mariners has protested to the doge in writing. "
    "Every secret society in the city maintains at least one archive of forbidden documents, and "
    "the committee has decided to postpone the railway conference until further notice is issued "
    "by the board of directors. Mathematics is the language in which nature has chosen to write "
    "the universe, and every equation is a sentence waiting patiently to be understood by whoever "
    "has the patience to learn its grammar and the courage to question its oldest assumptions."
)


#: Ciphers that cannot give the exact letters back, and the fold that makes the
#: comparison fair: Bacon merges U/V and I/J, Playfair pads with X, Polybius and
#: Bifid merge I/J.  These are documented losses, not bugs.
LOSSY_FOLDS = {
    "bacon": lambda t: t.replace("V", "U").replace("J", "I"),
    "bacon_case": lambda t: t.replace("V", "U").replace("J", "I"),
    "polybius": lambda t: t.replace("J", "I"),
    "bifid": lambda t: t.replace("J", "I"),
    "playfair": lambda t: t.replace("J", "I").replace("X", ""),
}


def folded_cipher(report) -> str:
    """The cipher that actually produced the plaintext -- the last hop of the chain.

    A peeled encoding reports ``cipher="none"`` (the layer did the work), so the
    path is what names the cipher whose losses have to be folded away.
    """
    return report.path.split(" -> ")[-1] if report.path else report.cipher


def squash(text: str, cipher: str = "") -> str:
    """Letters and digits only, uppercased: the comparison normal form."""
    out = "".join(c for c in text.upper() if c.isalnum())
    return LOSSY_FOLDS.get(cipher, lambda t: t)(out)


def enc(name: str, text: str = SENTENCE, key=None) -> str:
    cipher = get(name)
    return cipher.encrypt(text, key if key is not None else cipher.info.example_key)


def code(name: str, text: str = SENTENCE) -> str:
    return get(name).encode(text)


class TestPlaintext(unittest.TestCase):
    def test_english_is_returned_unchanged(self):
        report = solve(SENTENCE, budget=8)
        self.assertTrue(report.solved)
        self.assertEqual(report.cipher, "none")
        self.assertEqual(report.plaintext, SENTENCE)
        self.assertEqual(report.path, "none")

    def test_gibberish_is_not_claimed_as_solved(self):
        report = solve("Xk9#Qv2!Lm7$Zr4@Wp8%Ty3^Bn6&Js1*Hd5", budget=6)
        self.assertFalse(report.solved)
        self.assertLess(report.confidence, SOLVED_CONFIDENCE)
        self.assertTrue(report.candidates)  # ...but it still shows its best guess

    def test_empty_input_is_handled(self):
        for text in ("", "   ", "\n\t"):
            with self.subTest(text=repr(text)):
                report = solve(text, budget=2)
                self.assertFalse(report.solved)
                self.assertEqual(report.plaintext, "")


class TestSingleCiphers(unittest.TestCase):
    def assert_solves(self, ciphertext: str, expected: str, plaintext: str = SENTENCE, budget: float = BUDGET):
        """Assert the ciphertext breaks, via ``expected`` in the decode chain."""
        report = solve(ciphertext, budget=budget, workers=WORKERS)
        self.assertTrue(
            report.solved,
            f"{expected}: confidence {report.confidence:.3f}, path {report.path}\n{report.plaintext[:120]}",
        )
        self.assertEqual(report.path, expected, f"plaintext was {report.formatted[:80]!r}")
        self.assertEqual(
            squash(report.formatted, folded_cipher(report)),
            squash(plaintext, folded_cipher(report)),
        )
        return report

    def test_shift_family(self):
        self.assert_solves(enc("caesar", key=7), "caesar")
        self.assert_solves(enc("rot13"), "rot13")
        self.assert_solves(enc("caesar", key=13), "rot13")  # shift 13 is named properly
        self.assert_solves(enc("atbash"), "atbash")
        self.assert_solves(enc("affine"), "affine")
        self.assert_solves(enc("rot47", key=47), "rot47")

    def test_polyalphabetic_family(self):
        self.assert_solves(enc("vigenere", key="SECRET"), "vigenere")
        self.assert_solves(enc("beaufort", key="LANTERN"), "beaufort")
        self.assert_solves(enc("autokey", key="PRIMER"), "autokey")
        self.assert_solves(enc("trithemius"), "trithemius")

    def test_transposition_family(self):
        self.assert_solves(enc("columnar", key="SPIES"), "columnar")
        self.assert_solves(enc("rail_fence", key=4), "rail_fence")
        self.assert_solves(enc("skip", key=3), "skip")

    def test_byte_family(self):
        # XOR writes its output as hex, so the chain is "hex -> xor".
        self.assert_solves(enc("xor_single", key=0x42), "base16 -> xor_single")
        report = self.assert_solves(enc("xor_repeating", key="KEY"), "base16 -> xor_repeating")
        self.assertIn("KEY", "".join(report.key_repr.upper().split()))

    def test_codes(self):
        self.assert_solves(code("morse"), "morse")
        self.assert_solves(code("a1z26"), "a1z26")
        self.assert_solves(code("polybius"), "polybius")
        self.assert_solves(code("bacon"), "bacon")

    def test_encodings(self):
        for name in ("base64", "base32", "base16", "base58", "base85", "url", "binary", "decimal_ascii"):
            with self.subTest(encoding=name):
                report = solve(code(name), budget=15, workers=WORKERS)
                self.assertTrue(report.solved, f"{name}: {report.confidence:.3f}")
                self.assertEqual(report.path, name)

    @unittest.skipUnless(SLOW, "set BUTTCRACK_SLOW=1 to run the expensive searches")
    def test_substitution_family(self):
        # A keyword-generated alphabet *is* a mixed alphabet, and the recovered
        # mapping is its inverse -- which is not keyword-shaped, so the generic
        # substitution attack usually wins the tie.  Both names are the right
        # answer as long as every letter comes back.
        report = solve(enc("keyword_substitution", PARAGRAPH, "GALAXY"), budget=40, workers=WORKERS)
        self.assertTrue(report.solved, f"confidence {report.confidence:.3f}, path {report.path}")
        self.assertIn(report.cipher, {"substitution", "keyword_substitution"})
        self.assertEqual(
            squash(report.formatted, folded_cipher(report)),
            squash(PARAGRAPH, folded_cipher(report)),
        )

    @unittest.skipUnless(SLOW, "set BUTTCRACK_SLOW=1 to run the expensive searches")
    def test_playfair(self):
        # Playfair is the one cipher here that is not reliably finished from
        # scratch, and the test says so instead of pretending otherwise.  A 5x5
        # grid has 25! arrangements, one misplaced cell costs ~0.9 per character
        # of fitness (five times what a wrong substitution alphabet costs), and a
        # pure-Python genetic algorithm recovers roughly nine letters in ten
        # within 90 seconds -- sometimes enough to cross the solve threshold,
        # sometimes not (measured confidence 0.26-0.66 across seeds and worker
        # counts).  What is guaranteed is the contract: the right cipher is
        # named, the reading is far better than noise, and a hinted solve is
        # exact.  Playfair also needs roughly 1500 letters; below that several
        # grids explain the ciphertext equally well.
        text = PARAGRAPH * 3
        ciphertext = enc("playfair", text, "MONARCHY")
        report = solve(ciphertext, budget=90, workers=WORKERS)
        self.assertEqual(report.cipher, "playfair")
        self.assertGreater(report.confidence, 0.15, f"plaintext was {report.plaintext[:120]!r}")
        if not report.solved:
            self.assertIn("partial", report.notes.get("caveat", ""), report.notes)
        hinted = solve(ciphertext, budget=20, workers=WORKERS, hints={"key": "MONARCHY"})
        self.assertTrue(hinted.solved, f"{hinted.confidence:.3f}")
        self.assertEqual(hinted.cipher, "playfair")
        self.assertEqual(
            squash(hinted.formatted, folded_cipher(hinted)),
            squash(text, folded_cipher(hinted)),
        )


class TestStacks(unittest.TestCase):
    """The interesting case: encodings wrapped around ciphers."""

    def assert_chain(self, ciphertext: str, chain: str, plaintext: str = SENTENCE):
        report = solve(ciphertext, budget=BUDGET, workers=WORKERS)
        self.assertTrue(report.solved, f"{chain}: confidence {report.confidence:.3f}, path {report.path}")
        self.assertEqual(report.path, chain)
        self.assertEqual(report.notes.get("decode_chain"), chain)
        self.assertEqual(
            squash(report.formatted, folded_cipher(report)),
            squash(plaintext, folded_cipher(report)),
        )
        return report

    def test_encoding_over_cipher(self):
        self.assert_chain(code("base64", enc("caesar", key=5)), "base64 -> caesar")
        self.assert_chain(code("base16", enc("vigenere", key="LAMP")), "base16 -> vigenere")
        self.assert_chain(code("base64", code("morse", "Proceed to the extraction point immediately")),
                          "base64 -> morse", "Proceed to the extraction point immediately")

    def test_encoding_over_encoding(self):
        self.assert_chain(code("base32", code("base64")), "base32 -> base64")

    def test_three_layers(self):
        inner = enc("caesar", "The signal will be given at midnight from the north tower", key=9)
        stacked = code("base32", code("base64", inner))
        report = solve(stacked, budget=BUDGET, workers=WORKERS)
        self.assertTrue(report.solved, f"{report.confidence:.3f} {report.path}")
        self.assertEqual(report.path, "base32 -> base64 -> caesar")

    def test_depth_limit_stops_the_peeler(self):
        stacked = code("base64", enc("caesar", key=5))
        report = solve(stacked, budget=10, max_depth=0)
        self.assertFalse(report.solved)

    def test_a_layer_is_peeled_before_expensive_attacks_run(self):
        # Regression: attacking first meant a substitution hill climb burned the
        # whole budget on a base64 blob before the payload was ever seen.
        stacked = code("base64", enc("caesar", key=5))
        started = time.time()
        report = solve(stacked, budget=BUDGET, workers=WORKERS)
        elapsed = time.time() - started
        self.assertTrue(report.solved)
        self.assertLess(elapsed, 5.0, "peeling a base64 layer must not wait behind a hill climb")
        self.assertNotIn("substitution", [a.cipher for a in report.attacks])


class TestReport(unittest.TestCase):
    def test_the_report_carries_its_evidence(self):
        report = solve(enc("caesar", key=7), budget=10)
        self.assertTrue(report.solved)
        self.assertGreater(report.elapsed, 0.0)
        self.assertEqual(report.budget, 10)
        self.assertTrue(report.hypotheses)
        self.assertTrue(report.attacks)
        self.assertIn("length", report.stats)
        self.assertIn("index_of_coincidence", report.stats)
        self.assertEqual(report.key_repr, "7")

    def test_the_key_is_reported_in_a_usable_form(self):
        report = solve(enc("vigenere", key="SECRET"), budget=BUDGET, workers=WORKERS)
        self.assertTrue(report.solved)
        self.assertIn("SECRET", report.key_repr.upper())
        self.assertTrue(report.notes.get("method"))

    def test_layout_is_restored_for_position_preserving_ciphers(self):
        ciphertext = enc("caesar", "Attack at dawn, and hold the bridge.", key=7)
        report = solve(ciphertext, budget=10)
        self.assertTrue(report.solved)
        self.assertEqual(report.formatted, "Attack at dawn, and hold the bridge.")

    def test_word_breaks_are_recovered_when_the_ciphertext_has_none(self):
        ciphertext = enc("columnar", SENTENCE, key="SPIES")
        report = solve(ciphertext, budget=BUDGET, workers=WORKERS)
        self.assertTrue(report.solved)
        self.assertIn(" ", report.respaced)

    def test_candidates_are_ranked_and_deduplicated(self):
        report = solve(enc("caesar", key=7), budget=10)
        confidences = [c.confidence for c in report.candidates]
        self.assertEqual(confidences, sorted(confidences, reverse=True))
        plaintexts = [c.plaintext for c in report.candidates]
        self.assertEqual(len(plaintexts), len(set(plaintexts)))

    def test_progress_is_reported_as_it_happens(self):
        messages = []

        def progress(message, fraction, extra):
            messages.append((message, fraction, extra))

        solve(enc("vigenere", key="SECRET"), budget=15, workers=1, progress=progress)
        self.assertGreater(len(messages), 3)
        self.assertTrue(all(isinstance(m, str) and m for m, _f, _e in messages))
        self.assertTrue(any("hypothesis" in m for m, _f, _e in messages))
        self.assertTrue(any("solved" in m or "finished" in m for m, _f, _e in messages))

    def test_the_answer_is_deterministic(self):
        ciphertext = enc("vigenere", key="SECRET")
        first = solve(ciphertext, budget=15, workers=WORKERS)
        second = solve(ciphertext, budget=15, workers=WORKERS)
        self.assertEqual(first.cipher, second.cipher)
        self.assertEqual(first.key_repr, second.key_repr)
        self.assertEqual(first.plaintext, second.plaintext)


class TestSolverControls(unittest.TestCase):
    def test_hints_short_circuit_the_search(self):
        ciphertext = enc("vigenere", PARAGRAPH, key="SECRET")
        report = solve(ciphertext, budget=10, hints={"key": "SECRET"})
        self.assertTrue(report.solved)
        self.assertEqual(report.cipher, "vigenere")
        self.assertLess(report.elapsed, 5.0)

    def test_a_key_length_hint_is_used(self):
        ciphertext = enc("vigenere", PARAGRAPH, key="SECRET")
        report = solve(ciphertext, budget=20, workers=WORKERS, hints={"key_length": 6})
        self.assertTrue(report.solved)
        self.assertEqual(report.cipher, "vigenere")

    def test_the_budget_is_respected(self):
        started = time.time()
        solve(enc("substitution", PARAGRAPH), budget=1.0, workers=1)
        self.assertLess(time.time() - started, 12.0)

    def test_the_attack_set_can_be_restricted(self):
        solver = Solver(budget=10, ciphers=[get("caesar")])
        report = solver.solve(enc("caesar", key=7))
        self.assertTrue(report.solved)
        self.assertEqual(report.cipher, "caesar")
        # A restricted solver must not silently run the whole registry.
        self.assertEqual({a.cipher for a in report.attacks}, {"caesar"})

    def test_exhaustive_mode_still_answers(self):
        report = solve(enc("caesar", key=7), budget=10, exhaustive=True)
        self.assertTrue(report.solved)

    def test_workers_do_not_change_the_answer(self):
        ciphertext = enc("columnar", SENTENCE, key="SPIES")
        serial = solve(ciphertext, budget=BUDGET, workers=1)
        parallel = solve(ciphertext, budget=BUDGET, workers=WORKERS)
        self.assertEqual(serial.plaintext, parallel.plaintext)

    def test_report_serialises_to_json(self):
        import json

        report = solve(enc("caesar", key=7), budget=10)
        payload = json.dumps(report.as_dict())
        self.assertIn("caesar", payload)


class TestCandidatePool(unittest.TestCase):
    def setUp(self):
        self.pool = CandidatePool(get_model())

    def test_empty_pool(self):
        self.assertIsNone(self.pool.best)
        self.assertEqual(self.pool.best_confidence, 0.0)
        self.assertFalse(self.pool.solved)
        self.assertFalse(self.pool.certain)
        self.assertEqual(self.pool.ranked(), [])

    def test_best_candidate_is_returned(self):
        weak = Candidate(plaintext="XQZ JVK WBP", cipher="caesar", key=1, confidence=0.1, fitness=-8.0)
        strong = Candidate(plaintext=SENTENCE, cipher="caesar", key=7, confidence=0.95, fitness=-4.0)
        self.pool.add(weak)
        self.assertTrue(self.pool.add(strong))
        self.assertIs(self.pool.best, strong)
        self.assertTrue(self.pool.solved)
        self.assertTrue(self.pool.certain)

    def test_identical_plaintexts_are_deduplicated(self):
        first = Candidate(plaintext=SENTENCE, cipher="affine", key=(5, 8), confidence=0.9, fitness=-4.2)
        second = Candidate(plaintext=SENTENCE, cipher="caesar", key=7, confidence=0.9, fitness=-4.2)
        self.pool.add(first)
        self.pool.add(second)
        self.assertEqual(len(self.pool.ranked()), 1)

    def test_empty_plaintexts_are_rejected(self):
        self.assertFalse(self.pool.add(Candidate(plaintext="", cipher="caesar", key=1)))

    def test_ranking_is_limited(self):
        for i in range(70):
            self.pool.add(
                Candidate(plaintext=f"XQZJVKWBP{i:03d}ABCDE", cipher="caesar", key=i, confidence=0.1, fitness=-8.0)
            )
        self.assertLessEqual(len(self.pool.ranked(10)), 10)


class TestConstants(unittest.TestCase):
    def test_the_strong_layer_threshold_is_a_majority(self):
        self.assertGreaterEqual(STRONG_LAYER, 0.5)
        self.assertLess(STRONG_LAYER, 0.95)


if __name__ == "__main__":
    unittest.main()
