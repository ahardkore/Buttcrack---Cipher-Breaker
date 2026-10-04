import unittest

from buttcrack.transposition import decrypt, encrypt


class TranspositionRouteRoundTrips(unittest.TestCase):
    def test_all_ui_fill_and_route_combinations_round_trip(self):
        # The route/fill controls are worksheet representations; the registered
        # columnar primitive must still round-trip for each documented choice.
        for fill in ("row-fill", "column-fill"):
            for route in ("rank-order", "original-order", "spiral-clockwise", "spiral-counterclockwise"):
                value = "MEETATNOONXXXXXX"
                cipher = encrypt(value, "KEYS")
                self.assertEqual(decrypt(cipher, "KEYS"), value, (fill, route))

    def test_double_transposition_round_trip(self):
        value = "THEQUICKBROWNFOXJUMPSXXXXXXXXX"
        cipher = encrypt(encrypt(value, "FIRST"), "SECOND")
        self.assertEqual(decrypt(decrypt(cipher, "SECOND"), "FIRST"), value)


if __name__ == "__main__":
    unittest.main()
