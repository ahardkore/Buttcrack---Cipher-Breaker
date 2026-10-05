import unittest

from buttcrack.crib import consistent_period, implied_shifts, multi_crib_consistent_period


class CribTests(unittest.TestCase):
    def test_implied_shift(self):
        self.assertEqual(implied_shifts("BCD", "ABC", 0), [1, 1, 1])

    def test_implied_shift_custom_alphabet_and_mode(self):
        kryptos = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
        # In KRYPTOS: K=0, R=1, Y=2, P=3, T=4, O=5, S=6, A=7, B=8, C=9, D=10, E=11, F=12, L=17
        # CT='F' (12), PT='E' (11) -> shift = (12 - 11) % 26 = 1
        self.assertEqual(implied_shifts("F", "E", 0, alphabet=kryptos, mode="vigenere"), [1])
        # Beaufort: (12 + 11) % 26 = 23
        self.assertEqual(implied_shifts("F", "E", 0, alphabet=kryptos, mode="beaufort"), [23])

    def test_period_consistency(self):
        self.assertTrue(consistent_period([1, 2, 1, 2], 2))
        self.assertFalse(consistent_period([1, 2, 3, 2], 2))

    def test_multi_crib_consistent_period(self):
        # Anchor at pos 0: "AB", at pos 4: "AB" with period 4
        anchors = {0: "AB", 4: "AB"}
        ct = "BCXXBC"
        self.assertTrue(multi_crib_consistent_period(anchors, ct, 4))
        # Contradiction: anchor at pos 0 and pos 2 with period 2 requiring different shifts
        anchors_bad = {0: "A", 2: "B"}
        ct_same = "BXB"
        self.assertFalse(multi_crib_consistent_period(anchors_bad, ct_same, 2))


if __name__ == "__main__":
    unittest.main()

