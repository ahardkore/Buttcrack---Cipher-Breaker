from __future__ import annotations

import contextlib
import gzip
import hashlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts.nachtlorn_running_book_probe import END, OPENING, START, inspect_packet, key_domains, main, scan, transform


def synthetic_book():
    return ("Synthetic control metadata\n" + START + "\nSynthetic production credit\n" + OPENING + "\n"
            + "Synthetic key material only not the actual novel\n" * 500 + END + "\nSynthetic license\n").encode("ascii")


def encode26(data):
    value, result = int.from_bytes(data, "big"), ""
    while value:
        value, digit = divmod(value, 26)
        result = chr(65 + digit) + result
    return result or "A"


class NachtlornRunningBookProbeTests(unittest.TestCase):
    def test_key_domains_have_exact_boundaries_and_do_not_repeat(self):
        domains = key_domains(synthetic_book())
        self.assertEqual(set(domains), {"raw-file", "gutenberg-body", "story"})
        self.assertTrue(domains["raw-file"].startswith("SYNTHETICCONTROLMETADATA"))
        self.assertTrue(domains["gutenberg-body"].startswith("SYNTHETICPRODUCTIONCREDIT"))
        self.assertTrue(domains["story"].startswith("STATELYPLUMPBUCKMULLIGAN"))
        self.assertNotIn("SYNTHETICLICENSE", domains["story"])
        for raw in (b"no boundaries", synthetic_book() + START.encode()):
            with self.assertRaises(ValueError):
                key_domains(raw)
        with self.assertRaises(ValueError):
            transform("ABCDE", "ABC", "minus")

    def test_all_signs_have_an_independent_literal_inverse(self):
        source, key = "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "ZYXWVUTSRQPONMLKJIHGFEDCBA"
        for kind in ("minus", "plus", "beaufort"):
            result = transform(source, key, kind)
            self.assertEqual(transform(result, key, kind, inverse=True), source)
            for index, (c, k) in enumerate(zip(source, key)):
                a, b = ord(c) - 65, ord(k) - 65
                expected = (a - b if kind == "minus" else a + b if kind == "plus" else b - a) % 26
                self.assertEqual(ord(result[index]) - 65, expected)
        for text, key, kind in (("", "ABC", "minus"), ("abc", "ABC", "minus"), ("ABC", "AB!", "plus"),
                                ("ABC", "ABC", "unknown")):
            with self.assertRaises(ValueError):
                transform(text, key, kind)

    def test_only_complete_origin_zero_packets_are_accepted(self):
        payload = b'{"synthetic":true,"values":[1,2,3,99]}'
        self.assertEqual(inspect_packet(payload)[0]["format"], "json")
        packet = gzip.compress(payload, mtime=0)
        records = inspect_packet(packet)
        self.assertTrue(any(r["format"] == "gzip" and r["classification"]["sha256"] == hashlib.sha256(payload).hexdigest()
                            for r in records))
        self.assertEqual(inspect_packet(b"x" + packet), [])
        self.assertEqual(inspect_packet(packet + b"x"), [])
        self.assertEqual(inspect_packet(packet[:-1]), [])

    def test_full_marker_running_key_numeric_gzip_object_control(self):
        book = synthetic_book()
        key = key_domains(book)["story"]
        payload = b'{"synthetic":true,"values":[1,2,3,99],"note":"not recovered puzzle text"}'
        encoded = encode26(gzip.compress(payload, mtime=0))
        source = transform(encoded, key, "minus", inverse=True) + "I"
        report = scan(source, book)
        self.assertEqual(report["letter_paths"], 18)
        self.assertEqual(report["representation_configurations"], 576)
        self.assertTrue(all(r["exact_original_letter_roundtrip"] for r in report["roundtrips"]))
        self.assertTrue(any(r["drop_final_i"] and r["key_domain"] == "story" and r["operation"] == "minus"
                            and any(obj.get("classification", {}).get("sha256") == hashlib.sha256(payload).hexdigest()
                                    for obj in r["objects"]) for r in report["accepted_records"]))

    def test_cli_cannot_overwrite_either_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source, book = Path(directory) / "source.txt", Path(directory) / "book.txt"
            source.write_bytes(b"source unchanged")
            book.write_bytes(b"book unchanged")
            for output in (source, book):
                original = output.read_bytes()
                with contextlib.redirect_stderr(io.StringIO()) as errors:
                    with self.assertRaises(SystemExit) as failure:
                        main([str(source), "--book", str(book), "--output", str(output)])
                self.assertEqual(failure.exception.code, 2)
                self.assertIn("must not overwrite", errors.getvalue())
                self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
