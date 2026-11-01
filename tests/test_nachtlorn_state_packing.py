from __future__ import annotations

import contextlib
import hashlib
import io
import itertools
import json
import random
import tempfile
import unittest
from pathlib import Path

from scripts.nachtlorn_clue_ledger import vigenere
from scripts.nachtlorn_state_packing import leading_capacity, main, permutation, permute, scan


def encoded(bits):
    width, count = (7, 1248) if bits == 32 else (14, 624)
    rng = random.Random(157)
    result = []
    for _ in range(count):
        value = rng.getrandbits(bits)
        digits = []
        for _ in range(width):
            digits.append(chr(65 + value % 26))
            value //= 26
        result.append("".join(reversed(digits)))
    return "".join(result)


def keyed(text):
    rng = random.Random(314159)
    alphabets = []
    for _ in range(5):
        alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        rng.shuffle(alphabet)
        alphabets.append(alphabet)
    return "".join(alphabets[i % 5][ord(c) - 65] for i, c in enumerate(text))


def layered_control(text):
    # Native shuffling of ragged strings, independent of the route implementation.
    text = keyed(text)
    chunks = [text[i:i + 5] for i in range(0, len(text), 5)]
    rng = random.Random(4300)
    for _ in range(146):
        rng.randrange(8)
    rng.shuffle(chunks)
    return vigenere("".join(chunks), "BLOOM", encrypt=True)


