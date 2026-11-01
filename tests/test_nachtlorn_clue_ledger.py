"""The ledger must reproduce facts without promoting candidates to answers."""
from __future__ import annotations

import contextlib
import io
import json
import random
import tempfile
import unittest
from pathlib import Path

from scripts.nachtlorn_clue_ledger import audit, given_taken_key, main, vigenere

SOURCE = Path(__file__).resolve().parents[1] / "docs/data/nachtlorn-transcript.txt"
SHA256 = "04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e"


class NachtlornClueLedgerTests(unittest.TestCase):
    def test_literal_acrostic_and_proposed_line_order_key(self):
        result = audit(SOURCE.read_bytes())
        self.assertEqual(result["acrostic"], "BLOOM")
        self.assertEqual(result["proposed_given_taken_key"]["key"], "BLPNM")
        self.assertEqual(result["proposed_given_taken_key"]["changed_poem_lines"], [3, 4])
        self.assertIn("hypothesis", result["proposed_given_taken_key"]["status"])

    def test_key_adjustment_wraps_modulo26(self):
        self.assertEqual(given_taken_key("ZZZZZ"), "ZZAYZ")
        self.assertEqual(given_taken_key("AAAAA"), "AABZA")

    def test_bad_key_initials_rejected(self):
        for key in ("", "BLOO", "bloom", "BLOÖM", "BLO OM"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    given_taken_key(key)

    def test_native_vigenere_known_vector_and_roundtrip(self):
        self.assertEqual(vigenere("ATTACKATDAWN", "LEMON", encrypt=True), "LXFOPVEFRNHR")
        self.assertEqual(vigenere("LXFOPVEFRNHR", "LEMON"), "ATTACKATDAWN")

    def test_vigenere_rejects_nonliteral_streams_and_keys(self):
        for text, key in (("", "A"), ("ABC", ""), ("a", "B"), ("A B", "C"),
                          ("É", "ABC"), ("ABC", "é")):
            with self.subTest(text=text, key=key):
                with self.assertRaises(ValueError):
                    vigenere(text, key)

    def test_source_fingerprint_and_entire_indent_trace(self):
        result = audit(SOURCE.read_bytes())
        self.assertEqual(result["source_sha256"], SHA256)
        self.assertEqual(result["source_bytes"], 11129)
        self.assertEqual((result["body_rows"], result["body_letters"]), (146, 8736))
        self.assertEqual(result["indentation"]["matches"], 146)
        self.assertTrue(result["indentation"]["exact_match"])
        self.assertTrue(all(r["exact_source_letter_roundtrip"] for r in result["roundtrips"]))
        self.assertIn("Unresolved", result["status"])

    def test_literal_fragments_have_exact_source_positions_not_repairs(self):
        fragments = audit(SOURCE.read_bytes())["literal_fragments"]
        self.assertEqual(len(fragments), 2)
        frodo = next(x for x in fragments if x["decoded_literal"] == "FRODO")
        tract = next(x for x in fragments if x["decoded_literal"] == "TRACT")
        self.assertEqual((frodo["key"], frodo["ciphertext"], frodo["letter_offset"],
                          frodo["body_row"], frodo["group"], frodo["source_columns_one_based"]),
                         ("BLOOM", "GCCRA", 7625, 128, 2, [10, 14]))
        self.assertEqual((tract["key"], tract["ciphertext"], tract["letter_offset"],
                          tract["body_row"], tract["group"], tract["source_columns_one_based"]),
                         ("BLPNM", "UCPPF", 7595, 127, 8, [44, 48]))
        self.assertEqual(frodo["source_columns_zero_based"], [9, 13])
        self.assertEqual(tract["source_columns_zero_based"], [43, 47])
        self.assertEqual(tract["context20"], "DINTRACTCOMEDUEDATEZ")
        self.assertNotIn("CONTRACT", tract["context20"])

    def test_unexplained_pad_parameters_and_finite_roster_stay_labeled(self):
        result = audit(SOURCE.read_bytes())
        self.assertEqual(result["native_fragment"]["decoded_literal"], "SHAREISPAGETTI")
        self.assertIn("unexplained", result["native_fragment"]["status"])
        self.assertEqual(len(result["finite_joyce_roster"]), 13)
        self.assertEqual(result["joyce_roster_hits"], [])
        self.assertIn("No rule", result["interpretation_gap"])

    def test_malformed_source_rejected(self):
        good = SOURCE.read_bytes()
        for raw in (b"", b"ABC", good.replace(b"blue", b"\xc3\xa9", 1),
                    good.replace(b"VXGFA", b"vxgfa", 1)):
            with self.subTest(raw_prefix=raw[:12]):
                with self.assertRaises((ValueError, UnicodeError)):
                    audit(raw)

    def test_cli_is_read_only_and_leaves_global_random_state_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cipher.txt"
            original = SOURCE.read_bytes()
            path.write_bytes(original)
            state = random.getstate()
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main([str(path)]), 0)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(random.getstate(), state)
            result = json.loads(output.getvalue())
            self.assertEqual(result["source_sha256"], SHA256)
            self.assertIn("not a recovered", result["status"])


if __name__ == "__main__":
    unittest.main()
