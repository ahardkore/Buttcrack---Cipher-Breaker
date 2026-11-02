from __future__ import annotations

import bz2
import gzip
import hashlib
import itertools
import json
import lzma
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import nachtlorn_little_endian_probe as probe
from scripts.nachtlorn_prefix_invariants import ALPHABET, header_catalog, numeral


def encode(value, alphabet, bias):
    digits = []
    while value:
        value, digit = divmod(value - bias, len(alphabet))
        digits.append(alphabet[digit])
    return "".join(reversed(digits)) or alphabet[0]


class ResidueTests(unittest.TestCase):
    def test_modular_coefficients_match_full_scalar_arithmetic(self):
        rng = random.Random(4300)
        for alphabet in ("ABC", "ABCD", ALPHABET):
            mapping = dict(zip(alphabet, rng.sample(range(len(alphabet)), len(alphabet))))
            text = "".join(rng.choice(alphabet) for _ in range(200))
            for bias in (0, 1):
                for bits in (1, 8, 16, 48, 80):
                    coefficients, shift = probe.residue_coefficients(text, bits, alphabet=alphabet, bias=bias)
                    residue = (sum(coefficients[glyph] * digit for glyph, digit in mapping.items()) + shift) % (1 << bits)
                    self.assertEqual(residue, numeral(text, mapping, len(alphabet), bias) % (1 << bits))

    def test_only_last_eighty_digits_affect_an_eighty_bit_residue(self):
        tail = ALPHABET * 4
        self.assertEqual(probe.residue_coefficients("A" * 1000 + tail, 80),
                         probe.residue_coefficients("Z" * 2000 + tail, 80))

    def test_exact_roundtrip_preserves_leading_zero_glyph(self):
        mapping = {c: i for i, c in enumerate(ALPHABET)}
        for bias in (0, 1):
            text = "AABCAI"
            self.assertTrue(probe.exact_roundtrip(text, mapping, numeral(text, mapping, 26, bias), 26, bias))

    def test_missing_solver_is_not_a_negative_result(self):
        with mock.patch.object(probe, "z3", None), self.assertRaisesRegex(RuntimeError, "missing solver"):
            probe.build_query("AB", (b"x",), alphabet="AB")

    def test_published_witnesses_verify_without_rerunning_the_solver(self):
        root = Path(__file__).resolve().parents[1]
        raw = (root / "docs/data/nachtlorn-transcript.txt").read_bytes()
        text = "".join(c for row in raw.decode("ascii").splitlines()[8:] for c in row if "A" <= c <= "Z")
        report = json.loads((root / "docs/data/nachtlorn-reset-little-endian-results.json").read_text())
        self.assertEqual(report["source_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(report["source_sha256"], "04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e")
        self.assertEqual(report["headers"], {k: [h.hex() for h in v] for k, v in header_catalog().items()})
        self.assertEqual(len(report["cases"]), 4)
        for case in report["cases"]:
            retained = text[:-1] if case["drop_final_i"] else text
            self.assertEqual(len(retained), case["retained_letters"])
            for family in case["families"]:
                self.assertIn(family["status"], ("sat", "unsat", "unknown"))
                if family["status"] != "sat":
                    self.assertNotIn("witness", family)
                    self.assertNotIn("witness_packet_check", family)
                    if family["status"] == "unknown":
                        self.assertTrue(family["reason"])
                    continue
                witness = family["witness"]
                alphabet = witness["digit_alphabet"]
                self.assertEqual(set(alphabet), set(ALPHABET))
                mapping = {glyph: i for i, glyph in enumerate(alphabet)}
                value = numeral(retained, mapping, 26, case["bias"])
                data = value.to_bytes(max(1, (value.bit_length() + 7) // 8), "little")
                self.assertEqual(hashlib.sha256(data).hexdigest(), witness["binary_sha256"])
                header = bytes.fromhex(witness["matched_header_hex"])
                self.assertIn(header, header_catalog()[family["format"]])
                self.assertTrue(data.startswith(header))
                self.assertTrue(probe.exact_roundtrip(retained, mapping, value, 26, case["bias"]))
                self.assertEqual(probe.check_witness(retained, family, family["format"], case["bias"]),
                                 family["witness_packet_check"])

    def test_source_overwrite_and_nonpositive_timeout_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.txt"
            path.write_text("unchanged", encoding="ascii")
            for arguments in ([str(path), "--output", str(path)],
                              [str(path), "--output", str(path.with_suffix(".json")), "--timeout-ms", "0"]):
                with self.assertRaises(SystemExit):
                    probe.main(arguments)
            self.assertEqual(path.read_text(), "unchanged")

    def test_invalid_modulus_width_is_rejected(self):
        with self.assertRaises(ValueError):
            probe.residue_coefficients("AB", 0, alphabet="AB")


@unittest.skipUnless(probe.z3 is not None, "optional z3-solver research dependency not installed")
class SolverTests(unittest.TestCase):
    def test_solver_matches_small_alphabet_exhaustion(self):
        for text in ("AB", "ABACAB", "ABCDABCD"):
            alphabet = "ABCD"
            for bias in (0, 1):
                values = [numeral(text, dict(zip(alphabet, p)), 4, bias)
                          for p in itertools.permutations(range(4))]
                for headers in ((b"\x00",), (b"\xff",), (b"\x11", b"\x22"), (b"\x01\x00",),
                                (values[0].to_bytes(max(1, (values[0].bit_length() + 7) // 8), "little")[:2],)):
                    expected = any(any(value.to_bytes(max(1, (value.bit_length() + 7) // 8), "little").startswith(h)
                                       for h in headers) for value in values)
                    result = probe.solve_family(text, headers, alphabet=alphabet, bias=bias, timeout_ms=2000)
                    self.assertEqual(result["status"], "sat" if expected else "unsat", result)

    def test_minimal_bytes_cannot_truncate_a_header_ending_in_zero(self):
        result = probe.solve_family("AB", (b"\x01\x00",), alphabet="AB", timeout_ms=2000)
        self.assertEqual(result["status"], "unsat")

    def test_unknown_remains_unknown_and_does_not_request_a_model(self):
        solver = mock.Mock()
        solver.to_smt2.return_value = "synthetic formula"
        solver.check.return_value = probe.z3.unknown
        solver.reason_unknown.return_value = "timeout"
        with mock.patch.object(probe, "build_query", return_value=(solver, {})):
            result = probe.solve_family("AB", (b"x",), alphabet="AB")
        self.assertEqual((result["status"], result["reason"]), ("unknown", "timeout"))
        self.assertNotIn("witness", result)
        solver.model.assert_not_called()

    def test_fixed_alphabets_recover_complete_synthetic_packets(self):
        alphabet = ALPHABET[::-1]
        mapping = {c: i for i, c in enumerate(alphabet)}
        payload = b'{"objects":[2,3,5],"scope":"synthetic control"}' * 2
        import zlib
        members = {"gzip": gzip.compress(payload, mtime=0), "zlib": zlib.compress(payload),
                   "bzip2": bz2.compress(payload), "xz": lzma.compress(payload)}
        for name, member in members.items():
            for bias in (0, 1):
                text = encode(int.from_bytes(member, "little"), alphabet, bias)
                result = probe.solve_family(text, header_catalog()[name], bias=bias, fixed=mapping, timeout_ms=2000)
                self.assertEqual(result["status"], "sat", result)
                self.assertTrue(result["witness"]["exact_retained_letter_roundtrip"])
                packet = probe.check_witness(text, result, name, bias)
                self.assertTrue(packet["complete_stream_verified"], packet)
                self.assertTrue(any(r["output_sha256"] == hashlib.sha256(payload).hexdigest()
                                    and r["consumed_bytes"] == len(member) for r in packet["accepted_records"]))

    def test_bad_models_are_rejected_before_solving(self):
        for headers, fixed in (((), {}), ((b"",), {}), ((b"a", b"aa"), {}),
                               ((b"a",), {"A": 0, "B": 0}), ((b"a",), {"A": 4})):
            with self.assertRaises(ValueError):
                probe.build_query("ABCD", headers, alphabet="ABCD", fixed=fixed)
        with self.assertRaises(ValueError):
            probe.build_query("ABCD", (b"x",), alphabet="ABCD", timeout_ms=0)


if __name__ == "__main__":
    unittest.main()
