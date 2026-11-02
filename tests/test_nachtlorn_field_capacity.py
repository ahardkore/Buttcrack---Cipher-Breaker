from __future__ import annotations

import copy
import hashlib
import itertools
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import nachtlorn_field_capacity as probe
from scripts import nachtlorn_fieldwise_iblt_probe as earlier


def scalar_fields(text, schema, layout, order, mapping, bias):
    """Independent ordinary field slicing and integer conversion."""
    cells = len(text) // sum(w for _n, w, _b in schema)
    cursor = 0
    words = []
    slots = [(cell, i) for cell in range(cells) for i in range(len(schema))]
    if layout == "field_major":
        slots = [(cell, i) for i in range(len(schema)) for cell in range(cells)]
    for _cell, i in slots:
        _name, width, bits = schema[i]
        word = text[cursor:cursor + width]
        cursor += width
        if order == "least_significant_first":
            word = word[::-1]
        value = 0
        for glyph in word:
            value = value * len(mapping) + mapping[glyph] + bias
        words.append((value, bits))
    return words


class CapacityTests(unittest.TestCase):
    def test_schema_matches_original_registered_fields(self):
        self.assertEqual(probe.FIELDS, earlier.FIELDS)

    def test_capacity_matches_independent_direct_inequalities(self):
        for base in range(2, 7):
            for width in range(1, 5):
                for bits in range(1, 15):
                    for bias in (0, 1):
                        allowed = []
                        for digit in range(base):
                            value = digit + bias
                            for _ in range(width - 1):
                                value = value * base + bias
                            if value < 2 ** bits:
                                allowed.append(digit)
                        self.assertEqual(allowed, list(range(probe.leading_capacity(base, width, bits, bias))))

    def test_real_field_capacities_and_relaxation_boundary(self):
        self.assertEqual([probe.leading_capacity(26, w, b, a) for a in (0, 1)
                          for w, b in ((7, 32), (14, 64))], [14, 8, 13, 7])
        self.assertEqual(probe.leading_capacity(4, 2, 2, 1), 0)
        self.assertEqual(probe.leading_capacity(4, 2, 32, 0), 4)

    def test_certificate_exclusions_hold_against_exhaustive_alphabets(self):
        rng = random.Random(4300)
        alphabet = "ABCD"
        schema = (("small", 2, 3), ("larger", 3, 5))
        for _ in range(20):
            text = "".join(rng.choice(alphabet) for _ in range(15))
            for layout, order, bias in itertools.product(probe.LAYOUTS, probe.ORDERS, (0, 1)):
                result = probe.analyze(text, layout, order, bias, fields=schema, alphabet=alphabet)
                if not result["exact_exclusion"]:
                    continue
                for digits in itertools.permutations(range(4)):
                    mapping = dict(zip(alphabet, digits))
                    values = scalar_fields(text, schema, layout, order, mapping, bias)
                    self.assertTrue(any(v >= 2 ** b for v, b in values))
                for field in result["fields"]:
                    if field["capacity_exceeded"]:
                        self.assertTrue(probe.verify_certificate(text, layout, order, bias, field["name"],
                                                                 field["certificate"], fields=schema, alphabet=alphabet))

    def test_positive_width_controls_under_both_biases_orders_and_layouts(self):
        alphabet = probe.ALPHABET[::-1]
        mapping = {g: d for d, g in enumerate(alphabet)}
        for layout, order, bias in itertools.product(probe.LAYOUTS, probe.ORDERS, (0, 1)):
            words = [[alphabet[0] * (w - 1) + alphabet[1] for _n, w, _b in probe.FIELDS] for _ in range(4)]
            slots = [(c, f) for c in range(4) for f in range(3)]
            if layout == "field_major":
                slots = [(c, f) for f in range(3) for c in range(4)]
            text = "".join(words[c][f] if order == "most_significant_first" else words[c][f][::-1]
                           for c, f in slots)
            self.assertTrue(all(v < 2 ** b for v, b in scalar_fields(text, probe.FIELDS, layout, order, mapping, bias)))
            result = probe.analyze(text, layout, order, bias)
            self.assertEqual(result["status"], "necessary_bound_only")
            self.assertFalse(result["exact_exclusion"])

    def test_certificate_replay_does_not_reuse_capacity_or_scanner(self):
        schema = (("x", 2, 2),)
        args = ("AABA", "cell_interleaved", "most_significant_first", 0)
        field = probe.analyze(*args, fields=schema, alphabet="ABCD")["fields"][0]
        with mock.patch.object(probe, "leading_capacity", side_effect=AssertionError), \
                mock.patch.object(probe, "analyze", side_effect=AssertionError):
            self.assertTrue(probe.verify_certificate(*args, "x", field["certificate"], fields=schema, alphabet="ABCD"))

    def test_tampered_certificates_are_rejected(self):
        schema = (("x", 2, 2),)
        args = ("AABA", "cell_interleaved", "most_significant_first", 0)
        original = probe.analyze(*args, fields=schema, alphabet="ABCD")["fields"][0]["certificate"]
        bad = [[], original + original[:1]]
        for key, value in (("glyph", "D"), ("glyph", None), ("body_letter_index", -1),
                           ("body_letter_index", 1), ("body_letter_index", True)):
            changed = copy.deepcopy(original)
            changed[0][key] = value
            bad.append(changed)
        changed = copy.deepcopy(original)
        changed[1] = changed[0]
        bad.append(changed)
        for certificate in bad:
            self.assertFalse(probe.verify_certificate(*args, "x", certificate, fields=schema, alphabet="ABCD"))

    def test_dimensions_are_not_silently_padded(self):
        result = probe.analyze("A" * 27, "field_major", "most_significant_first", 0)
        self.assertEqual(result["status"], "dimension_failure")
        self.assertEqual(result["remainder"], 27)
        self.assertTrue(result["exact_exclusion"])
        self.assertEqual(result["fields"], [])

    def test_invalid_parameters_raise_instead_of_excluding(self):
        for args in ((1, 7, 32, 0), (26, 0, 32, 0), (26, 7, 0, 0), (26, 7, 32, 2)):
            with self.assertRaises(ValueError):
                probe.leading_capacity(*args)
        with self.assertRaises(ValueError):
            probe.analyze("A", "unknown", "most_significant_first", 0)
        with self.assertRaises(ValueError):
            probe.scan("ABCD")

    def test_published_certificates_replay_against_unchanged_source(self):
        root = Path(__file__).resolve().parents[1]
        raw = (root / "docs/data/nachtlorn-transcript.txt").read_bytes()
        report = json.loads((root / "docs/data/nachtlorn-reset-field-capacity-results.json").read_text())
        self.assertEqual(report["source_sha256"], hashlib.sha256(raw).hexdigest())
        text = "".join(c for row in raw.decode("ascii").splitlines()[8:] for c in row if "A" <= c <= "Z")
        self.assertEqual(len(report["cases"]), 16)
        certificates = 0
        for case in report["cases"]:
            retained = text[:-1] if case["drop_final_i"] else text
            self.assertEqual(case["retained_letters"], len(retained))
            self.assertTrue(case["exact_exclusion"])
            if case["drop_final_i"]:
                self.assertEqual(case["status"], "dimension_failure")
                continue
            for field in case["fields"]:
                self.assertTrue(probe.verify_certificate(retained, case["layout"], case["digit_order"],
                                                         case["bias"], field["name"], field["certificate"]))
                certificates += 1
        self.assertEqual(certificates, 24)

    def test_cli_source_overwrite_is_guarded(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            source.write_text("unchanged")
            with self.assertRaises(SystemExit):
                probe.main([str(source), "--output", str(source)])
            self.assertEqual(source.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
