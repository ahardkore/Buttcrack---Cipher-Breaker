import tempfile
import unittest
from pathlib import Path

from buttcrack.project import Project


class ProjectTests(unittest.TestCase):
    def test_structured_state_round_trip(self):
        import tempfile

        project = Project(
            source="desktop",
            verification={"algorithm": "Vigenere", "result": "mismatch"},
            crib_placements=[{"crib": "TEST", "offset": 2}],
            transposition={"fill": "row-fill", "history": ["grid"]},
            scoring_records=[{"provider": "QuadgramScore", "value": 1.2}],
            campaign={"total_chunks": 10},
            assistant_outputs=[{"text": "hypothesis"}],
        )
        project.add_candidate("PLAINTEXT", {"score": -1})
        project.record_candidate_verification(0, "failed", {"reason": "round trip"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.json"
            project.save(path)
            loaded = Project.load(path)
        self.assertEqual(loaded.verification["result"], "mismatch")
        self.assertEqual(loaded.crib_placements[0]["offset"], 2)
        self.assertEqual(loaded.transposition["history"], ["grid"])
        self.assertEqual(loaded.scoring_records[0]["provider"], "QuadgramScore")
        self.assertEqual(loaded.campaign["total_chunks"], 10)
        self.assertEqual(loaded.candidates[0]["verification_history"][0]["state"], "failed")

    def test_save_load_preserves_ciphertext_and_audit_data(self):
        project = Project(ciphertext="KRYPTOS", source="test")
        project.add_attack("caesar", {"shift": 3}, "negative")
        project.add_candidate("NUBS GBV", {"status": "heuristic"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.kryptos-project.json"
            project.save(path)
            loaded = Project.load(path)
        self.assertEqual(loaded.ciphertext, "KRYPTOS")
        self.assertEqual(loaded.attacks[0]["status"], "negative")
        self.assertEqual(loaded.candidates[0]["evidence"]["status"], "heuristic")

    def test_hash_is_deterministic(self):
        self.assertEqual(Project(ciphertext="ABC").ciphertext_sha256, Project(ciphertext="ABC").ciphertext_sha256)


if __name__ == "__main__":
    unittest.main()
