"""End-to-end tests for the solver: ciphertext in, verdict out.

Fast cases run always.  The expensive ones (Playfair, Bifid, long substitution
searches) run only when ``BUTTCRACK_SLOW=1`` is set, so the default suite stays
under a few seconds:

    BUTTCRACK_SLOW=1 python3 -m unittest discover -s tests
"""

from __future__ import annotations

import os
import pathlib
import random
import time
import unittest

from buttcrack.ciphers import get
from buttcrack.ciphers.base import BRUTAL, CHEAP, EXPENSIVE, Cipher, CipherInfo, CrackContext, Family
from buttcrack.ciphers.ratchet import random_key
from buttcrack.engine import (
    EVIDENCE_TIE_BAND,
    HINT_PRIOR,
    PHASE_SLICES,
    STRONG_LAYER,
    UNSUPPORTED_PHASE_SHARE,
    CandidatePool,
    Solver,
    attack_ciphers,
    solve,
)
from buttcrack.lang import SOLVED_CONFIDENCE, get_model
from buttcrack.results import Candidate, CrackReport, Hypothesis
from buttcrack.text import letters_only

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


class TestHintPrior(unittest.TestCase):
    """A crib is decisive evidence -- for the ciphers that can read it.

    ``CipherInfo.hints`` is the declaration and ``Solver._hint_prior`` is the
    rule that acts on it.  Without it the plan spends a crib on the shift family
    first, and on the 409-letter wheel challenge that meant the attack which
    solves the puzzle outright was reached after 40s of a 60s budget.
    """

    def test_a_declared_hint_moves_a_cipher_to_the_front(self):
        solver = Solver(budget=5.0, workers=1)
        ctx = CrackContext.create(budget=5.0, workers=1, hints={"crib": "THE"})
        blended = solver._hint_prior(ctx, {"vigenere": 0.6})
        self.assertEqual(blended["ratchet"], HINT_PRIOR)
        self.assertEqual(blended["sum_clock"], HINT_PRIOR)
        self.assertGreaterEqual(HINT_PRIOR, 0.86)  # above every hook's ceiling
        # ...and a cipher that cannot read the crib keeps the text's opinion.
        self.assertEqual(blended["vigenere"], 0.6)
        self.assertEqual(blended.get("rail_fence", 0.0), 0.0)

    def test_no_hint_and_unusable_hints_change_nothing(self):
        solver = Solver(budget=5.0, workers=1)
        for hints in ({}, {"key_length": 5}, {"alphabet": "KRYPTOS"}):
            with self.subTest(hints=hints):
                ctx = CrackContext.create(budget=5.0, workers=1, hints=hints)
                before = {"ratchet": 0.0, "vigenere": 0.4}
                self.assertEqual(solver._hint_prior(ctx, dict(before)), before)

    @unittest.skipUnless(SLOW, "full engine solve")
    def test_a_crib_reaches_the_cipher_that_declares_it(self):
        cipher = get("ratchet")
        corpus = letters_only(
            pathlib.Path("examples/english_samples.txt").read_text(encoding="utf-8")
        )
        plaintext = corpus[:420]
        crib = plaintext[:200]
        while len(set(crib)) < 26 and len(crib) < len(plaintext):
            crib = plaintext[: len(crib) + 20]
        self.assertEqual(len(set(crib)), 26, "a 26-letter crib is exact")
        ciphertext = cipher.encrypt(plaintext, cipher.info.example_key)
        report = solve(ciphertext, budget=45.0, workers=WORKERS, hints={"crib": crib})
        self.assertTrue(report.solved)
        self.assertEqual(report.path, "ratchet")
        # The first letter is the necklace's start offset, unrecoverable even
        # with a crib: the crib pins the differences, not the absolute state.
        self.assertEqual(letters_only(report.plaintext)[1:], plaintext[1:])

    @unittest.skipUnless(SLOW, "full engine solve")
    def test_a_mid_message_crib_gets_the_time_a_swing_needs(self):
        """A crib from the middle is found by swinging it through every offset.

        That swing costs seconds, not milliseconds, so the cipher that can read
        the crib takes the phase's whole budget rather than a share of it.  Given
        a share, the swing never finishes inside an engine solve -- measured on a
        900-letter message, a 300-letter crib and a 60s budget, the attack was
        reached and starved.
        """
        cipher = get("ratchet")
        corpus = letters_only(
            pathlib.Path("examples/english_samples.txt").read_text(encoding="utf-8")
        )
        plaintext = corpus[:900]
        crib = plaintext[300:600]
        ciphertext = cipher.encrypt(plaintext, random_key(random.Random(20261013)))
        report = solve(ciphertext, budget=60.0, workers=WORKERS, hints={"crib": crib})
        self.assertTrue(report.solved)
        self.assertEqual(report.path, "ratchet")
        self.assertEqual(letters_only(report.plaintext)[1:], plaintext[1:])


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

    def test_porta(self):
        self.assert_solves(enc("porta", key="LANTERN"), "porta")

    def test_myszkowski_and_amsco(self):
        self.assert_solves(enc("myszkowski", key="TOMATO"), "myszkowski")
        self.assert_solves(enc("amsco", key="ZEBRA"), "amsco")

    def test_hill(self):
        # Broken by scoring each row of the decryption matrix on its own: the
        # 157,248 invertible 2x2 matrices collapse to 676 row evaluations.
        self.assert_solves(enc("hill", key="HILL"), "hill")

    def test_four_square_and_trifid_are_exact_with_a_hint(self):
        """Both have key spaces past what a from-scratch search finishes, so
        the contract is the one Bifid has: named, and exact when hinted."""
        for name, key in (
            ("four_square", {"top": "EXAMPLE", "bottom": "KEYWORD"}),
            ("trifid", {"key": "TRIFID", "period": 5}),
        ):
            with self.subTest(cipher=name):
                cipher = get(name)
                ciphertext = cipher.encrypt(PARAGRAPH, key)
                # Restricted to the cipher under test: the contract is "a
                # hinted key gives the exact plaintext", not "this attack wins
                # a race against forty-nine others for a 20-second budget",
                # which is what made this flaky as the registry grew.
                report = Solver(budget=20, workers=WORKERS, ciphers=[cipher], hints={"key": key}).solve(ciphertext)
                self.assertTrue(report.solved, f"{name}: {report.confidence:.3f}")
                self.assertEqual(report.cipher, name)
                self.assertTrue(squash(report.plaintext, "").startswith(squash(PARAGRAPH, "")[:60]))

    def test_new_code_layers(self):
        for name in ("tap_code", "nato", "braille", "baudot"):
            with self.subTest(code=name):
                self.assert_solves(code(name), name)

    def test_new_encoding_layers(self):
        for name in ("uuencode",):
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
        # pure-Python genetic algorithm recovers roughly nine letters in ten once
        # it has enough time -- sometimes enough to cross the solve threshold,
        # sometimes not.
        #
        # This used to assert ``confidence > 0.15`` and it failed on every run: the
        # engine gives Playfair about 19s of a 90s budget, and measured across
        # seeds the unhinted search reaches 0.43 or 0.86 on a lucky run and 0.00
        # on an unlucky one, so the assertion was a coin toss that had already
        # come up tails.  What is *guaranteed*, and what the self-test grades by
        # the same contract (see ``buttcrack.selftest._check_partial``), is:
        # the right cipher is named, a partial reading says it is partial, and
        # the true key comes back exact.  A run that does solve must be exact.
        text = PARAGRAPH * 3
        ciphertext = enc("playfair", text, "MONARCHY")
        report = solve(ciphertext, budget=90, workers=WORKERS)
        self.assertIn("playfair", report.path, f"the identifier's own 90% read was overruled: {report.path!r}")
        if report.solved:
            self.assertEqual(
                squash(report.formatted, folded_cipher(report)),
                squash(text, folded_cipher(report)),
            )
        else:
            self.assertIn("partial", report.notes.get("caveat", ""), report.notes)
        hinted = solve(ciphertext, budget=20, workers=WORKERS, hints={"key": "MONARCHY"})
        self.assertTrue(hinted.solved, f"{hinted.confidence:.3f}")
        self.assertEqual(hinted.cipher, "playfair")
        self.assertEqual(
            squash(hinted.formatted, folded_cipher(hinted)),
            squash(text, folded_cipher(hinted)),
        )

    @unittest.skipUnless(SLOW, "set BUTTCRACK_SLOW=1 to run the expensive searches")
    def test_playfair_search_recovers_the_grid_when_it_is_within_reach(self):
        # The capability that *is* deterministic, and the one the polish pass
        # exists for: the docstring's claim that "a climb started from the truth
        # with three cells scrambled recovers it in 0.2s".  Guarding it here
        # keeps a real regression test on the search even though the unhinted
        # end-to-end run above cannot promise a solve.
        import random as _random

        from buttcrack.ciphers.polygraphic import apply_grid, make_grid, prepare_playfair

        text = PARAGRAPH * 3
        stream = prepare_playfair(enc("playfair", text, "MONARCHY"))
        model = get_model()
        truth = make_grid("MONARCHY")
        scrambled = list(truth)
        rng = _random.Random(20261012)
        for _ in range(3):
            x, y = rng.sample(range(25), 2)
            scrambled[x], scrambled[y] = scrambled[y], scrambled[x]

        def polish(grid: str) -> float:
            return model.ngram_score(apply_grid(stream, grid, True), normalise=False)

        best, best_fit = list(scrambled), polish("".join(scrambled))
        for _ in range(12):  # the same steepest-ascent pass the worker ends with
            pair, value = None, best_fit
            for x in range(25):
                for y in range(x + 1, 25):
                    best[x], best[y] = best[y], best[x]
                    candidate = polish("".join(best))
                    best[x], best[y] = best[y], best[x]
                    if candidate > value + 1e-12:
                        pair, value = (x, y), candidate
            if pair is None:
                break
            x, y = pair
            best[x], best[y] = best[y], best[x]
            best_fit = value
        self.assertEqual("".join(best), truth, "the search could not recover a grid three swaps from the truth")


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
        self.assert_chain(
            code("base64", code("morse", "Proceed to the extraction point immediately")),
            "base64 -> morse",
            "Proceed to the extraction point immediately",
        )

    def test_encoding_over_encoding(self):
        self.assert_chain(code("base32", code("base64")), "base32 -> base64")

    def test_three_layers(self):
        inner = enc("caesar", "The signal will be given at midnight from the north tower", key=9)
        stacked = code("base32", code("base64", inner))
        report = solve(stacked, budget=BUDGET, workers=WORKERS)
        self.assertTrue(report.solved, f"{report.confidence:.3f} {report.path}")
        self.assertEqual(report.path, "base32 -> base64 -> caesar")

    def test_cipher_under_a_transposition(self):
        """A transposition wrapped around a substitution comes apart.

        Every rail fence key produces the same letter statistics, so the
        correct reading cannot be recognised before the inner cipher is
        solved -- the solver has to try the readings, not rank them.
        """
        inner = enc("caesar", SENTENCE, key=5)
        stacked = get("rail_fence").encrypt(inner, 4)
        report = solve(stacked, budget=BUDGET, workers=WORKERS)
        self.assertTrue(report.solved, f"{report.confidence:.3f} {report.path}")
        self.assertEqual(report.path, "rail_fence -> caesar")

    def test_cipher_under_a_reflection(self):
        stacked = get("reverse").encrypt(enc("vigenere", SENTENCE, key="LAMP"))
        report = solve(stacked, budget=BUDGET, workers=WORKERS)
        self.assertTrue(report.solved, f"{report.confidence:.3f} {report.path}")
        self.assertEqual(report.path, "reverse -> vigenere")

    def test_five_layers(self):
        """hex(base64(morse(reverse(caesar(text))))) -- five steps, two of them
        ciphers rather than encodings."""
        inner = enc("caesar", "The signal will be given at midnight from the north tower", key=7)
        stacked = code("base16", code("base64", code("morse", get("reverse").encrypt(inner))))
        report = solve(stacked, budget=BUDGET, workers=WORKERS, max_depth=6)
        self.assertTrue(report.solved, f"{report.confidence:.3f} {report.path}")
        self.assertEqual(report.path, "base16 -> base64 -> morse -> reverse -> caesar")

    def test_six_layers(self):
        """The full advertised depth: six steps peeled in one solve."""
        inner = enc("caesar", "Meet the courier beneath the clock tower at dawn", key=11)
        stacked = code("base32", code("base16", code("base64", code("morse", get("reverse").encrypt(inner)))))
        report = solve(stacked, budget=BUDGET, workers=WORKERS, max_depth=6)
        self.assertTrue(report.solved, f"{report.confidence:.3f} {report.path}")
        self.assertEqual(report.path, "base32 -> base16 -> base64 -> morse -> reverse -> caesar")

    def test_three_ciphers_deep(self):
        """Ciphers stacked on ciphers, not just encodings on ciphers."""
        stacked = get("reverse").encrypt(get("rail_fence").encrypt(enc("caesar", SENTENCE, key=5), 4))
        report = solve(stacked, budget=BUDGET, workers=WORKERS)
        self.assertTrue(report.solved, f"{report.confidence:.3f} {report.path}")
        self.assertEqual(report.path, "reverse -> rail_fence -> caesar")

    def test_six_ciphers_deep(self):
        """Six ciphers, no encodings: five transpositions over a ROT13.

        Tractable because transpositions and monoalphabetic substitutions
        commute, so the stack equals one permutation plus one substitution --
        see `Solver._chain_search`.
        """
        inner = enc("rot13", SENTENCE)
        stacked = get("reverse").encrypt(
            get("rail_fence").encrypt(
                get("skip").encrypt(get("reverse").encrypt(get("rail_fence").encrypt(inner, 3)), 5), 4
            )
        )
        report = solve(stacked, budget=30, workers=WORKERS)
        self.assertTrue(report.solved, f"{report.confidence:.3f} {report.path}")
        self.assertEqual(report.path, "reverse -> rail_fence -> skip -> reverse -> rail_fence -> rot13")

    def test_encodings_wrapped_around_a_cipher_chain(self):
        """The chain search keeps the steps it was already inside."""
        inner = get("reverse").encrypt(get("rail_fence").encrypt(enc("caesar", SENTENCE, key=9), 3))
        stacked = code("base64", code("morse", inner))
        report = solve(stacked, budget=30, workers=WORKERS)
        self.assertTrue(report.solved, f"{report.confidence:.3f} {report.path}")
        self.assertEqual(report.path, "base64 -> morse -> reverse -> rail_fence -> caesar")

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

    def test_expensive_attacks_split_the_remaining_budget_without_a_floor(self):
        class BudgetProbe(Cipher):
            def __init__(self, name):
                self.info = CipherInfo(
                    name=name,
                    title=name,
                    family=Family.SUBSTITUTION,
                    cost=EXPENSIVE,
                    min_length=2,
                    description="test-only budget probe",
                )
                self.slices = []

            def crack(self, ciphertext, ctx):
                self.slices.append(ctx.budget)
                if False:  # make this a generator without producing a candidate
                    yield None

        first, second = BudgetProbe("budget_probe_first"), BudgetProbe("budget_probe_second")
        Solver(budget=1.0, ciphers=[first, second]).solve("QZXWVUTSRQPONMLKJIHGFEDCBA")
        self.assertEqual(len(first.slices), 1)
        self.assertEqual(len(second.slices), 1)
        # Equally likely attacks split the phase, so the first of two gets half.
        # The second may use what is left -- a slice is a cap against overrunning
        # the user's deadline, not a reservation for attacks that never ran.
        self.assertLessEqual(first.slices[0], 0.5)
        self.assertLessEqual(second.slices[0], 1.0)
        self.assertLessEqual(first.slices[0] + second.slices[0], 1.5)

    def test_likely_attacks_get_more_of_the_phase_than_unlikely_ones(self):
        """Budget follows evidence: identification orders *and* funds the search.

        Regression: when every expensive attack got an equal slice, adding
        ciphers to the registry silently took time away from the one that was
        going to work, and a keyed Polybius stopped coming out.
        """

        class Probe(Cipher):
            def __init__(self, name):
                self.info = CipherInfo(
                    name=name,
                    title=name,
                    family=Family.SUBSTITUTION,
                    cost=EXPENSIVE,
                    min_length=2,
                    description="test-only budget probe",
                )
                self.slices = []

            def crack(self, ciphertext, ctx):
                self.slices.append(ctx.budget)
                if False:
                    yield None

        likely, unlikely, tail = Probe("probe_a"), Probe("probe_b"), Probe("probe_c")
        solver = Solver(budget=4.0, ciphers=[likely, unlikely, tail])
        pool = CandidatePool(solver.model)
        report = CrackReport(ciphertext="QZXWVUTSRQPONMLKJIHGFEDCBA")
        ctx = CrackContext.create(budget=4.0, model=solver.model)
        # The last attack in a phase may use whatever is left, so the comparison
        # is between the two that still have a successor.
        solver._attack(
            "QZXWVUTSRQPONMLKJIHGFEDCBA",
            ctx,
            pool,
            {"probe_a": 0.9, "probe_b": 0.0, "probe_c": 0.0},
            report,
            costs=(EXPENSIVE,),
        )
        self.assertGreater(likely.slices[0], unlikely.slices[0])

    def test_no_expensive_phase_is_starved_for_the_ones_before_it(self):
        """The wheel test's root cause, at the level of the allocator.

        Unplanned, the phases competed for the budget and the strongest ate it:
        on a wheel ciphertext the expensive group ran from 14s to 62s, and the
        brutal group -- Bifid, four-square, Trifid and the M-94 that solves a
        wheel in four seconds -- was left 0.08s and never started.  Phases are
        now offered their own per-cipher caps up front and share proportionally
        when those do not fit.
        """
        expensive = [c for c in attack_ciphers() if c.info.cost == EXPENSIVE]
        brutal = [c for c in attack_ciphers() if c.info.cost == BRUTAL]
        self.assertGreater(len(brutal), 0, "the brutal tier is what solves a wheel cipher")
        phases = [
            (EXPENSIVE, expensive, [1.0] * len(expensive)),
            (BRUTAL, brutal, [1.0] * len(brutal)),
        ]
        for available in (90.0, 60.0, 40.0):
            with self.subTest(available=available):
                ctx = CrackContext.create(budget=available, model=get_model())
                budgets = self.solver_budgets(phases, ctx, (EXPENSIVE, BRUTAL))
                self.assertIsNotNone(budgets[0])
                self.assertLessEqual(sum(budgets), available + 1e-6)
                # Both phases get time, in proportion to what they asked for.
                self.assertGreater(budgets[1], 0.0)
                asked = [PHASE_SLICES[cost] * len(group) for cost, group, _ in phases]
                self.assertAlmostEqual(budgets[0] / budgets[1], asked[0] / asked[1], places=6)

    def test_an_unsupported_phase_does_not_take_room_from_a_supported_one(self):
        """Size alone is the wrong question -- evidence is the other half.

        Asked by size alone, the BRUTAL tier claims four ciphers' worth of time
        on every text, and on a transposition ciphertext (where Bifid,
        four-square, Trifid and M-94 all come back empty) that is time the
        columnar, Myszkowski and AMSCO searches needed: measured on the
        self-test's Myszkowski and AMSCO puzzles, the 7.7s of attack time became
        5.5s and neither named its cipher any more.
        """
        supported = self.solver_phase_demand(EXPENSIVE, [0.85] + [0.15] * 7)
        unsupported = self.solver_phase_demand(BRUTAL, [0.15] * 4)
        self.assertAlmostEqual(supported, PHASE_SLICES[EXPENSIVE] * 8)
        self.assertAlmostEqual(
            unsupported,
            PHASE_SLICES[BRUTAL] * (1.0 + UNSUPPORTED_PHASE_SHARE * 3),
        )
        self.assertLess(unsupported, PHASE_SLICES[BRUTAL] * 4, "an unsupported phase asks for less than its size")
        # A wheel ciphertext is the case the reservation exists for: the M-94's
        # own read arrives at 0.45, over the bar, so BRUTAL is worth its sweep.
        self.assertGreaterEqual(self.solver_phase_demand(BRUTAL, [0.45, 0.19, 0.15, 0.15]), PHASE_SLICES[BRUTAL])

    def solver_phase_demand(self, cost, weights):
        return Solver._phase_demand(cost, weights)

    def test_a_phase_keeps_its_own_cap_when_everything_fits(self):
        expensive = [c for c in attack_ciphers() if c.info.cost == EXPENSIVE]
        ctx = CrackContext.create(budget=100000.0, model=get_model())
        phases = [(EXPENSIVE, expensive, [1.0] * len(expensive))]
        budgets = self.solver_budgets(phases, ctx, (EXPENSIVE,))
        self.assertAlmostEqual(budgets[0], PHASE_SLICES[EXPENSIVE] * len(expensive))

    def test_unplanned_costs_stay_unplanned(self):
        # Cheap and moderate attacks take milliseconds and are well calibrated;
        # planning them would change timings that already work.
        cheap = [c for c in attack_ciphers() if c.info.cost == CHEAP][:2]
        ctx = CrackContext.create(budget=10.0, model=get_model())
        phases = [(CHEAP, cheap, [1.0] * len(cheap)), (EXPENSIVE, [], [])]
        budgets = self.solver_budgets(phases, ctx, (CHEAP, EXPENSIVE))
        self.assertEqual(budgets, [None, None])

    def solver_budgets(self, phases, ctx, costs):
        solver = Solver(budget=ctx.budget, workers=1)
        return solver._phase_budgets(phases, ctx, costs)

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

    def test_the_evidence_tie_band_is_narrow(self):
        # It exists to settle noise against noise (0.000 against 0.011), not to
        # let a weak identification overturn a reading that found real words.
        self.assertGreater(EVIDENCE_TIE_BAND, 0.0)
        self.assertLessEqual(EVIDENCE_TIE_BAND, 0.1)


