from __future__ import annotations

import gzip
import hashlib
import itertools
import math
import random
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

from scripts import nachtlorn_stored_gzip_probe as probe
from scripts.nachtlorn_prefix_invariants import ALPHABET, count_interval, numeral


def stored_packet(payload, padding=0, final=True):
    size = len(payload)
    header = b"\x1f\x8b\x08\0" + (123456).to_bytes(4, "little") + b"\0\xff"
    block = bytes([(padding << 3) | int(final)]) + size.to_bytes(2, "little") + (size ^ 65535).to_bytes(2, "little")
    return header + block + payload + (zlib.crc32(payload) & 0xffffffff).to_bytes(4, "little") + size.to_bytes(4, "little")


def encode(value, alphabet, bias):
    digits = []
    while value:
        value, digit = divmod(value - bias, len(alphabet))
        digits.append(alphabet[digit])
    return "".join(reversed(digits)) or alphabet[0]


def fixture(bias=0, corrupt_crc=False, corrupt_complement=False):
    payload = bytes(range(256)) + b"independent stored-block control" * 2
    packet = bytearray(stored_packet(payload, padding=31))
    if corrupt_crc:
        packet[-8] ^= 1
    if corrupt_complement:
        packet[13] ^= 1
    packet = bytes(packet)
    alphabet = ALPHABET[::-1]
    mapping = {glyph: i for i, glyph in enumerate(alphabet)}
    text = encode(int.from_bytes(packet, "little"), alphabet, bias)
    minimal_bytes = len(packet.rstrip(b"\0"))
    case = next(c for c in probe.length_cases(text, bias) if c["minimal_bytes"] == minimal_bytes
                and c["restored_trailing_zero_bytes"] == len(packet) - minimal_bytes)
    return text, mapping, case, packet, payload


class StoredArithmeticTests(unittest.TestCase):
    def test_prefix_covers_match_exhaustive_permutations_and_counts(self):
        rng = random.Random(4300)
        alphabet = "ABCD"
        for text in ("A", "ABBA", "ABCDA", "DABACAB"):
            for bias in (0, 1):
                values = [(dict(zip(alphabet, p)), numeral(text, dict(zip(alphabet, p)), 4, bias))
                          for p in itertools.permutations(range(4))]
                maximum = 2 * 4 ** len(text)
                intervals = [(0, maximum), (-10, -1)]
                intervals += [tuple(sorted((rng.randrange(maximum), rng.randrange(maximum)))) for _ in range(12)]
                for low, high in intervals:
                    covers = probe.interval_covers(text, low, high, alphabet=alphabet, bias=bias)
                    total = sum(math.factorial(4 - len(c)) for c in covers)
                    self.assertEqual(total, count_interval(text, low, high, alphabet=alphabet, bias=bias)["alphabet_mappings"])
                    for mapping, value in values:
                        matches = sum(all(mapping[k] == v for k, v in cover.items()) for cover in covers)
                        self.assertEqual(matches, int(low <= value <= high))

    def test_cover_rejects_reversed_interval(self):
        with self.assertRaises(ValueError):
            probe.interval_covers("AB", 10, 0, alphabet="AB")

    def test_complete_packet_and_ignored_padding_are_validated_independently(self):
        payload = bytes(range(256)) + b"control"
        for padding in (0, 1, 31):
            packet = stored_packet(payload, padding)
            self.assertEqual(gzip.decompress(packet), payload)
            result = probe.verify_packet(packet)
            self.assertTrue(result["complete_stream_verified"])
            self.assertEqual(result["payload_sha256"], hashlib.sha256(payload).hexdigest())

    def test_crc_failure_is_distinct_from_packet_grammar(self):
        packet = bytearray(stored_packet(b"CRC control"))
        packet[-8] ^= 1
        result = probe.verify_packet(bytes(packet))
        self.assertTrue(result["grammar_valid"])
        self.assertFalse(result["crc32_valid"])
        self.assertFalse(result["complete_stream_verified"])

    def test_wrong_complement_nonfinal_block_and_optional_flags_are_outside_scope(self):
        packet = stored_packet(b"scope control")
        for index, mask in ((13, 1), (10, 1), (3, 8), (-1, 1)):
            changed = bytearray(packet)
            changed[index] ^= mask
            self.assertFalse(probe.verify_packet(bytes(changed))["grammar_valid"])

    def test_length_and_zero_restoration_are_derived_from_the_trailer(self):
        for bias in (0, 1):
            _text, _mapping, case, packet, payload = fixture(bias)
            self.assertEqual(case["payload_bytes"], len(payload))
            self.assertEqual(case["minimal_bytes"] + case["restored_trailing_zero_bytes"], len(packet))
            self.assertEqual(case["restored_trailing_zero_bytes"], 2)
            self.assertEqual(bytes.fromhex(case["high_prefix_hex"]), len(payload).to_bytes(4, "little").rstrip(b"\0")[::-1])

    def test_absent_solver_is_not_an_exclusion(self):
        with mock.patch.object(probe, "z3", None), self.assertRaisesRegex(RuntimeError, "not an exclusion"):
            probe.build_stored_query("AB", 0, {"payload_bytes": 1}, [])

    def test_source_overwrite_and_invalid_budgets_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            source.write_text("unchanged", encoding="ascii")
            for args in ([str(source), "--output", str(source)],
                         [str(source), "--output", str(source.with_suffix(".json")), "--budget-ms", "0"],
                         [str(source), "--output", str(source.with_suffix(".json")), "--candidate-cap", "0"]):
                with self.assertRaises(SystemExit):
                    probe.main(args)
            self.assertEqual(source.read_text(), "unchanged")


