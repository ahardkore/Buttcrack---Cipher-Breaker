"""Geometry stays literal; descriptive counts do not promote an outlier."""

import unittest
from pathlib import Path

from buttcrack.strip_analysis import analyze


class StripAnalysisTests(unittest.TestCase):
    def test_spaces_blank_lines_and_edges(self):
        result = analyze(" AB C\r\n\r\nXY  Z ", 3)
        self.assertEqual(result["rows"], [
            {"line": 1, "letters": 3, "before": 1, "on": 1, "after": 1},
            {"line": 3, "letters": 3, "before": 2, "on": 0, "after": 1},
        ])
        self.assertEqual(analyze("ABC", 20)["rows"][0]["before"], 3)

    def test_rejects_ambiguous_input(self):
        for text, column in [("A\tB", 2), ("Aé", 1), ("A\rB", 1), (" ", 1), ("A", True), ("A", 0), ("A", 1.5), ("A" * 100001, 1), ("A\n" * 2000, 1)]:
            with self.subTest(text=text[:10], column=column), self.assertRaises(ValueError):
                analyze(text, column)

    def test_reproduces_nachtlorn_guide_counts(self):
        raw = Path("docs/data/nachtlorn-transcript.txt").read_text(encoding="ascii")
        body = "\n".join(raw.splitlines()[8:])
        result = analyze(body, 49)
        self.assertEqual(len(result["rows"]), 146)
        self.assertEqual(result["rows"][0], {"line": 1, "letters": 60, "before": 35, "on": 0, "after": 25})
        self.assertEqual(result["rows"][-1], {"line": 146, "letters": 36, "before": 35, "on": 1, "after": 0})


if __name__ == "__main__":
    unittest.main()
