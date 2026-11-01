"""Synthetic controls for the registered colour hypothesis, not puzzle evidence."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.nachtlorn_colour_probe import AES, buffers, main, proposal, reference_contexts, scan
from scripts.nachtlorn_running_book_probe import transform

POEM = ("blue at the bottom of the bowl.\nlaughter, somewhere on the stairs.\n"
        "one given.\none taken.\nmorning. neither be right.\n\nFind the outlier.\n\n")
BOOK = b"A bowl of white china stood there holding the green sluggish bile."


def encode26(data):
    number, letters = int.from_bytes(data, "big"), []
    while number:
        number, digit = divmod(number, 26)
        letters.append(chr(65 + digit))
    return "".join(reversed(letters)) or "A"


class ColourProbeTests(unittest.TestCase):
    def test_proposal_preserves_input_and_marks_interpretation(self):
        raw = (POEM + "ABCDE I\n").encode()
        original = bytes(raw)
        result = proposal(raw, BOOK)
        self.assertEqual(raw, original)
        self.assertEqual(result["original_poem"][0], "blue at the bottom of the bowl.")
        self.assertEqual(result["proposed_poem"][0], "green at the bottom of the bowl.")
        self.assertEqual(result["derived_acrostic"], "GLOOM")
        with self.assertRaises(ValueError):
            proposal(raw, b"A bowl of blue china.")

    def test_white_is_admitted_without_being_an_english_word(self):
        raw = (POEM + "ABCDE I\n").encode()
        result = proposal(raw, BOOK, "white")
        self.assertEqual(result["derived_acrostic"], "WLOOM")
        self.assertEqual(result["proposed_poem"][0], "white at the bottom of the bowl.")
        report = scan("ABCDE", "WLOOM")
        self.assertEqual(report["key"], "WLOOM")
        self.assertEqual(report["standalone_password_test"]["password_cases"], ["WLOOM", "wloom", "Wloom"])
        with self.assertRaises(ValueError):
            proposal(raw, BOOK, "yellow")

    def test_context_audit_has_explicit_domains_and_does_not_infer_modification(self):
        book = ("Stately, plump Buck Mulligan saw a bowl. A yellow gown hung there.\n"
                "[ 2 ]\nThere were bowls and a blue hat.\n"
                "*** END OF THIS PROJECT GUTENBERG EBOOK ULYSSES ***\nBlue bowls.").encode()
        result = reference_contexts(book)
        self.assertEqual(result["bowl_token_hits"], 2)
        self.assertEqual([r["episode"] for r in result["records"]], [1, 2])
        self.assertIn("Proximity does not establish", result["caution"])
        self.assertTrue(any(c["token"] == "yellow" for c in result["records"][0]["nearby_colour_tokens"]))

    def test_representation_count_and_zero_restoration(self):
        data = b"\0" * 6 + b'{"test":true}'
        candidates = list(buffers(encode26(data)))
        self.assertEqual(len(candidates), 32)
        self.assertIn(({"bias": 0, "byteorder": "big", "restored_zero_bytes": 6}, data), candidates)

    def test_repeating_key_recovers_complete_json_with_marker(self):
        plain = encode26(b'{"synthetic_control":"not puzzle evidence"}')
        key = ("GLOOM" * ((len(plain) + 4) // 5))[:len(plain)]
        stream = transform(plain, key, "minus", inverse=True) + "I"
        report = scan(stream)
        literal = report["literal_key_test"]
        self.assertEqual(literal["letter_paths"], 6)
        self.assertEqual(literal["representation_configurations"], 192)
        self.assertTrue(all(r["exact_letter_roundtrip"] for r in literal["roundtrips"]))
        self.assertTrue(any(r["drop_final_i"] and r["operation"] == "minus"
                            and any(o["format"] == "json" for o in r["objects"])
                            for r in literal["accepted_records"]))

    @unittest.skipIf(AES is None, "optional research crypto dependency not installed")
    def test_password_recovers_authenticated_synthetic_packet(self):
        plaintext = b'{"synthetic_control":"not puzzle evidence"}'
        for password in ("GLOOM", "WLOOM"):
            cipher = AES.new(hashlib.sha256(password.encode()).digest(), AES.MODE_GCM,
                             nonce=bytes(range(1, 13)))
            ciphertext, tag = cipher.encrypt_and_digest(plaintext)
            packet = bytes(range(1, 13)) + ciphertext + tag
            report = scan(encode26(packet) + "I", password)
            accepted = report["standalone_password_test"]["accepted"]
            self.assertTrue(any(row["drop_final_i"] and row["password"] == password
                                and row["derivation"] == "sha256"
                                and bytes.fromhex(row["plaintext_hex"]) == plaintext for row in accepted))
            damaged = packet[:-1] + bytes([packet[-1] ^ 1])
            self.assertEqual(scan(encode26(damaged), password)["standalone_password_test"]["accepted"], [])

    def test_rejects_unregistered_key_and_invalid_source(self):
        for stream, key in (("ABCDE", "BLOOM"), ("abcde", "GLOOM"), ("I", "GLOOM")):
            with self.assertRaises(ValueError):
                scan(stream, key)

    def test_output_cannot_overwrite_either_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source, book = Path(directory) / "source.txt", Path(directory) / "book.txt"
            source.write_text(POEM + "ABCDE I\n")
            book.write_bytes(BOOK)
            before = source.read_bytes(), book.read_bytes()
            for output in (source, book):
                with self.assertRaises(SystemExit):
                    main([str(source), "--book", str(book), "--output", str(output)])
            self.assertEqual((source.read_bytes(), book.read_bytes()), before)


if __name__ == "__main__":
    unittest.main()
