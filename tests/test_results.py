"""Tests for the result types: ranking, key formatting and the evidence rules."""

from __future__ import annotations

import json
import time
import unittest

from buttcrack.lang import SOLVED_CONFIDENCE, get_model
from buttcrack.results import (
    EVIDENCE_CAP,
    AttackLog,
    Candidate,
    CrackReport,
    Hypothesis,
    evidence_shortfall,
    key_entropy_bits,
)

MODEL = get_model()
ENGLISH = "The archive contains the original manuscripts and three letters"


def candidate(plaintext=ENGLISH, cipher="caesar", key=7, confidence=0.9, fitness=-4.2, steps=()):
    return Candidate(
        plaintext=plaintext,
        cipher=cipher,
        key=key,
        confidence=confidence,
        fitness=fitness,
        score=MODEL.score(plaintext),
        steps=steps,
    )


class TestKeyRepr(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(candidate(key=None).key_repr, "-")
        self.assertEqual(candidate(key=7).key_repr, "7")
        self.assertEqual(candidate(key="LEMON").key_repr, "LEMON")
        self.assertEqual(candidate(key=(5, 8)).key_repr, "5,8")
        self.assertEqual(candidate(key=b"\x41\x42").key_repr, "AB")
        self.assertEqual(candidate(key={"key": "SECRET", "period": 7}).key_repr, "key=SECRET,period=7")

    def test_undecodable_bytes_fall_back_to_hex(self):
        self.assertEqual(candidate(key=b"\xff\xfe").key_repr, "fffe")


class TestRanking(unittest.TestCase):
    def test_higher_confidence_wins(self):
        weak = candidate(confidence=0.5)
        strong = candidate(confidence=0.95)
        self.assertLess(strong.sort_key(), weak.sort_key())

    def test_tiny_confidence_differences_are_noise(self):
        # 0.900 vs 0.9004 is model noise, not evidence: the tie-break must be
        # something else (here, the shorter decode chain).
        a = candidate(confidence=0.9, steps=())
        b = candidate(confidence=0.9004, steps=("base64",))
        self.assertLess(a.sort_key(), b.sort_key())

    def test_fewer_steps_win_a_tie(self):
        direct = candidate(confidence=0.9, steps=())
        layered = candidate(confidence=0.9, steps=("base64", "base32"))
        self.assertLess(direct.sort_key(), layered.sort_key())

    def test_a_good_opening_word_breaks_a_transposition_rotation_tie(self):
        good_start = candidate(plaintext="THEARCHIVECONTAINS", confidence=0.9)
        rotated = candidate(plaintext="EARCHIVECONTAINSTH", confidence=0.9)
        self.assertLess(good_start.sort_key(), rotated.sort_key())

    def test_solved_and_certain_flags(self):
        self.assertTrue(candidate(confidence=SOLVED_CONFIDENCE).solved)
        self.assertFalse(candidate(confidence=SOLVED_CONFIDENCE - 0.01).solved)
        self.assertTrue(candidate(confidence=0.99).certain)

    def test_path_reads_outermost_layer_first(self):
        self.assertEqual(candidate(steps=()).path, "caesar")
        self.assertEqual(candidate(steps=("base64",)).path, "base64 -> caesar")
        self.assertEqual(
            candidate(cipher="none", steps=("base64", "morse")).path, "base64 -> morse"
        )

    def test_as_dict_is_json_serialisable(self):
        payload = json.dumps(candidate(key={"key": "SECRET"}).as_dict())
        self.assertIn("SECRET", payload)


class TestKeyEntropy(unittest.TestCase):
    def test_no_key_holds_no_secret(self):
        self.assertEqual(key_entropy_bits(None), 0.0)

    def test_a_shift_holds_a_few_bits(self):
        self.assertLess(key_entropy_bits(7), 5.0)

    def test_a_keyword_holds_its_length_in_letters(self):
        self.assertAlmostEqual(key_entropy_bits("SECRET"), 28.2, places=1)

    def test_a_full_mixed_alphabet_holds_88_bits(self):
        alphabet = "QWERTYUIOPASDFGHJKLZXCVBNM"
        self.assertAlmostEqual(key_entropy_bits(alphabet), 88.4, places=1)

    def test_repetition_does_not_add_entropy(self):
        self.assertLessEqual(key_entropy_bits("MONARCHY" * 24), key_entropy_bits("QWERTYUIOPASDFGHJKLZXCVBNM"))

    def test_composite_keys_add_up(self):
        self.assertAlmostEqual(key_entropy_bits({"a": 5, "b": 8}), 2 * key_entropy_bits(5), places=6)
        self.assertAlmostEqual(key_entropy_bits((5, 8)), 2 * key_entropy_bits(5), places=6)

    def test_bytes_count_eight_bits_each(self):
        self.assertEqual(key_entropy_bits(b"KEY"), 24.0)


class TestEvidence(unittest.TestCase):
    def test_short_text_cannot_support_a_big_key(self):
        bits, letters = evidence_shortfall("ATTACKATDAWN", "QWERTYUIOPASDFGHJKLZXCVBNM")
        self.assertGreater(bits, 80)
        self.assertEqual(letters, 12)

    def test_long_text_supports_the_same_key(self):
        bits, _letters = evidence_shortfall(ENGLISH * 4, "QWERTYUIOPASDFGHJKLZXCVBNM")
        self.assertEqual(bits, 0.0)

    def test_a_shift_is_supported_by_short_text(self):
        bits, _letters = evidence_shortfall("ATTACKATDAWN", 7)
        self.assertEqual(bits, 0.0)

    def test_the_cap_sits_below_the_solve_threshold(self):
        self.assertLess(EVIDENCE_CAP, SOLVED_CONFIDENCE)


class TestReportTypes(unittest.TestCase):
    def test_hypothesis_round_trips_through_dict(self):
        hypothesis = Hypothesis("vigenere", 0.8512345, "period 6 columns look English")
        payload = hypothesis.as_dict()
        self.assertEqual(payload["cipher"], "vigenere")
        self.assertEqual(payload["likelihood"], 0.8512)

    def test_attack_log_records_what_happened(self):
        started = time.time() - 0.01
        log = AttackLog(
            cipher="caesar", started=started, finished=started + 0.01,
            status="solved", tried=25, best_confidence=0.99, detail="key=7",
        )
        payload = log.as_dict()
        self.assertEqual(payload["status"], "solved")
        self.assertEqual(payload["tried"], 25)
        self.assertEqual(payload["detail"], "key=7")
        self.assertAlmostEqual(log.elapsed, 0.01, places=3)

    def test_a_running_attack_reports_its_elapsed_time_so_far(self):
        log = AttackLog(cipher="substitution", started=time.time() - 0.5)
        self.assertEqual(log.status, "running")
        self.assertGreater(log.elapsed, 0.4)

    def test_report_exposes_the_winning_candidate(self):
        best = candidate(confidence=0.93, steps=("base64",))
        report = CrackReport(ciphertext="abc", solved=True, best=best, candidates=[best])
        self.assertEqual(report.plaintext, best.plaintext)
        self.assertEqual(report.cipher, "caesar")
        self.assertEqual(report.key_repr, "7")
        self.assertEqual(report.path, "base64 -> caesar")
        self.assertEqual(report.steps, ("base64",))
        self.assertTrue(report.solved)

    def test_an_empty_report_is_still_usable(self):
        report = CrackReport(ciphertext="")
        self.assertEqual(report.plaintext, "")
        self.assertEqual(report.confidence, 0.0)
        self.assertEqual(report.cipher, "")
        self.assertIsNone(report.key)
        self.assertEqual(report.path, "none")
        self.assertEqual(report.notes, {})
        self.assertFalse(report.solved)

    def test_report_serialises_for_the_web_api(self):
        best = candidate(confidence=0.93)
        report = CrackReport(
            ciphertext="Wkh txlfn",
            solved=True,
            best=best,
            candidates=[best],
            hypotheses=[Hypothesis("caesar", 0.95, "one shift restores English")],
            attacks=[AttackLog(cipher="caesar", started=time.time(), finished=time.time(),
                               status="solved", tried=25, best_confidence=0.93)],
            elapsed=0.02,
            budget=10.0,
            workers=2,
            stats={"length": 9},
        )
        payload = json.dumps(report.as_dict())
        self.assertIn("caesar", payload)
        self.assertIn("hypotheses", payload)

    def test_plaintext_can_be_truncated_for_transport(self):
        best = candidate(plaintext="A" * 500)
        report = CrackReport(ciphertext="x", best=best, candidates=[best])
        payload = report.as_dict(plaintext_limit=40)
        self.assertEqual(len(payload["best"]["plaintext"]), 40)


if __name__ == "__main__":
    unittest.main()
