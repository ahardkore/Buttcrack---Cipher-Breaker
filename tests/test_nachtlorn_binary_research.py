from __future__ import annotations

import contextlib
import gzip
import hashlib
import io
import json
import random
import tempfile
import unittest
import zlib
from pathlib import Path

from scripts.binary_envelope_probe import ALPHABETS, decode_base26, inspect_binary, keyed_alphabet
from scripts.binary_text_probe import apply_mask
from scripts.nachtlorn_binary_research import (
    apply_periodic,
    apply_route,
    book_dictionaries,
    main,
    periodic_specs,
    route_specs,
    scan,
    variants,
)
from tests.test_binary_envelope_probe import encode_bytes


def has_payload(report, payload):
    wanted = hashlib.sha256(payload).hexdigest()
    return any(obj.get("classification", {}).get("sha256") == wanted
               for record in report["verified_records"] for obj in record["objects"])


class NachtlornBinaryResearchTests(unittest.TestCase):
    def test_enumeration_counts(self):
        self.assertEqual(len(periodic_specs()), 97)
        self.assertEqual(len(route_specs()), 29)
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 2 + "I"
        self.assertEqual(sum(1 for _ in variants(text, "periodic-then-route")), 2813)
        self.assertEqual(sum(1 for _ in variants(text, "route-then-periodic")), 2688)

    def test_every_transform_roundtrips_ragged_input_without_global_rng_changes(self):
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 5 + "I"
        state = random.getstate()
        for spec in periodic_specs():
            self.assertEqual(apply_periodic(apply_periodic(text, spec, inverse=True), spec), text)
        for spec in route_specs():
            self.assertEqual(apply_route(apply_route(text, spec, inverse=True), spec), text)
        self.assertEqual(random.getstate(), state)

    def test_full_first_order_search_recovers_nonprose_gzip_json(self):
        payload = b"[1,2,3,999]"
        encoded = encode_bytes(gzip.compress(payload, mtime=0), keyed_alphabet("NACHTLORN"))
        periodic = {"kind": "porta", "key": "NACHTLORN", "phase": 3}
        route = {"kind": "myszkowski", "key": "BLOOM"}
        ciphertext = apply_periodic(apply_route(encoded, route, inverse=True), periodic, inverse=True)
        report = scan(ciphertext, "periodic-then-route")
        self.assertEqual(report["path_configurations"], 2813)
        self.assertTrue(has_payload(report, payload))

    def test_full_other_order_recovers_bijective_little_endian_dictionary_zlib(self):
        payload = b"[2,3,5,1000]"
        dictionary = b"Joyce Bloom morning bowl stairs. " * 100
        compressor = zlib.compressobj(zdict=dictionary)
        member = compressor.compress(payload) + compressor.flush()
        encoded = encode_bytes(member, bias=1, byteorder="little")
        periodic = {"kind": "minus", "key": "BLPNM", "phase": 4}
        route = {"kind": "shuffle", "unit": 5, "indent_draws": 146, "inverse": True}
        ciphertext = apply_route(apply_periodic(encoded, periodic, inverse=True), route, inverse=True)
        report = scan(ciphertext, "route-then-periodic", {zlib.adler32(dictionary): dictionary})
        self.assertEqual(report["path_configurations"], 2688)
        self.assertTrue(has_payload(report, payload))
        self.assertGreater(report["preset_dictionary_id_matches"], 0)

    def test_book_dictionary_metadata_and_collision_free_ids(self):
        raw = b"Blue bowl.\n" + b"Joyce at dawn.\n" * 4000
        dictionaries, metadata = book_dictionaries(raw)
        self.assertEqual(len(metadata), 4)
        self.assertEqual(len(dictionaries), 4)
        self.assertEqual(metadata[0]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(dictionaries[int(metadata[0]["adler32"], 16)], raw)
        for item in metadata:
            data = dictionaries[int(item["adler32"], 16)]
            self.assertEqual(len(data), item["bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])

    def test_invalid_source_and_order_rejected(self):
        with self.assertRaises(ValueError):
            scan("ABC def", "periodic-then-route")
        with self.assertRaises(ValueError):
            scan("ABC", "unknown")

    def test_all_recorded_actual_header_buffers_replay_without_scratch_inputs(self):
        root = Path(__file__).resolve().parents[1]
        source = "".join(c for row in (root / "docs/data/nachtlorn-transcript.txt").read_text().splitlines()[8:]
                         for c in row if "A" <= c <= "Z")
        replayed = jpeg = 0
        for filename in ("nachtlorn-binary-key-route.json", "nachtlorn-binary-route-key.json"):
            report = json.loads((root / "docs/data" / filename).read_text())
            self.assertEqual(report["preset_dictionary_id_matches"], 0)
            self.assertEqual(sum(len(r["headers"]) for r in report["header_examples"]),
                             report["magic_headers_recorded"])
            for record in report["header_examples"]:
                if report["mode"] == "periodic-then-route":
                    text = apply_route(apply_periodic(source, record["periodic"]), record["route"])
                else:
                    text = apply_periodic(apply_route(source, record["route"]), record["periodic"])
                _, alphabet, bias = next(a for a in ALPHABETS if a[0] == record["alphabet"])
                data = decode_base26(text, alphabet, bias, record["block_width"],
                                     record["byte_width"], record["byteorder"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), record["binary_sha256"])
                result = inspect_binary(data)
                self.assertEqual(result["verified"], [])
                self.assertEqual(result["signature_headers"], record["headers"])
                for header in record["headers"]:
                    if header["format"] == "jpeg":
                        jpeg += 1
                        tail = data[header["offset"]:]
                        self.assertGreater(int.from_bytes(tail[4:6], "big"), len(tail) - 4)
                replayed += 1
        self.assertEqual((replayed, jpeg), (121, 8))

    def test_terminal_marker_header_records_replay_without_external_inputs(self):
        root = Path(__file__).resolve().parents[1]
        original = "".join(c for row in (root / "docs/data/nachtlorn-transcript.txt").read_text().splitlines()[8:]
                           for c in row if "A" <= c <= "Z")
        self.assertTrue(original.endswith("I"))
        source, replayed = original[:-1], 0
        for suffix in ("key-route", "route-key"):
            report = json.loads((root / f"docs/data/nachtlorn-terminal-i-{suffix}.json").read_text())
            self.assertEqual(report["source_extraction"], {"original_body_letters": 8736,
                                                         "retained_body_letters": 8735, "removed_terminal": "I"})
            self.assertEqual(report["preset_dictionary_id_matches"], 0)
            self.assertEqual(sum(len(r["headers"]) for r in report["header_examples"]), report["magic_headers_recorded"])
            for record in report["header_examples"]:
                text = (apply_route(apply_periodic(source, record["periodic"]), record["route"])
                        if report["mode"] == "periodic-then-route" else
                        apply_periodic(apply_route(source, record["route"]), record["periodic"]))
                _, alphabet, bias = next(a for a in ALPHABETS if a[0] == record["alphabet"])
                data = decode_base26(text, alphabet, bias, record["block_width"], record["byte_width"], record["byteorder"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), record["binary_sha256"])
                result = inspect_binary(data)
                self.assertEqual(result["signature_headers"], record["headers"])
                self.assertEqual(result["verified"], [])
                replayed += 1
        self.assertEqual(replayed, 90)

    def test_literal_lowercase_acrostic_byte_key(self):
        payload = b'{"synthetic":true,"samples":[1,2,3,999],"note":"inserted I is only a hypothesis"}'
        data = apply_mask(gzip.compress(payload, mtime=0), {"kind": "xor", "key": "bloom", "phase": 3})
        report = scan(encode_bytes(data), "byte-layer", byte_keys=("bloom",))
        self.assertTrue(has_payload(report, payload))
        self.assertEqual({s["key"] for s in report["specification"]["byte_masks"] if s["kind"] == "xor"},
                         {"bloom"})
        with self.assertRaises(ValueError):
            scan("ABC", "periodic-then-route", byte_keys=("bloom",))

    def test_terminal_literal_I_is_an_explicit_readonly_extraction(self):
        payload = b'{"synthetic":true,"marker":"terminal I is not part of this compressed integer"}'
        ciphertext = encode_bytes(gzip.compress(payload, mtime=0))
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "original.txt", Path(directory) / "report.json"
            raw = ("synthetic header\n" * 8 + ciphertext + "I\n").encode("ascii")
            source.write_bytes(raw)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(source), "--mode", "byte-layer", "--drop-final-i",
                                       "--output", str(output)]), 0)
            report = json.loads(output.read_text())
            self.assertTrue(has_payload(report, payload))
            self.assertEqual(report["source_extraction"], {"original_body_letters": len(ciphertext) + 1,
                                                         "retained_body_letters": len(ciphertext),
                                                         "removed_terminal": "I"})
            self.assertEqual(source.read_bytes(), raw)

    def test_cli_cannot_overwrite_either_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source, dictionary = Path(directory) / "source.txt", Path(directory) / "book.txt"
            source.write_bytes(b"source")
            dictionary.write_bytes(b"book")
            for output in (source, dictionary):
                with contextlib.redirect_stderr(io.StringIO()) as errors, self.assertRaises(SystemExit) as failure:
                    main([str(source), "--dictionary", str(dictionary), "--mode",
                          "periodic-then-route", "--output", str(output)])
                self.assertEqual(failure.exception.code, 2)
                self.assertIn("must not overwrite", errors.getvalue())
            self.assertEqual(source.read_bytes(), b"source")
            self.assertEqual(dictionary.read_bytes(), b"book")


if __name__ == "__main__":
    unittest.main()