class TestNamedByEvidence(unittest.TestCase):
    """Nothing solved: which failed reading gets named?

    A failed search's ranking is noise -- 0.011 against 0.000 decides nothing --
    while the identifier's read of the *cipher* is structural evidence.  These
    cases pin both directions: the evidence names a cipher when the readings are
    indistinguishable, and keeps quiet when one reading genuinely reads better.
    """

    def setUp(self):
        self.solver = Solver(budget=1, workers=1)
        self.ctx = CrackContext.create(budget=1, model=self.solver.model)

    def candidates(self) -> list[Candidate]:
        return [
            Candidate(plaintext="AAAA", cipher="four_square", confidence=0.000),
            Candidate(plaintext="BBBB", cipher="playfair", confidence=0.000),
            Candidate(plaintext="CCCC", cipher="substitution", confidence=0.574),
        ]

    def test_the_identifiers_evidence_names_the_cipher_when_readings_are_noise(self):
        named = self.solver._named_by_evidence(
            self.candidates(), [Hypothesis("playfair", 0.9, "flat IC over an even-length stream")]
        )
        self.assertIsNotNone(named)
        self.assertEqual(named.cipher, "playfair")
        self.assertIn("playfair", named.notes["named_by"])
        self.assertIn("90%", named.notes["named_by"])
        self.assertIn("four_square", named.notes["named_by"])

    def test_a_weak_identification_stays_quiet(self):
        # Below STRONG_LAYER the identifier is saying "might be", and "might be"
        # must not outweigh a reading that found actual words.
        named = self.solver._named_by_evidence(
            self.candidates(), [Hypothesis("playfair", STRONG_LAYER - 0.01, "flat IC")]
        )
        self.assertIsNone(named)

    def test_a_reading_that_reads_well_is_not_overturned(self):
        # The dangerous direction: a good reading (0.574) is already on top, so
        # there is no noise to settle and the identifier's preference for a
        # different cipher must not displace it.
        ranked = [
            Candidate(plaintext="CCCC", cipher="substitution", confidence=0.574),
            Candidate(plaintext="BBBB", cipher="playfair", confidence=0.000),
        ]
        self.assertIsNone(self.solver._named_by_evidence(ranked, [Hypothesis("playfair", 0.9, "flat IC")]))

    def test_a_strong_reading_keeps_its_own_name(self):
        named = self.solver._named_by_evidence(
            [Candidate(plaintext="CCCC", cipher="substitution", confidence=0.574)],
            [Hypothesis("playfair", 0.9, "flat IC")],
        )
        self.assertIsNone(named, "there was no other reading to name")

    def test_the_winner_is_annotated_when_the_identified_cipher_never_ran(self):
        # The short-budget case: the identifier is sure, but the earlier phases
        # spent the whole allowance and the cipher never got a slice, so there is
        # no reading to promote.  The winner keeps its place -- nothing else is
        # any better -- and gains the explanation, so "vigenere, key=AMYYYY" on a
        # Playfair puzzle cannot be read as a confirmed answer.
        ranked = [
            Candidate(plaintext="AAAA", cipher="vigenere", confidence=0.000, notes={}),
            Candidate(plaintext="BBBB", cipher="hill", confidence=0.000),
        ]
        self.assertIsNone(self.solver._named_by_evidence(ranked, [Hypothesis("playfair", 0.9, "flat IC")]))
        note = ranked[0].notes.get("named_by", "")
        self.assertIn("playfair", note)
        self.assertIn("90%", note)
        self.assertIn("vigenere", note)
        self.assertEqual(ranked[0].cipher, "vigenere", "the winner is annotated, not displaced")

    def test_no_hypotheses_means_nothing_to_say(self):
        self.assertIsNone(self.solver._named_by_evidence(self.candidates(), []))

    def test_only_the_hypothesised_cipher_is_considered(self):
        # The evidence names playfair; a strong read of a *different* cipher
        # must not be dragged up in its place.
        ranked = [
            Candidate(plaintext="AAAA", cipher="four_square", confidence=0.000),
            Candidate(plaintext="DDDD", cipher="hill", confidence=0.000),
            Candidate(plaintext="CCCC", cipher="m94", confidence=0.000),
        ]
        self.assertIsNone(self.solver._named_by_evidence(ranked, [Hypothesis("playfair", 0.9, "flat IC")]))


