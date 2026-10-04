import unittest
from buttcrack.crib import implied_shifts, consistent_period
class CribTests(unittest.TestCase):
    def test_implied_shift(self):
        self.assertEqual(implied_shifts("BCD", "ABC", 0), [1, 1, 1])
    def test_period_consistency(self):
        self.assertTrue(consistent_period([1, 2, 1, 2], 2))
        self.assertFalse(consistent_period([1, 2, 3, 2], 2))
if __name__ == "__main__": unittest.main()
