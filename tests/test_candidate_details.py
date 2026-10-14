"""Ranking evidence is explanatory; score and round-trip never become proof."""

from __future__ import annotations

import json
import unittest
from unittest import mock

from buttcrack.candidate_details import profile, verification
from buttcrack.ciphers import get
from buttcrack.engine import CandidatePool, Solver, solve_auto
from buttcrack.lang import get_model
from buttcrack.paradigm import RECORDS, exact_candidate
from buttcrack.results import Candidate, CrackReport

MODEL = get_model()
PLAIN = "THEARCHIVECONTAINSTHEORIGINALMANUSCRIPTSANDTHREELETTERS"


def reading(text=PLAIN, key=7, confidence=.9, fitness=-4.2, notes=None):
    return Candidate(text, "caesar", key, confidence, fitness, MODEL.score(text), notes=notes or {})


class VerificationTests(unittest.TestCase):
    def test_dictionary_unassessed_is_distinct_from_zero_coverage(self):
        self.assertTrue(MODEL.score(PLAIN).as_dict()["dictionary_assessed"])
        self.assertFalse(MODEL.score(PLAIN, with_words=False).as_dict()["dictionary_assessed"])

    def test_good_score_alone_does_not_verify(self):
        result = profile(reading(confidence=1.0))
        self.assertFalse(result["statistical_plausibility"]["is_probability"])
        self.assertEqual(result["verification"]["status"], "not_checked")
        self.assertFalse(result["verification"]["intended_plaintext_proven"])

    def test_round_trip_is_reproduction_not_independent_proof(self):
        cipher = get("caesar")
        original = cipher.encrypt(PLAIN, 7)
        result = verification(reading(), original)
        self.assertEqual(result["status"], "reproduced")
        self.assertEqual(result["normalization"], "exact characters")
        self.assertFalse(result["independent_verification"])
        self.assertFalse(result["intended_plaintext_proven"])
        # A different key's incorrect reading still reproduces the ciphertext.
        wrong = reading(cipher.decrypt(original, 8), key=8)
        self.assertEqual(verification(wrong, original)["status"], "reproduced")
        self.assertFalse(verification(wrong, original)["intended_plaintext_proven"])

    def test_wrong_candidate_reports_mismatch(self):
        result = verification(reading(key=8), get("caesar").encrypt(PLAIN, 7))
        self.assertEqual(result["round_trip"], "failed")
        self.assertEqual(result["status"], "mismatch")

    def test_normalization_is_disclosed(self):
        original = get("caesar").encrypt("The archive contains the original manuscripts and three letters.", 7)
        result = verification(reading(), original)
        self.assertEqual(result["round_trip"], "passed")
        self.assertIn("punctuation ignored", result["normalization"])

    def test_layered_readings_do_not_claim_full_chain_checks(self):
        candidate = reading()
        candidate.steps = ("base64",)
        result = verification(candidate, "whatever")
        self.assertEqual(result["status"], "not_checked")
        self.assertIn("outer-layer key", result["detail"])

    def test_unsupported_key_is_not_verification_failure_claim(self):
        result = verification(reading(key={"invalid": "key"}), "whatever")
        self.assertEqual(result["status"], "not_checked")

    def test_forged_verification_note_is_ignored(self):
        candidate = reading(notes={"verification_status": "verified exact match", "independent_recheck": True})
        self.assertEqual(profile(candidate)["verification"]["status"], "not_checked")
        self.assertFalse(verification(candidate, "bad input")["independent_verification"])

    def test_corpus_match_requires_real_input_plaintext_and_key(self):
        record = RECORDS[0]
        candidate = exact_candidate(record.ciphertext, MODEL)
        result = verification(candidate, record.ciphertext)
        self.assertEqual(result["status"], "corpus_match")
        self.assertEqual(result["record"], record.challenge_id)
        self.assertEqual(result["round_trip"], "documented_in_corpus")
        self.assertFalse(result["independent_verification"])
        self.assertEqual(verification(candidate, "wrong input")["status"], "not_checked")
        candidate.plaintext += "X"
        self.assertEqual(verification(candidate, record.ciphertext)["status"], "not_checked")