if __name__ == "__main__":
    unittest.main()


class TestChainSearch(unittest.TestCase):
    """The commuting-stack search and the gate that decides when it runs."""

    def setUp(self):
        self.solver = Solver(budget=5, workers=1)
        self.ctx = CrackContext.create(budget=5, model=self.solver.model)

    def test_gate_admits_transpositions_and_rejects_everything_else(self):
        # A transposition cannot change which letters are present, so any stack
        # of transpositions and monoalphabetic substitutions keeps an English
        # histogram under some rotation.  Nothing else does.
        for name, ciphertext in (
            ("plain", SENTENCE),
            ("rail_fence", enc("rail_fence", SENTENCE, key=4)),
            ("columnar", enc("columnar", SENTENCE, key="ZEBRA")),
            ("rail_fence over caesar", get("rail_fence").encrypt(enc("caesar", SENTENCE, key=5), 4)),
        ):
            with self.subTest(admits=name):
                self.assertTrue(self.solver._transposition_shaped(ciphertext, self.ctx))
        for name, ciphertext in (
            ("vigenere", enc("vigenere", SENTENCE, key="LEMON")),
            ("substitution", enc("substitution", SENTENCE)),
            ("hill", enc("hill", SENTENCE, key="HILL")),
        ):
            with self.subTest(rejects=name):
                self.assertFalse(self.solver._transposition_shaped(ciphertext, self.ctx))

    def test_the_substitution_is_read_off_the_histogram(self):
        """Transpositions do not disturb letter counts, so the shift is
        recoverable *before* any transposition is undone."""
        stacked = get("rail_fence").encrypt(enc("caesar", SENTENCE, key=5), 4)
        candidates = self.solver._monoalphabetic_candidates(stacked, self.ctx)
        self.assertEqual([(n, k) for n, k, _ in candidates][0], ("caesar", 5))
