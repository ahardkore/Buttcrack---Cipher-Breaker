from __future__ import annotations

import bz2
import gzip
import hashlib
import io
import json
import lzma
import pickle
import sys
import unittest
import zipfile
import zlib
from unittest import mock

from scripts.binary_envelope_probe import (
    A26, ALPHABETS, decode_base26, decompress_member, describe, inspect_binary,
)


def encode_bytes(data, alphabet=A26, bias=0, byteorder="big"):
    value = int.from_bytes(data, byteorder)
    if not value:
        if bias:
            raise ValueError("zero has no nonempty bijective representation")
        return alphabet[0]
    digits = []
    while value:
        value, digit = divmod(value - bias, 26)
        digits.append(alphabet[digit])
    return "".join(reversed(digits))


class BinaryEnvelopeProbeTests(unittest.TestCase):
    def test_known_base26_vectors(self):
        self.assertEqual(decode_base26("A"), b"\x00")
        self.assertEqual(decode_base26("Z"), b"\x19")
        self.assertEqual(decode_base26("BA"), b"\x1a")
        self.assertEqual(decode_base26("Z", bias=1), b"\x1a")
        self.assertEqual(decode_base26("AA", bias=1), b"\x1b")

    def test_all_alphabets_and_byteorders_roundtrip(self):
        data = b"\x1f\x8b\x08binary data ending in a nonzero byte!"
        for _, alphabet, bias in ALPHABETS:
            for byteorder in ("big", "little"):
                encoded = encode_bytes(data, alphabet, bias, byteorder)
                self.assertEqual(decode_base26(encoded, alphabet, bias, byteorder=byteorder), data)

    def test_long_input_does_not_change_integer_string_limit(self):
        old_limit = sys.get_int_max_str_digits()
        try:
            sys.set_int_max_str_digits(640)
            data = bytes(range(1, 256)) * 12
            encoded = encode_bytes(data)
            self.assertGreater(len(encoded), 4300)
            self.assertEqual(decode_base26(encoded), data)
            self.assertEqual(sys.get_int_max_str_digits(), 640)
        finally:
            sys.set_int_max_str_digits(old_limit)

    def test_partial_block_keeps_terminal_i_and_overflow_is_rejected(self):
        self.assertEqual(decode_base26("AAAAAI", block_width=5, byte_width=3), b"\0\0\0\x08")
        with self.assertRaises(ValueError):
            decode_base26("ZZZZZZZ", block_width=7, byte_width=4)

    def test_bad_arguments_rejected(self):
        for text, alphabet, bias in (("", A26, 0), ("abc", A26, 0), ("A B", A26, 0),
                                    ("ABC", "A" * 26, 0), ("ABC", A26, 2)):
            with self.assertRaises(ValueError):
                decode_base26(text, alphabet, bias)
        with self.assertRaises(ValueError):
            decode_base26("ABC", byte_width=3)

    def test_four_wrapped_formats_need_no_english_gate(self):
        payload = b'{"values":[1,2,3,999]}'
        for kind, member in (("gzip", gzip.compress(payload, mtime=0)), ("zlib", zlib.compress(payload)),
                             ("bzip2", bz2.compress(payload)), ("xz", lzma.compress(payload))):
            with self.subTest(kind=kind):
                result = inspect_binary(member)
                record = next(r for r in result["verified"] if r["format"] == kind and r["offset"] == 0)
                self.assertEqual(record["classification"]["sha256"], hashlib.sha256(payload).hexdigest())
                self.assertEqual(record["classification"]["kind"], "json")
                self.assertEqual(record["trailing_bytes"], 0)

    def test_embedded_member_reports_exact_consumption_and_offset(self):
        payload = b"not necessarily English\0\xff\x80"
        member = gzip.compress(payload, mtime=0)
        result = inspect_binary(b"prefix123" + member + b"tail")
        record = next(r for r in result["verified"] if r["format"] == "gzip")
        self.assertEqual((record["offset"], record["compressed_bytes"], record["trailing_bytes"]),
                         (9, len(member), 4))
        self.assertEqual(record["classification"]["sha256"], hashlib.sha256(payload).hexdigest())

    def test_truncation_and_bad_checksum_are_not_recoveries(self):
        payload = b"checksum validation" * 20
        for kind, member in (("gzip", gzip.compress(payload, mtime=0)), ("zlib", zlib.compress(payload)),
                             ("bzip2", bz2.compress(payload)), ("xz", lzma.compress(payload))):
            self.assertIsNone(decompress_member(member[:-1], kind))
        member = zlib.compress(payload)
        self.assertIsNone(decompress_member(member[:-1] + bytes([member[-1] ^ 1]), "zlib"))

    def test_overlapping_zlib_headers_do_not_hide_a_valid_member(self):
        payload = b"overlapping header control" * 20
        member = zlib.compress(payload, wbits=10)
        self.assertEqual(member[0], 0x28)
        # 0x5828 is also a valid zlib header; a two-byte finditer would skip offset1.
        result = inspect_binary(b"\x58" + member)
        record = next(r for r in result["verified"] if r["format"] == "zlib" and r["offset"] == 1)
        self.assertEqual(record["classification"]["sha256"], hashlib.sha256(payload).hexdigest())

    def test_output_limit_is_enforced_for_every_compressor(self):
        data = b"A" * 10000
        for kind, member in (("gzip", gzip.compress(data, mtime=0)), ("zlib", zlib.compress(data)),
                             ("bzip2", bz2.compress(data)), ("xz", lzma.compress(data))):
            self.assertIsNone(decompress_member(member, kind, limit=99))

    def test_preset_dictionary_requires_matching_id_and_valid_content(self):
        dictionary = b"Joyce Bloom4300 morning bowl stairs. " * 100
        payload = b'{"book":"Joyce Bloom4300 morning bowl stairs."}'
        compressor = zlib.compressobj(zdict=dictionary)
        member = compressor.compress(payload) + compressor.flush()
        self.assertEqual(inspect_binary(member)["verified"], [])
        result = inspect_binary(member, {zlib.adler32(dictionary): dictionary})
        self.assertEqual(result["dictionary_id_matches"], 1)
        record = next(r for r in result["verified"] if r["format"] == "zlib")
        self.assertEqual(record["classification"]["sha256"], hashlib.sha256(payload).hexdigest())
        wrong = inspect_binary(member, {zlib.adler32(dictionary): b"wrong dictionary"})
        self.assertEqual(wrong["verified"], [])

    def test_json_is_complete_and_strict(self):
        self.assertEqual(describe(b" 42\n")["kind"], "json")
        self.assertEqual(describe(b'{"x":NaN}')["kind"], "unclassified-bytes")
        self.assertEqual(describe(b'{"x":1}garbage')["kind"], "unclassified-bytes")

    def test_pickle_is_statically_parsed_never_loaded(self):
        benign = pickle.dumps({"values": [1, 2, 3]}, protocol=4)
        executable = b"\x80\x02cposix\nsystem\n(Vecho DO_NOT_EXECUTE\ntR."
        with mock.patch("pickle.loads", side_effect=AssertionError("must not load")):
            self.assertEqual(describe(benign)["kind"], "pickle-static-only")
            record = describe(executable)
            self.assertEqual(record["kind"], "pickle-static-only")
            self.assertTrue(record["executable_opcodes_present"])
        self.assertEqual(describe(benign + b"extra")["kind"], "unclassified-bytes")

    def test_archive_is_read_in_memory_never_extracted(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("../../do-not-extract.json", b'{"values":[1,2,3]}')
        with mock.patch.object(zipfile.ZipFile, "extractall", side_effect=AssertionError("must not extract")):
            record = next(r for r in inspect_binary(stream.getvalue())["verified"] if r["format"] == "zip")
        self.assertEqual(record["members"][0]["classification"]["kind"], "json")

    def test_header_alone_is_not_verified(self):
        result = inspect_binary(b"%PDF-1.7\nnot a validated PDF")
        self.assertEqual(result["verified"], [])
        self.assertEqual(result["signature_headers"], [{"format": "pdf", "offset": 0}])


if __name__ == "__main__":
    unittest.main()