class DescriptionTests(unittest.TestCase):
    def test_raw_key_parameters_and_family(self):
        candidate = Candidate("TEXT", "vigenere", {"key": "LEMON"}, notes={"key_length": 5, "method": "test"})
        payload = candidate.as_dict()
        self.assertEqual(payload["family"], "polyalphabetic")
        self.assertEqual(payload["key_data"], {"key": "LEMON"})
        self.assertEqual(payload["parameters"]["key_length"], 5)
        self.assertEqual(payload["parameters"]["key"], "LEMON")
        encoded = Candidate("TEXT", "xor_repeating", b"\xff\x00").as_dict()
        self.assertEqual(encoded["key_data"], {"encoding": "hex", "value": "ff00"})
        json.dumps(encoded)

    def test_close_competitors_and_actual_sort_explanation(self):
        first, second, third = reading(confidence=.9), reading(key=8, confidence=.88), reading(key=9, confidence=.5)
        report = CrackReport("CIPHER", best=first, candidates=[first, second, third])
        data = report.as_dict()
        self.assertEqual(data["candidate_comparison"]["close_ranks"], [2])
        self.assertEqual(data["candidates"][0]["ranking"]["close_peers"], [2])
        self.assertAlmostEqual(data["candidates"][1]["ranking"]["gap_to_leader"], .02)
        self.assertIn("ahead of #2", data["best"]["ranking"]["reasons"][0])
        self.assertIn("rank score", data["candidates"][1]["ranking"]["reasons"][0])

    def test_fitness_only_breaks_rounded_rank_score_ties(self):
        first, second = reading(fitness=-4.2), reading(key=8, fitness=-4.8)
        report = CrackReport("", best=first, candidates=[first, second])
        self.assertIn("n-gram fitness", report.as_dict()["candidates"][1]["ranking"]["reasons"][0])

    def test_identification_override_does_not_hide_negative_score_gap(self):
        named = reading(confidence=.2, notes={"named_by": "identifier prefers this family, both readings still weak"})
        competitor = reading(key=8, confidence=.22)
        report = CrackReport("", best=named, candidates=[named, competitor])
        data = report.as_dict()
        self.assertLess(data["candidates"][1]["ranking"]["gap_to_leader"], 0)
        self.assertIn("identification", data["best"]["ranking"]["reasons"][0])
        self.assertEqual(data["candidate_comparison"]["close_ranks"], [2])

    def test_truncation_does_not_change_checks_or_ranking(self):
        candidate = reading()
        report = CrackReport(get("caesar").encrypt(PLAIN, 7), best=candidate, candidates=[candidate])
        data = report.as_dict(plaintext_limit=5, max_candidates=10)
        self.assertEqual(data["best"]["plaintext"], PLAIN[:5])
        self.assertEqual(data["best"]["verification"]["round_trip"], "passed")
        self.assertEqual(data["candidate_comparison"]["returned"], 1)
        self.assertEqual(report.best.plaintext, PLAIN)

    def test_empty_report_and_missing_measurements(self):
        self.assertEqual(CrackReport("").as_dict()["candidates"], [])
        candidate = Candidate("TEXT", "unknown", confidence=.5)
        data = CrackReport("", best=candidate, candidates=[candidate]).as_dict()
        self.assertIsNone(data["best"]["statistical_plausibility"]["language_score"])
        self.assertIn("No language-score breakdown", data["best"]["ranking"]["reasons"][1])


class ComparisonSearchTests(unittest.TestCase):
    def test_comparison_does_not_stop_pool_at_high_language_score(self):
        pool = CandidatePool(MODEL, stop_on_confidence=False)
        pool.add(reading(confidence=.99))
        self.assertTrue(pool.solved)
        self.assertFalse(pool.certain)

    def test_same_prefix_is_not_a_duplicate_reading(self):
        pool = CandidatePool(MODEL)
        pool.add(reading("A" * 160 + "FIRSTENDING"))
        pool.add(reading("A" * 160 + "SECONDENDING"))
        self.assertEqual(len(pool.ranked()), 2)

    def test_real_caesar_retains_ten_readings(self):
        text = get("caesar").encrypt(PLAIN, 7)
        result = Solver(budget=.5, ciphers=[get("caesar")], compare=True).solve(text)
        self.assertEqual(result.plaintext, PLAIN)
        data = result.as_dict(max_candidates=10)
        self.assertEqual(len(data["candidates"]), 10)
        self.assertEqual(data["candidate_comparison"]["search_mode"], "comparison")
        self.assertEqual([c["ranking"]["rank"] for c in data["candidates"]], list(range(1, 11)))

    def test_auto_language_refines_probe_in_comparison_mode(self):
        probe = CrackReport("TEXT", best=reading(), solved=True, language="english")
        expanded = CrackReport("TEXT", best=reading(), candidates=[reading()], comparison_mode=True)
        with mock.patch("buttcrack.engine.solve", side_effect=[probe, expanded]) as solve:
            result = solve_auto("TEXT", budget=5, compare=True)
        self.assertIs(result, expanded)
        self.assertTrue(solve.call_args.kwargs["compare"])
        self.assertEqual(result.budget, 5)

    def test_verified_corpus_does_not_invent_competitors(self):
        record = RECORDS[0]
        result = Solver(budget=.5, compare=True).solve(record.ciphertext).as_dict(max_candidates=10)
        self.assertEqual(len(result["candidates"]), 1)
        self.assertTrue(result["candidate_comparison"]["corpus_shortcut"])


if __name__ == "__main__":
    unittest.main()
