import unittest

from buttcrack.verification import round_trip


class VerificationTests(unittest.TestCase):
    def test_exact_round_trip(self):
        result = round_trip("ABC", "BCD", lambda text: "BCD")
        self.assertTrue(result.exact)
        self.assertIsNone(result.mismatch_index)

    def test_reports_first_mismatch(self):
        result = round_trip("ABC", "BXD", lambda text: "BCD")
        self.assertFalse(result.exact)
        self.assertEqual(result.mismatch_index, 1)
        self.assertIn("position 1", result.message)

    def test_reports_length_mismatch(self):
        result = round_trip("ABC", "BC", lambda text: "BCD")
        self.assertFalse(result.exact)
        self.assertIn("length mismatch", result.message)


if __name__ == "__main__":
    unittest.main()
