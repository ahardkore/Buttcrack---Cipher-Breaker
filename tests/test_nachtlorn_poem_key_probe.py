"""R9 mechanical derivation and synthetic recovery; not a plaintext word search."""
import contextlib
import hashlib
import io
from pathlib import Path
import tempfile
import unittest

from scripts.nachtlorn_colour_probe import AES, scan
from scripts.nachtlorn_poem_key_probe import derive, main, scan_all
from scripts.nachtlorn_running_book_probe import transform
from tests.test_nachtlorn_colour_probe import BOOK, POEM, encode26


class PoemKeyTests(unittest.TestCase):
    def test_derivations_preserve_poem_and_do_not_reverse_operations(self):
        poem = POEM.splitlines()[:5]
        original = poem[:]
        for colour, before, after in (("green", "GLOOM", "GLPNM"),
                                     ("white", "WLOOM", "WLPNM"), (None, "BLOOM", "BLPNM")):
            result = derive(poem, colour)
            self.assertEqual(result["before_unit_shifts"], before)
            self.assertEqual(result["derived_key"], after)
            self.assertEqual([op["delta"] for op in result["operations"]], [1, -1])
        self.assertEqual(poem, original)
        with self.assertRaises(ValueError):
            derive(poem, "yellow")
        poem[2] = "one taken."
        with self.assertRaises(ValueError):
            derive(poem, "green")

    def test_all_three_declared_keys_have_synthetic_structured_recovery(self):
        plain = encode26(b'{"synthetic_control":"not puzzle evidence"}')
        for key in ("GLPNM", "WLPNM", "BLPNM"):
            expanded = (key * ((len(plain) + 4) // 5))[:len(plain)]
            source = transform(plain, expanded, "minus", inverse=True) + "I"
            result = scan(source, key)
            self.assertTrue(any(r["operation"] == "minus" and r["drop_final_i"]
                                and any(o["format"] == "json" for o in r["objects"])
                                for r in result["literal_key_test"]["accepted_records"]))

    @unittest.skipIf(AES is None, "optional research crypto dependency not installed")
    def test_new_derived_password_authentication_and_tamper_rejection(self):
        key = "GLPNM"
        plaintext = b'{"synthetic_control":"not puzzle evidence"}'
        nonce = bytes(range(1, 13))
        cipher = AES.new(hashlib.sha256(key.encode()).digest(), AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        packet = nonce + ciphertext + tag
        valid = scan(encode26(packet), key)["standalone_password_test"]["accepted"]
        self.assertTrue(any(r["password"] == key and bytes.fromhex(r["plaintext_hex"]) == plaintext
                            for r in valid))
        bad = packet[:-1] + bytes([packet[-1] ^ 1])
        self.assertEqual(scan(encode26(bad), key)["standalone_password_test"]["accepted"], [])

    def test_combined_report_and_input_overwrite_guards(self):
        raw = (POEM + "ABCDEFGHI\n").encode()
        result = scan_all(raw, BOOK)
        self.assertEqual([r["key"] for r in result["candidate_reports"]], ["GLPNM", "WLPNM", "BLPNM"])
        self.assertEqual(result["source_sha256"], hashlib.sha256(raw).hexdigest())
        with tempfile.TemporaryDirectory() as directory:
            source, book = Path(directory) / "source.txt", Path(directory) / "book.txt"
            source.write_bytes(raw)
            book.write_bytes(BOOK)
            with contextlib.redirect_stderr(io.StringIO()):
                for output in (source, book):
                    with self.assertRaises(SystemExit):
                        main([str(source), "--book", str(book), "--output", str(output)])
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(book.read_bytes(), BOOK)


if __name__ == "__main__":
    unittest.main()
