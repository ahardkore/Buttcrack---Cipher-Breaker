"""Regression tests for verified Paradigm Kryptos PK1–PK10 support.

The important boundary is tested as much as the happy path: only exact
normalized ciphertext equality may receive the verified-corpus verdict.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

from buttcrack.assistant import analysis, explain, recommend
from buttcrack.engine import solve
from buttcrack.lang import get_model
from buttcrack.paradigm import RECORDS, catalog, exact_candidate, match, normalize

ROOT = Path(__file__).resolve().parents[1]


class ParadigmKryptosTests(unittest.TestCase):
    def test_catalog_has_every_pk_record_in_order(self) -> None:
        self.assertEqual([record.challenge_id for record in RECORDS], [f"PK{i}" for i in range(1, 11)])
        self.assertEqual(len(catalog()), 10)
        for record in RECORDS:
            with self.subTest(record=record.challenge_id):
                self.assertEqual(match(record.ciphertext), record)
                self.assertEqual(hashlib.sha256(record.plaintext.encode("ascii")).hexdigest(), record.plaintext_sha256)

    def test_match_uses_documented_normalization_and_never_a_near_match(self) -> None:
        record = RECORDS[0]
        wrapped = "\n".join(record.ciphertext[i : i + 32].lower() for i in range(0, len(record.ciphertext), 32))
        self.assertEqual(normalize(wrapped), record.ciphertext)
        self.assertEqual(match(wrapped), record)
        altered = "Z" + record.ciphertext[1:]
        self.assertNotEqual(altered, record.ciphertext)
        self.assertIsNone(match(altered))

    def test_exact_candidate_carries_verification_not_score_as_proof(self) -> None:
        record = RECORDS[-1]
        candidate = exact_candidate(record.ciphertext, get_model())
        self.assertIsNotNone(candidate)
        assert candidate is not None  # help type checkers while preserving unittest assertions
        self.assertEqual(candidate.plaintext, record.plaintext)
        self.assertEqual(candidate.confidence, 1.0)
        self.assertEqual(candidate.notes["verification_status"], "verified exact match")
        self.assertEqual(candidate.notes["corpus_match"], "PK10")
        self.assertIn("not a claim", candidate.notes["caveat"])

    def test_engine_returns_all_canonical_records_without_spending_search_budget(self) -> None:
        for record in RECORDS:
            with self.subTest(record=record.challenge_id):
                report = solve(record.ciphertext, budget=0.5)
                self.assertTrue(report.solved)
                self.assertEqual(report.plaintext, record.plaintext)
                self.assertEqual(report.cipher, record.cipher_name)
                self.assertEqual(report.notes["corpus_match"], record.challenge_id)
                self.assertEqual(report.notes["verification_status"], "verified exact match")
                self.assertEqual(report.attacks[0].status, "solved")

    def test_assistant_only_calls_an_exact_record_verified(self) -> None:
        record = RECORDS[0]
        verified = analysis(record.ciphertext)
        self.assertEqual(verified["status"], "verified_exact_match")
        self.assertEqual(verified["exact_match"]["id"], record.challenge_id)
        self.assertEqual(recommend(record.ciphertext)[0].confidence, "verified")
        self.assertIn("VERIFIED EXACT MATCH", explain(record.ciphertext))

        unverified = analysis("Z" + record.ciphertext[1:])
        self.assertEqual(unverified["status"], "recommendations_only")
        self.assertIsNone(unverified["exact_match"])
        self.assertTrue(all(item["confidence"] != "verified" for item in unverified["recommendations"]))

    def test_generated_catalog_assets_match_the_manifest(self) -> None:
        """The public browser and packaged desktop consume the same generated data."""
        path = ROOT / "scripts" / "build_paradigm_catalog.py"
        spec = importlib.util.spec_from_file_location("build_paradigm_catalog", path)
        self.assertIsNotNone(spec)
        assert spec and spec.loader
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        manifest = json.loads((ROOT / "kryptos" / "pk_submission_manifest.json").read_text(encoding="utf-8"))
        records = generator.normalized_records(manifest)
        package_records = json.loads((ROOT / "buttcrack" / "data" / "paradigm_kryptos.json").read_text(encoding="utf-8"))
        self.assertEqual(package_records, records)
        expected_js = generator.javascript(records)
        for target in (
            ROOT / "buttcrack" / "static" / "paradigm.js",
            ROOT / "ventures" / "cipher-solver-web" / "paradigm.js",
        ):
            self.assertEqual(target.read_text(encoding="utf-8"), expected_js)


if __name__ == "__main__":
    unittest.main()
