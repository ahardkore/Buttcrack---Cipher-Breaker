import unittest

from buttcrack.attack import AttackResult, merge_result


class AttackTests(unittest.TestCase):
    def test_merge_retains_best_and_deduplicates(self):
        old = AttackResult("demo", progress=.2, best_score=-7, candidates=[{"key": "A", "score": -7}])
        new = AttackResult("demo", status="negative", progress=.4, best_score=-5, candidates=[{"key": "A", "score": -7}, {"key": "B", "score": -5}])
        merged = merge_result(old, new)
        self.assertEqual(merged.status, "negative")
        self.assertEqual(merged.progress, .4)
        self.assertEqual(len(merged.candidates), 2)
        self.assertEqual(merged.best_score, -5)


if __name__ == "__main__":
    unittest.main()
