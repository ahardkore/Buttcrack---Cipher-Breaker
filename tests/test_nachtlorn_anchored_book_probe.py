"""Exact address controls and a complete synthetic running-key recovery."""
import contextlib
import gzip
import io
from pathlib import Path
import tempfile
import unittest

from scripts.nachtlorn_anchored_book_probe import anchored_domains, main, scan
from scripts.nachtlorn_running_book_probe import END, scan_domains, transform
from tests.test_nachtlorn_colour_probe import POEM, encode26

BOOK = ("Stately, plump Buck Mulligan. A bowl of white china had stood beside her deathbed "
        "holding the green sluggish bile. The cold black marble bowl while two people stood. "
        "Notice because I’m in mourning myself. " + "Synthetic reference key material only. " * 100
        + "\n" + END + "\n").encode()


class AnchoredBookTests(unittest.TestCase):
    def test_eight_unique_addresses_and_starts(self):
        domains, positions = anchored_domains(BOOK)
        self.assertEqual(len(domains), 8)
        expected = {"deathbed-bowl": "BOWLOFWHITE", "after-deathbed-bowl": "OFWHITE",
                    "deathbed-white": "WHITECHINA", "deathbed-green": "GREENSLUGGISH",
                    "holy-water-black": "BLACKMARBLEBOWL", "holy-water-bowl": "BOWLWHILE",
                    "after-holy-water-bowl": "WHILE", "explicit-mourning": "MOURNINGMYSELF"}
        for name, prefix in expected.items():
            self.assertTrue(domains[name].startswith(prefix), name)
        self.assertEqual(len({p["normalized_story_character_offset"] for p in positions.values()}), 8)
        self.assertEqual(anchored_domains(BOOK.replace(b"\n", b"\r\n")), (domains, positions))

    def test_missing_ambiguous_and_insufficient_key_rejections(self):
        with self.assertRaises(ValueError):
            anchored_domains(BOOK.replace(b"cold black marble bowl", b"cold purple marble bowl"))
        with self.assertRaises(ValueError):
            anchored_domains(BOOK.replace(END.encode(), b"cold black marble bowl " + END.encode()))
        with self.assertRaises(ValueError):
            scan_domains("ABCDEFGHI", {"too-short": "ABC"}, "synthetic")

    def test_synthetic_packet_recovery_and_exact_marker_roundtrip(self):
        plain = encode26(gzip.compress(b'{"synthetic_control":"not puzzle evidence"}', mtime=0))
        domains, _ = anchored_domains(BOOK)
        cipher = transform(plain, domains["holy-water-black"], "minus", inverse=True) + "I"
        result = scan(cipher, BOOK)
        self.assertEqual(result["letter_paths"], 48)
        self.assertEqual(result["representation_configurations"], 1536)
        self.assertTrue(all(r["exact_original_letter_roundtrip"] for r in result["roundtrips"]))
        self.assertTrue(any(r["key_domain"] == "holy-water-black" and r["drop_final_i"]
                            and r["operation"] == "minus" and any(o["format"] == "gzip" for o in r["objects"])
                            for r in result["accepted_records"]))

    def test_cli_and_both_input_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            source, book, output = (Path(directory) / name for name in ("source.txt", "book.txt", "result.json"))
            original = (POEM + "ABCDEFGHI\n").encode()
            source.write_bytes(original)
            book.write_bytes(BOOK)
            args = [str(source), "--book", str(book), "--output", str(output)]
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 0)
                for path in (source, book):
                    with self.assertRaises(SystemExit):
                        main(args[:-1] + [str(path)])
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(book.read_bytes(), BOOK)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
