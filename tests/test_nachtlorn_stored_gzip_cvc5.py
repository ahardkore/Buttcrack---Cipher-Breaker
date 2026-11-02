from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import nachtlorn_stored_gzip_cvc5 as cross
from scripts import nachtlorn_stored_gzip_probe as stored
from tests.test_nachtlorn_stored_gzip_probe import fixture


class CrosscheckGuardTests(unittest.TestCase):
    def test_missing_backend_is_not_an_exclusion(self):
        with mock.patch.object(cross, "cvc5", None), self.assertRaisesRegex(RuntimeError, "not an exclusion"):
            cross.CvcFacade("(check-sat)")

    def test_source_and_previous_result_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            previous = Path(directory) / "previous.json"
            source.write_text("unchanged")
            previous.write_text("{}")
            for output in (source, previous):
                with self.assertRaises(SystemExit):
                    cross.main([str(source), "--previous", str(previous), "--output", str(output)])
            self.assertEqual(source.read_text(), "unchanged")
            self.assertEqual(previous.read_text(), "{}")


@unittest.skipUnless(cross.cvc5 is not None and stored.z3 is not None, "optional cvc5/z3 research dependencies not installed")
class CrosscheckSolverTests(unittest.TestCase):
    def test_full_packet_recovery_with_independent_backend_under_both_biases(self):
        for bias in (0, 1):
            text, mapping, case, _packet, _payload = fixture(bias)
            result = stored.search_case(text, bias, case, fixed=mapping, budget_ms=3000,
                                        solver_adapter=cross.CvcFacade)
            self.assertEqual(result["status"], "verified_packet", result)
            self.assertTrue(result["candidate_audits"][0]["packet_checks"]["complete_stream_verified"])

    def test_crc_failure_and_incremental_model_blocking_exhaust_the_domain(self):
        text, mapping, case, _packet, _payload = fixture(corrupt_crc=True)
        result = stored.search_case(text, 0, case, fixed=mapping, budget_ms=3000,
                                    solver_adapter=cross.CvcFacade)
        self.assertEqual(result["status"], "exhausted_no_packet", result)
        self.assertEqual(result["candidate_numerals_checked"], 1)
        self.assertTrue(result["exact_exclusion"])

    def test_candidate_cap_remains_incomplete(self):
        text, mapping, case, _packet, _payload = fixture(corrupt_crc=True)
        result = stored.search_case(text, 0, case, fixed=mapping, budget_ms=3000, candidate_cap=1,
                                    solver_adapter=cross.CvcFacade)
        self.assertEqual(result["status"], "candidate_cap", result)
        self.assertFalse(result["exact_exclusion"])

    def test_nlen_corruption_is_unsatisfiable_in_both_backends(self):
        text, mapping, case, _packet, _payload = fixture(corrupt_complement=True)
        result = stored.search_case(text, 0, case, fixed=mapping, budget_ms=3000,
                                    solver_adapter=cross.CvcFacade)
        self.assertEqual(result["status"], "exhausted_no_packet", result)
        self.assertEqual(result["candidate_numerals_checked"], 0)

    def test_followup_selects_only_recorded_unknown_cases(self):
        text, _mapping, case, _packet, _payload = fixture()
        previous = {"models": [{"drop_final_i": False, "bias": 0, "retained_letters": len(text),
                                "cases": [{**case, "status": "unknown"}, {**case, "status": "empty_interval_cover"}]}]}
        expected = {**case, "status": "unknown", "candidate_numerals_checked": 0, "elapsed_seconds": 0.0}
        with mock.patch.object(stored, "search_case", return_value=expected) as search:
            result = cross.followup(text, previous)
        self.assertEqual(len(result["cases"]), 1)
        search.assert_called_once()
        self.assertIs(search.call_args.kwargs["solver_adapter"], cross.CvcFacade)


if __name__ == "__main__":
    unittest.main()
