import unittest

from buttcrack.evidence import Evidence, EvidenceStatus


class EvidenceTests(unittest.TestCase):
    def test_score_only_candidate_is_not_solution(self):
        result = Evidence(EvidenceStatus.HEURISTIC, score=-4.2)
        self.assertFalse(result.can_claim_solution())

    def test_round_trip_without_independent_recheck_is_reproduced_only(self):
        result = Evidence(EvidenceStatus.HEURISTIC).promote(
            exact_round_trip=True, independent_recheck=False
        )
        self.assertIs(result.status, EvidenceStatus.REPRODUCED)
        self.assertFalse(result.can_claim_solution())

    def test_verified_requires_both_checks(self):
        result = Evidence(EvidenceStatus.HEURISTIC).promote(
            exact_round_trip=True, independent_recheck=True
        )
        self.assertIs(result.status, EvidenceStatus.VERIFIED)
        self.assertTrue(result.can_claim_solution())


if __name__ == "__main__":
    unittest.main()
