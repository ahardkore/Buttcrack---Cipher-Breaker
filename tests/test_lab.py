import unittest

from buttcrack.transposition import decrypt, encrypt


class LabTests(unittest.TestCase):
    def test_transposition_round_trip(self):
        text = "MEETATNOONXXXXXX"
        self.assertEqual(decrypt(encrypt(text, "KEYS"), "KEYS"), text)

    def test_double_transposition_round_trip(self):
        from buttcrack.transposition import double_decrypt, double_encrypt

        text = "MEETATNOONXXXXXX"
        self.assertEqual(double_decrypt(double_encrypt(text, "KEYS", "WORD"), "KEYS", "WORD"), text)


if __name__ == "__main__":
    unittest.main()
