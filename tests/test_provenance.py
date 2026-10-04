import tempfile
import unittest
from pathlib import Path

from buttcrack.provenance import AssistantRecord


class ProvenanceTests(unittest.TestCase):
    def test_record_hash_and_jsonl(self):
        record = AssistantRecord.create("planner", "built-in", "why?", "try period scan", "ABC")
        self.assertEqual(len(record.ciphertext_sha256), 64)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "assistant.jsonl"
            record.save_jsonl(p)
            self.assertIn("planner", p.read_text())


if __name__ == "__main__":
    unittest.main()
