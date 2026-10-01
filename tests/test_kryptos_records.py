"""The stored Paradigm Kryptos records must not outrun their evidence.

`kryptos/` is a research dump, and research dumps drift: a plaintext gets
pasted next to the wrong ciphertext, a failed candidate keeps the word
"SOLVED" in its status, a generator script rewrites a corrected record from a
stale literal.  These tests are the ratchet that stops that happening again.

The rule is the one from `kryptos/AUDIT.md`: a record may call itself SOLVED
only if the key it names re-encrypts its plaintext into the published
ciphertext, character for character.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "kryptos"

sys.path.insert(0, str(CORPUS))
from verify_pk_records import REBUILD  # noqa: E402

from buttcrack.lang import get_model  # noqa: E402

MODEL = get_model()


class TestRecordVerification(unittest.TestCase):
    def setUp(self) -> None:
        self.ciphertexts = json.loads((CORPUS / "pk_all_ciphertexts.json").read_text())
        self.solutions = json.loads((CORPUS / "pk_verified_solutions.json").read_text())
        self.manifest = json.loads((CORPUS / "pk_submission_manifest.json").read_text())

    def test_solved_records_reproduce_their_ciphertext(self):
        for name, rebuild in REBUILD.items():
            with self.subTest(challenge=name):
                record = self.solutions[name]
                self.assertEqual(
                    rebuild(record["plaintext"]),
                    self.ciphertexts[name],
                    f"{name}: the stated key does not re-encrypt to the published ciphertext",
                )

    def test_nothing_claims_solved_without_a_reconstruction(self):
        """Every SOLVED label must be backed by an entry in REBUILD."""
        for store in (self.solutions, self.manifest):
            for name, record in store.items():
                status = str(record.get("status", "")).upper()
                if status.startswith("SOLVED"):
                    with self.subTest(challenge=name, status=status):
                        self.assertIn(
                            name, REBUILD,
                            f"{name} is labelled {status!r} but nothing verifies it",
                        )

    def test_stored_plaintexts_are_english(self):
        """A verified record's plaintext has to read as English, not merely fit."""
        for name in REBUILD:
            with self.subTest(challenge=name):
                score = MODEL.score(self.solutions[name]["plaintext"])
                self.assertGreater(score.fitness, -5.0, f"{name} does not read as English")

    def test_failed_candidates_are_not_labelled_solved(self):
        """PK8's four-wheel candidate is not English; the record must say so."""
        record = self.manifest["PK8"]
        self.assertFalse(str(record["status"]).upper().startswith("SOLVED"))
        candidate = record.get("candidate_plaintext", "")
        self.assertTrue(candidate, "the failed candidate should be retained, just labelled")
        self.assertLess(
            MODEL.score(candidate).fitness, -5.0,
            "if this candidate now reads as English, re-audit the record",
        )

    def test_unsolved_records_claim_nothing(self):
        for name in ("PK9", "PK10"):
            with self.subTest(challenge=name):
                record = self.manifest[name]
                self.assertEqual(str(record["status"]).upper(), "UNSOLVED")
                self.assertFalse(record.get("plaintext"))

    def test_every_record_carries_its_audit_verdict(self):
        audit = json.loads((CORPUS / "pk_audit.json").read_text())
        for name, fields in audit.items():
            with self.subTest(challenge=name):
                stored = self.manifest.get(name) or self.solutions.get(name)
                self.assertEqual(stored.get("status"), fields["status"])
                self.assertIn("verify_pk_records.py", stored.get("verification", ""))

    def test_harness_exits_clean(self):
        result = subprocess.run(
            [sys.executable, str(CORPUS / "verify_pk_records.py")],
            capture_output=True, text=True, cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK: every record labelled SOLVED", result.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
