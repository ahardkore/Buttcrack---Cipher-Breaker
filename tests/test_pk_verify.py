"""The acceptance harness guards the lesson of the retraction: a candidate
solution must pass tests a wrong answer *cannot* pass.  These tests pin the
three behaviours that make it a guard and not a rubber stamp."""

from __future__ import annotations

import unittest

from scripts.pk_verify import RETRACTED_PK9, verdicts


class TestPkVerify(unittest.TestCase):
    PLAIN = (
        "THERAILWAYSTATIONATASHFORDWASCROWDEDWITHTRAVELLERSWAITINGFORTHEDELAY"
        "EXPRESSANDTHESTATIONMASTERWALKEDUPANDDOWNTHEPLATFORMWITHHISHANDSBEHINDHISBACKMUT"
    )

    TRUE_WHEELS = [[3, 1, 4, 1], [5, 9, 2, 6, 5], [3, 5, 8, 9, 7, 9], [3, 2, 3, 8, 4, 6, 2]]

    def _claim(self, claim_wheels):
        from buttcrack.ciphers.keyed import SumClock

        periods = [4, 5, 6, 7]
        ct = SumClock().encrypt(
            self.PLAIN, {"alphabet": "kryptos", "periods": periods, "wheels": self.TRUE_WHEELS}
        )
        return {
            "puzzle": "SYN",
            "plaintext": self.PLAIN,
            "family": "sum_clock",
            "periods": periods,
            "wheels": claim_wheels,
            "ciphertext": ct,
        }

    def test_true_key_passes(self):
        v = verdicts(self._claim(self.TRUE_WHEELS))
        self.assertTrue(v["solved"], v)

    def test_wrong_key_fails_reproduction(self):
        wrong = [list(w) for w in self.TRUE_WHEELS]
        wrong[3][2] = (wrong[3][2] + 1) % 26
        v = verdicts(self._claim(wrong))
        self.assertFalse(v["checks"]["reproduction"])
        self.assertFalse(v["solved"])

    def test_retracted_pk9_reading_fails(self):
        # The exact text the manuscript retracted must never pass again.
        claim = {
            "puzzle": "PK9",
            "plaintext": RETRACTED_PK9,
            "family": "sum_clock",
            "periods": [2],
            "wheels": [[0, 0]],
            "ciphertext": "X" * len(RETRACTED_PK9),
        }
        v = verdicts(claim)
        self.assertFalse(v["solved"])
        self.assertFalse(v["checks"]["english_band"], v)

    def test_gibberish_fails(self):
        claim = {
            "puzzle": "SYN",
            "plaintext": "QZXVJKWBQZXVJKWBQZXVJKWBQZXVJKWBQZXVJKWBQZXVJKWBQZXVJKWB",
            "family": "sum_clock",
            "periods": [2],
            "wheels": [[0, 0]],
            "ciphertext": "QZXVJKWBQZXVJKWBQZXVJKWBQZXVJKWBQZXVJKWBQZXVJKWBQZXVJKWB",
        }
        v = verdicts(claim)
        self.assertFalse(v["checks"]["english_band"], v)
        self.assertFalse(v["solved"])


if __name__ == "__main__":
    unittest.main()
