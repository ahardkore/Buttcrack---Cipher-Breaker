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
import zlib
from pathlib import Path

from scripts.nachtlorn_prefix_invariants import (
    ALPHABET,
    count_interval,
    header_catalog,
    main,
    numeral,
    numeric_bounds,
    prefix_interval,
    scan,
)


def encode(value, alphabet, bias):
    digits = []
    while value:
        value, digit = divmod(value - bias, len(alphabet))
        digits.append(alphabet[digit])
    return "".join(reversed(digits)) or alphabet[0]


class PrefixInvariantTests(unittest.TestCase):
    def test_interval_counts_match_exhaustive_permutations(self):
        alphabet = "ABCD"
        rng = random.Random(4300)
        for text in ("A", "AAAA", "ABBA", "ABCDA", "DBACAB", "ABCDABCD"):
            for bias in (0, 1):
                values = [(dict(zip(alphabet, permutation)), numeral(text, dict(zip(alphabet, permutation)), 4, bias))
                          for permutation in itertools.permutations(range(4))]
                ceiling = 2 * 4 ** len(text)
                intervals = [(-5, -1), (0, 0), (0, ceiling)]
                intervals += [tuple(sorted((rng.randrange(ceiling), rng.randrange(ceiling)))) for _ in range(12)]
                intervals += [(value, value) for _mapping, value in values[:3]]
                for fixed in ({}, {"A": 0}, {"D": 3}):
                    for low, high in intervals:
                        expected = sum(low <= value <= high and all(mapping[k] == v for k, v in fixed.items())
                                       for mapping, value in values)
                        with self.subTest(text=text, bias=bias, fixed=fixed, interval=(low, high)):
                            result = count_interval(text, low, high, alphabet=alphabet, bias=bias, fixed=fixed)
                            self.assertEqual(result["alphabet_mappings"], expected)
                            if expected:
                                witness = result["witness_mapping"]
                                self.assertEqual(set(witness.values()), set(range(4)))
                                self.assertTrue(all(witness[k] == v for k, v in fixed.items()))
                                self.assertTrue(low <= numeral(text, witness, 4, bias) <= high)

    def test_bounds_match_exhaustive_permutations(self):
        for text in ("A", "ABBA", "CABDAB", "AAAAAB"):
            for bias in (0, 1):
                values = [numeral(text, dict(zip("ABCD", p)), 4, bias) for p in itertools.permutations(range(4))]
                self.assertEqual(numeric_bounds(text, "ABCD", bias), (min(values), max(values)))

    def test_full_interval_closes_without_enumerating_alphabets(self):
        result = count_interval(ALPHABET * 400, 0, 26 ** (26 * 400) - 1)
        self.assertEqual(result["alphabet_mappings"], 403291461126605635584000000)
        self.assertEqual((result["nodes"], result["closed_subtrees"]), (1, 1))

    def test_leading_zero_and_bijective_conventions_are_distinct(self):
        self.assertEqual(count_interval("ABBA", 6, 6, alphabet="AB")["alphabet_mappings"], 1)
        self.assertEqual(count_interval("ABBA", 6, 6, alphabet="AB", fixed={"A": 0})["alphabet_mappings"], 1)
        self.assertEqual(count_interval("ABBA", 6, 6, alphabet="AB", bias=1)["alphabet_mappings"], 0)

    def test_headers_include_real_compressor_prefixes(self):
        catalog = header_catalog()
        payload = b"synthetic object population control" * 10
        samples = {"gzip": [gzip.compress(payload, mtime=0)],
                   "zlib": [zlib.compress(payload, level=0), zlib.compress(payload, level=9)],
                   "bzip2": [bz2.compress(payload), bz2.compress(b"")],
                   "xz": [lzma.compress(payload)]}
        compressor = zlib.compressobj(zdict=payload[:40])
        samples["zlib"].append(compressor.compress(payload) + compressor.flush())
        for name, members in samples.items():
            for member in members:
                self.assertTrue(any(member.startswith(header) for header in catalog[name]), name)
        self.assertEqual({len(h) for h in catalog["bzip2"]}, {10})
        self.assertEqual(len(catalog["gzip"]), 32)

    def test_relabelled_compressor_controls_and_witnesses(self):
        alphabet = "BLOMACDEFGHIJKNPQRSTUVWXYZ"
        mapping = {c: i for i, c in enumerate(alphabet)}
        payload = b"controlled population, not a target answer" * 3
        members = {"gzip": gzip.compress(payload, mtime=0), "zlib": zlib.compress(payload),
                   "bzip2": bz2.compress(payload), "xz": lzma.compress(payload)}
        for name, member in members.items():
            header = next(h for h in header_catalog()[name] if member.startswith(h))
            low, high = prefix_interval(header, len(member))
            for bias in (0, 1):
                text = encode(int.from_bytes(member, "big"), alphabet, bias)
                self.assertEqual(numeral(text, mapping, 26, bias), int.from_bytes(member, "big"))
                exact = count_interval(text, low, high, bias=bias, fixed=mapping)
                self.assertEqual(exact["alphabet_mappings"], 1)
                unrestricted = count_interval(text, low, high, bias=bias)
                self.assertGreaterEqual(unrestricted["alphabet_mappings"], 1)
                value = numeral(text, unrestricted["witness_mapping"], 26, bias)
                self.assertTrue(value.to_bytes(len(member), "big").startswith(header))
                self.assertEqual(count_interval(text, low, high, bias=1 - bias, fixed=mapping)["alphabet_mappings"], 0)

    def test_scan_preserves_terminal_i_as_a_separate_model(self):
        report = scan("ABCDEFGHIJKLMNOPQRSTUVWXYZI")
        self.assertEqual([case["retained_letters"] for case in report["cases"]], [27, 27, 26, 26])
        for case in report["cases"]:
            for family in case["formats"]:
                self.assertLessEqual(family["canonical_mappings"], family["alphabet_mappings"])
                if family["witness"]:
                    self.assertIn("not a recovered packet", family["witness"]["scope"])

    def test_invalid_models_and_fixed_assignments_are_rejected(self):
        for text, alphabet, bias in (("", "AB", 0), ("AC", "AB", 0), ("AB", "AA", 0), ("AB", "AB", 2)):
            with self.assertRaises(ValueError):
                count_interval(text, 0, 10, alphabet=alphabet, bias=bias)
        for fixed in ({"A": 0, "B": 0}, {"C": 0}, {"A": 2}, {"A": -1}):
            with self.assertRaises(ValueError):
                count_interval("AB", 0, 10, alphabet="AB", fixed=fixed)
        with self.assertRaises(ValueError):
            count_interval("AB", 10, 0, alphabet="AB")
        for header, length in ((b"", 1), (b"\0x", 2), (b"ab", 1)):
            with self.assertRaises(ValueError):
                prefix_interval(header, length)

    def test_committed_result_replays_from_the_unmodified_source(self):
        root = Path(__file__).resolve().parents[1]
        raw = (root / "docs/data/nachtlorn-transcript.txt").read_bytes()
        stream = "".join(c for row in raw.decode("ascii").splitlines()[8:] for c in row if "A" <= c <= "Z")
        expected = json.loads((root / "docs/data/nachtlorn-reset-prefix-invariant-results.json").read_text())
        actual = scan(stream)
        actual["source_sha256"] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(actual, expected)
        self.assertEqual(actual["source_sha256"], "04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e")

    def test_six_glyph_certificate_independently_excludes_three_families(self):
        root = Path(__file__).resolve().parents[1]
        raw = (root / "docs/data/nachtlorn-transcript.txt").read_text(encoding="ascii")
        stream = "".join(c for row in raw.splitlines()[8:] for c in row if "A" <= c <= "Z")
        self.assertEqual(stream[:6], "VXGFAG")
        report = json.loads((root / "docs/data/nachtlorn-reset-prefix-invariant-results.json").read_text())
        for case in report["cases"]:
            width = case["retained_letters"]
            span, suffix_scale = 26 ** width, 26 ** (width - 6)
            shift = case["bias"] * (span - 1) // 25
            for family in ("gzip", "bzip2", "xz"):
                for size in case["feasible_minimal_byte_lengths"]:
                    for header_hex in report["headers"][family]:
                        header = bytes.fromhex(header_hex)
                        prefix = int.from_bytes(header, "big")
                        suffix_bits = 8 * (size - len(header))
                        low = max(0, (prefix << suffix_bits) - shift)
                        high = min(span - 1, ((prefix + 1) << suffix_bits) - 1 - shift)
                        if low > high:
                            continue
                        first, last = low // suffix_scale, high // suffix_scale
                        # Exhaust the tiny six-digit range, not the interval solver.
                        self.assertLess(last - first, 26)
                        for number in range(first, last + 1):
                            digits = [0] * 6
                            for i in range(5, -1, -1):
                                number, digits[i] = divmod(number, 26)
                            assigned, reverse = {}, {}
                            for glyph, digit in zip(stream[:6], digits):
                                if ((glyph in assigned and assigned[glyph] != digit)
                                        or (digit in reverse and reverse[digit] != glyph)):
                                    break
                                assigned[glyph], reverse[digit] = digit, glyph
                            else:
                                self.fail(f"unexpected compatible six-glyph prefix: {case}, {family}, {header_hex}")

    def test_source_overwrite_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.txt"
            path.write_text("do not change", encoding="ascii")
            with self.assertRaises(SystemExit):
                main([str(path), "--output", str(path)])
            self.assertEqual(path.read_text(), "do not change")


if __name__ == "__main__":
    unittest.main()
