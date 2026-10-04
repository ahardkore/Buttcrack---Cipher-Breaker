import unittest

from buttcrack.assistant import explain, recommend


class AssistantTests(unittest.TestCase):
    def test_short_text_is_flagged_as_underdetermined(self):
        self.assertIn("manual crib", recommend("ABCD")[0].name)

    def test_explain_is_explicitly_not_a_solution(self):
        self.assertIn("recommendations only", explain("THEQUICKBROWNFOX"))

    def test_recommendations_are_nonempty(self):
        self.assertTrue(recommend("KRYPTOSABCDEFGHIJLMNQUVWXZ"))


if __name__ == "__main__":
    unittest.main()
