from __future__ import annotations

import gzip
import hashlib
import unittest

from scripts.binary_envelope_probe import ALPHABETS, SIGNATURES, keyed_alphabet
from scripts.binary_text_probe import apply_mask, mask_specs, printable_prefix, text_candidate
from scripts.nachtlorn_binary_research import (
    KEYS,
    apply_periodic,
    apply_route,
    byte_prefix_plausible,
    scan,
    single_stage_variants,
)
from tests.test_binary_envelope_probe import encode_bytes
from tests.test_nachtlorn_binary_research import has_payload


class BinaryTextProbeTests(unittest.TestCase):
    def test_all_masks_match_independent_byte_oracle_and_invert(self):
        source = bytes(range(256)) * 3
        for spec in mask_specs(KEYS):
            result = apply_mask(source, spec)
            if spec["kind"] == "xor":
                key = spec["key"].encode()
                expected = bytes(value ^ key[(i + spec["phase"]) % len(key)] for i, value in enumerate(source))
            elif spec["kind"] == "add":
                expected = bytes((value + spec["amount"]) % 256 for value in source)
            else:
                expected = source
            self.assertEqual(result, expected)
            self.assertEqual(apply_mask(result, spec, inverse=True), source)

    def test_text_candidate_is_language_independent_but_not_a_short_word_gate(self):
        data = b"ITEM,VALUE\n" * 20
        self.assertEqual(text_candidate(data)["sha256"], hashlib.sha256(data).hexdigest())
        self.assertIsNone(text_candidate(b"FRODO"))
        self.assertIsNone(text_candidate(data + b"\xff"))
        self.assertIsNone(text_candidate(b"A\0" * 100))
        self.assertIsNotNone(text_candidate(("é" * 100).encode()))

    def test_utf8_prefilter_accepts_partial_final_character(self):
        data = b"A" * 127 + "é".encode()
        self.assertTrue(printable_prefix(data))
        self.assertTrue(printable_prefix(data[:128]))
        self.assertTrue(byte_prefix_plausible(data[:128]))

    def test_object_headers_are_prefiltered_without_claiming_validity(self):
        for magic in SIGNATURES.values():
            self.assertTrue(byte_prefix_plausible(magic + b"\x80\xff" * 64))
        self.assertTrue(byte_prefix_plausible(b"\x78\x9c" + b"\x80\xff" * 64))
        self.assertTrue(byte_prefix_plausible(b"\x80\x04" + b"\x80\xff" * 64))

    def test_single_stage_and_mask_enumeration(self):
        self.assertEqual(sum(1 for _ in single_stage_variants("ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 2)), 125)
        self.assertEqual(len(mask_specs(KEYS)), 27)

    def test_full_byte_search_recovers_xor_compressed_numeric_json(self):
        payload = b"[1,2,3,999]"
        member = gzip.compress(payload, mtime=0)
        masked = apply_mask(member, {"kind": "xor", "key": "BLOOM", "phase": 3}, inverse=True)
        encoded = encode_bytes(masked, keyed_alphabet("BLOOM"), byteorder="little")
        route = {"kind": "columnar", "key": "NACHTLORN"}
        ciphertext = apply_route(encoded, route, inverse=True)
        report = scan(ciphertext, "byte-layer")
        self.assertEqual(report["path_configurations"], 125)
        self.assertTrue(has_payload(report, payload))

    def test_full_byte_search_finds_uncompressed_csv_without_english_scoring(self):
        payload = ("ITEM,VALUE\n" + "".join(f"ITEM,{i}\n" for i in range(20))).encode()
        masked = apply_mask(payload, {"kind": "add", "amount": -1}, inverse=True)
        alphabet = next(alphabet for name, alphabet, _ in ALPHABETS if name == "I0")
        encoded = encode_bytes(masked, alphabet)
        periodic = {"kind": "plus", "key": "BLOOM", "phase": 2}
        ciphertext = apply_periodic(encoded, periodic, inverse=True)
        report = scan(ciphertext, "byte-layer")
        wanted = hashlib.sha256(payload).hexdigest()
        self.assertTrue(any(r["text"]["sha256"] == wanted for r in report["text_candidates"]))

    def test_invalid_masks_rejected(self):
        for spec in ({"kind": "bad"}, {"kind": "xor", "key": "", "phase": 0},
                     {"kind": "xor", "key": "BLOOM", "phase": 5}):
            with self.assertRaises(ValueError):
                apply_mask(b"test", spec)


if __name__ == "__main__":
    unittest.main()
