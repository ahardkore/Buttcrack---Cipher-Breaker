"""Clue-role separation with synthetic packet and authenticated controls."""
import contextlib
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts.binary_envelope_probe import A26, keyed_alphabet
from scripts.nachtlorn_aead_probe import AES
from scripts.nachtlorn_colour_byte_probe import LITERAL_WORDS, key_material, scan as byte_scan
from scripts.nachtlorn_colour_probe import scan as colour_scan
from scripts.nachtlorn_replacement_role_probe import literal_roles, main, reference_basis, scan_keyword
from scripts.nachtlorn_running_book_probe import transform
from tests.test_nachtlorn_colour_probe import POEM, encode26

BOOK = (b"Stately, plump Buck Mulligan. A bowl of white china holding the green sluggish bile.\n"
        b"[ 5 ]\nThe cold black marble bowl. I am in mourning myself.\n"
        b"*** END OF THIS PROJECT GUTENBERG EBOOK ULYSSES ***\n")


def armoured(data, keyword):
    return encode26(data).translate(str.maketrans(A26, keyed_alphabet(keyword)))


class ReplacementRoleTests(unittest.TestCase):
    def test_reference_roles_and_literal_word_profile(self):
        raw = (POEM + "ABCDEFGHI\n").encode()
        basis = reference_basis(raw, BOOK)
        self.assertIn("green sluggish bile", basis["green_white_passage"])
        self.assertEqual(basis["black_mourning_context"]["episode"], 5)
        result = literal_roles("ABCDEFGHI")
        self.assertEqual([r["key"] for r in result["literal_word_reports"]], ["BLACK", "GREEN", "WHITE"])
        self.assertEqual(len(result["direct_byte_xor"]["key_specification"]), 18)
        self.assertEqual(result["direct_byte_xor"]["hypothesis"], "R11")
        with self.assertRaises(ValueError):
            reference_basis(raw, BOOK.replace(b"black marble", b"purple marble"))

    def test_literal_black_letter_key_recovers_synthetic_packet(self):
        plain = encode26(b'{"synthetic_control":"not puzzle evidence"}')
        expanded = ("BLACK" * ((len(plain) + 4) // 5))[:len(plain)]
        stream = transform(plain, expanded, "minus", inverse=True) + "I"
        result = colour_scan(stream, "BLACK")
        self.assertTrue(any(r["operation"] == "minus" and r["drop_final_i"]
                            and any(o["format"] == "json" for o in r["objects"])
                            for r in result["literal_key_test"]["accepted_records"]))

    def test_plain_keyed_alphabet_packet_and_all_roundtrips(self):
        packet = gzip.compress(b'{"synthetic_control":"not puzzle evidence"}', mtime=0)
        stream = armoured(packet, "GREEN") + "I"
        result = scan_keyword(stream, keywords=("GREEN",), password_words=("BLACK",))
        self.assertEqual(result["representation_configurations"], 64)
        self.assertEqual(len(result["roundtrips"]), 4)
        self.assertTrue(all(r["exact_numeric_and_source_roundtrip"] for r in result["roundtrips"]))
        self.assertTrue(any(r["drop_final_i"] and any(o["format"] == "gzip" for o in r["objects"])
                            for r in result["decoded_objects"]))

    @unittest.skipIf(AES is None, "optional research crypto dependency not installed")
    def test_primary_bloom_alphabet_black_password_and_damaged_tag(self):
        plaintext = gzip.compress(b'{"synthetic_control":"not puzzle evidence"}', mtime=0)
        nonce = bytes(range(1, 13))
        cipher = AES.new(hashlib.sha256(b"BLACK").digest(), AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        packet = nonce + ciphertext + tag
        result = scan_keyword(armoured(packet, "BLOOM") + "I",
                              keywords=("BLOOM",), password_words=("BLACK",))
        self.assertTrue(any(r["drop_final_i"] and r["password"] == "BLACK" and r["derivation"] == "sha256"
                            and bytes.fromhex(r["plaintext_hex"]) == plaintext for r in result["authenticated_packets"]))
        corrupted = packet[:-1] + bytes([packet[-1] ^ 1])
        bad = scan_keyword(armoured(corrupted, "BLOOM") + "I",
                           keywords=("BLOOM",), password_words=("BLACK",))
        self.assertEqual(bad["authenticated_packets"], [])

    def test_profiles_are_explicit_and_old_byte_profile_is_preserved(self):
        self.assertEqual(len(list(key_material())), 24)
        self.assertEqual(len(list(key_material(LITERAL_WORDS))), 18)
        with self.assertRaises(ValueError):
            list(key_material(("PURPLE",)))
        with self.assertRaises(ValueError):
            scan_keyword("ABCDEFGHI", keywords=("BLOOM", "BLOOM"))
        with self.assertRaises(ValueError):
            scan_keyword("ABCDEFGHI", password_words=("PURPLE",))
        with self.assertRaises(ValueError):
            scan_keyword("lowercase")
        self.assertEqual(byte_scan("ABCDEFGHI")["hypothesis"], "R10")

    def test_both_cli_modes_and_both_input_overwrite_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            source, book, output = (Path(directory) / name for name in ("source.txt", "book.txt", "result.json"))
            raw = (POEM + "ABCDEFGHI\n").encode()
            source.write_bytes(raw)
            book.write_bytes(BOOK)
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                for mode, expected in (("literal", "R11"), ("alphabet", "R12")):
                    args = [str(source), "--book", str(book), "--mode", mode, "--output", str(output)]
                    self.assertEqual(main(args), 0)
                    self.assertEqual(json.loads(output.read_text())["hypothesis"], expected)
                    for protected in (source, book):
                        with self.assertRaises(SystemExit):
                            main(args[:-1] + [str(protected)])
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(book.read_bytes(), BOOK)


if __name__ == "__main__":
    unittest.main()