class NachtlornStatePackingTests(unittest.TestCase):
    def test_32_and_64_bit_capacity_constants(self):
        self.assertEqual(leading_capacity("A" * 8736, 7, 32)["permitted_leading_symbols"], 14)
        self.assertEqual(leading_capacity("A" * 8736, 14, 64)["permitted_leading_symbols"], 8)

    def test_both_packed_objects_survive_five_unknown_alphabets(self):
        for bits, width in ((32, 7), (64, 14)):
            result = leading_capacity(keyed(encoded(bits)), width, bits)
            self.assertEqual(result["minimum_leading_symbol_replacements"], 0)
            self.assertEqual(result["complete_blocks"], 8736 // width)

    def test_one_out_of_range_object_costs_one_leading_replacement(self):
        for bits, width in ((32, 7), (64, 14)):
            raw = encoded(bits)
            self.assertNotEqual(raw[0], "Z")
            changed = "Z" + raw[1:]
            result = leading_capacity(keyed(changed), width, bits)
            self.assertEqual(result["minimum_leading_symbol_replacements"], 1)

    def test_bound_matches_exhaustive_subset_selection(self):
        text = "".join(c + "Z" for c in "A" * 9 + "B" * 8 + "C" * 2 + "D")
        result = leading_capacity(text, 2, 5, phases=1)
        brute = min(sum(c not in subset for c in text[::2])
                    for subset in itertools.combinations("ABCD", 2))
        self.assertEqual(result["permitted_leading_symbols"], 2)
        self.assertEqual(result["minimum_leading_symbol_replacements"], brute)
        self.assertEqual(brute, 3)

    def test_necessary_condition_does_not_claim_sufficient_integer_validity(self):
        value = 0
        for c in "NZZZZZZ":
            value = 26 * value + ord(c) - 65
        self.assertGreater(value, 2 ** 32 - 1)
        self.assertEqual(leading_capacity("NZZZZZZ" * 100, 7, 32)
                         ["minimum_leading_symbol_replacements"], 0)

    def test_little_endian_and_nonzero_alignment(self):
        raw = encoded(64)
        little = "ABCD" + "".join(raw[i:i + 14][::-1] for i in range(0, len(raw), 14))
        self.assertEqual(leading_capacity(keyed(little), 14, 64, 4, "little")
                         ["minimum_leading_symbol_replacements"], 0)

    def test_ragged_shuffle_matches_native_and_inverts_both_ways(self):
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for unit in (1, 5, 7, 14, 60):
            for draws in (0, 145, 146):
                with self.subTest(unit=unit, draws=draws):
                    indices = permutation(len(text), unit, draws)
                    native = [text[i:i + unit] for i in range(0, len(text), unit)]
                    rng = random.Random(4300)
                    for _ in range(draws):
                        rng.randrange(8)
                    rng.shuffle(native)
                    shuffled = permute(text, unit, indices)
                    self.assertEqual(shuffled, "".join(native))
                    self.assertEqual(permute(shuffled, unit, indices, inverse=True), text)
                    self.assertEqual(permute(permute(text, unit, indices, inverse=True),
                                             unit, indices), text)

    def test_full_search_finds_layered_objects_and_one_outlier(self):
        raw = encoded(64)
        for changes in (0, 1):
            position = 300 * 14  # Interior object: no alignment may discard it as an edge.
            value = raw if not changes else raw[:position] + "Z" + raw[position + 1:]
            report = scan(layered_control(value))
            self.assertEqual(report["readings"], 128)
            self.assertEqual(report["capacity_cases"], 5376)
            self.assertGreater(report["single_exception_candidates"], 0)
            self.assertEqual(report["best_cases"][0]["minimum_leading_symbol_replacements"], changes)
            self.assertTrue(any(r["route"] == "inverse-shuffle" and r["unit"] == 5
                                and r["indent_draws"] == 146 and r["pre_key"] == "BLOOM"
                                for r in report["best_cases"]))

    def test_bad_parameters_rejected_and_rng_unchanged(self):
        state = random.getstate()
        permutation(26, 5, 146)
        self.assertEqual(random.getstate(), state)
        for width, bits, align in ((0, 32, 0), (7, 0, 0), (7, 32, 7)):
            with self.assertRaises(ValueError):
                leading_capacity("A" * 100, width, bits, align)
        with self.assertRaises(ValueError):
            permute("ABCDE", 2, [0, 0, 1])
        with self.assertRaises(ValueError):
            scan("not uppercase")

    def test_actual_all_5376_cases_replayed_with_independent_histograms_and_index_routes(self):
        path = Path(__file__).resolve().parents[1] / "docs/data/nachtlorn-transcript.txt"
        text = "".join(c for row in path.read_text().splitlines()[8:]
                       for c in row if "A" <= c <= "Z")
        digest = hashlib.sha256()
        case_count = 0
        best = len(text)
        for key in (None, "BLOOM", "BLPNM", "BLNPM"):
            decoded = text if key is None else "".join(
                chr(65 + (ord(c) - ord(key[i % len(key)])) % 26)
                for i, c in enumerate(text))
            variants = [(decoded, {"route": "identity", "pre_key": key}),
                        (decoded[::-1], {"route": "reverse", "pre_key": key})]
            for draws in (0, 145, 146):
                for unit in (1, 5, 7, 14, 60):
                    rng = random.Random(4300)
                    for _ in range(draws):
                        rng.randrange(8)
                    chunks = [list(range(i, min(i + unit, len(text))))
                              for i in range(0, len(text), unit)]
                    rng.shuffle(chunks)
                    indices = list(itertools.chain.from_iterable(chunks))
                    for inverse in (False, True):
                        if inverse:
                            letters = [""] * len(text)
                            for observed, original in enumerate(indices):
                                letters[original] = decoded[observed]
                            value = "".join(letters)
                        else:
                            value = "".join(decoded[i] for i in indices)
                        variants.append((value, {
                            "route": "inverse-shuffle" if inverse else "shuffle",
                            "unit": unit, "seed": 4300, "indent_draws": draws, "pre_key": key}))
            for value, spec in variants:
                for width, bits in ((7, 32), (14, 64)):
                    allowed = min(26, ((2 ** bits - 1) // (26 ** (width - 1))) + 1)
                    for alignment in range(width):
                        blocks = (len(text) - alignment) // width
                        for order in ("big", "little"):
                            hist = [[0] * 26 for _ in range(5)]
                            for block in range(blocks):
                                pos = alignment + block * width + (width - 1 if order == "little" else 0)
                                hist[pos % 5][ord(value[pos]) - 65] += 1
                            loss = sum(sum(row) - sum(sorted(row, reverse=True)[:allowed]) for row in hist)
                            record = {**spec, "width": width, "bits": bits, "alignment": alignment,
                                      "order": order, "complete_blocks": blocks,
                                      "permitted_leading_symbols": allowed,
                                      "distinct_symbols_by_phase": [sum(n > 0 for n in row) for row in hist],
                                      "minimum_leading_symbol_replacements": loss}
                            digest.update((json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode())
                            best = min(best, loss)
                            case_count += 1
        report = scan(text)
        self.assertEqual(case_count, 5376)
        self.assertEqual(digest.hexdigest(), report["capacity_case_sha256"])
        self.assertEqual(best, 304)
        self.assertEqual(report["single_exception_candidates"], 0)

    def test_cli_cannot_overwrite_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.txt"
            path.write_bytes(b"original")
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main([str(path), "--output", str(path)])
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(path.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