@unittest.skipUnless(probe.z3 is not None, "optional z3-solver research dependency not installed")
class StoredSolverTests(unittest.TestCase):
    def test_known_relabelled_complete_packets_are_recovered_under_both_biases(self):
        for bias in (0, 1):
            text, mapping, case, packet, payload = fixture(bias)
            result = probe.search_case(text, bias, case, fixed=mapping, budget_ms=2000)
            self.assertEqual(result["status"], "verified_packet", result)
            self.assertEqual(result["candidate_numerals_checked"], 1)
            audit = result["candidate_audits"][0]
            self.assertEqual(audit["packet_sha256"], hashlib.sha256(packet).hexdigest())
            self.assertEqual(audit["packet_checks"]["payload_sha256"], hashlib.sha256(payload).hexdigest())
            self.assertTrue(audit["exact_retained_letter_roundtrip"])

    def test_corrupt_crc_exhausts_fixed_mapping_without_acceptance(self):
        text, mapping, case, _packet, _payload = fixture(corrupt_crc=True)
        result = probe.search_case(text, 0, case, fixed=mapping, budget_ms=2000)
        self.assertEqual(result["status"], "exhausted_no_packet", result)
        self.assertTrue(result["exact_exclusion"])
        self.assertEqual(result["candidate_numerals_checked"], 1)
        self.assertFalse(result["candidate_audits"][0]["packet_checks"]["crc32_valid"])

    def test_corrupt_complement_is_rejected_by_symbolic_structure(self):
        text, mapping, case, _packet, _payload = fixture(corrupt_complement=True)
        result = probe.search_case(text, 0, case, fixed=mapping, budget_ms=2000)
        self.assertEqual(result["status"], "exhausted_no_packet", result)
        self.assertEqual(result["candidate_numerals_checked"], 0)

    def test_candidate_cap_is_not_an_exhaustive_negative(self):
        text, mapping, case, _packet, _payload = fixture(corrupt_crc=True)
        result = probe.search_case(text, 0, case, fixed=mapping, budget_ms=2000, candidate_cap=1)
        self.assertEqual(result["status"], "candidate_cap", result)
        self.assertFalse(result["exact_exclusion"])

    def test_unknown_is_not_an_exclusion(self):
        text, _mapping, case, _packet, _payload = fixture()
        solver = mock.Mock()
        solver.to_smt2.return_value = "synthetic formula"
        solver.check.return_value = probe.z3.unknown
        solver.reason_unknown.return_value = "timeout"
        with mock.patch.object(probe, "build_stored_query", return_value=(solver, {})):
            result = probe.search_case(text, 0, case)
        self.assertEqual((result["status"], result["reason"]), ("unknown", "timeout"))
        self.assertFalse(result["exact_exclusion"])
        solver.model.assert_not_called()

    def test_expired_case_budget_is_not_an_exclusion(self):
        text, _mapping, case, _packet, _payload = fixture()
        solver = mock.Mock()
        solver.to_smt2.return_value = "synthetic formula"
        with mock.patch.object(probe, "build_stored_query", return_value=(solver, {})), mock.patch.object(probe.time, "monotonic", side_effect=[0.0, 31.0, 31.0]):
            result = probe.search_case(text, 0, case)
        self.assertEqual(result["status"], "budget_exhausted")
        self.assertFalse(result["exact_exclusion"])
        solver.check.assert_not_called()


if __name__ == "__main__":
    unittest.main()
