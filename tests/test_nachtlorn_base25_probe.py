from __future__ import annotations

import json
import unittest

from scripts.nachtlorn_base25_probe import ALPHABET, KEYS, checks, decode25, periodic25, variants


class NachtlornBase25ProbeTests(unittest.TestCase):
    def test_independent_integer_oracles_and_compressed_control(self):
        self.assertEqual(checks(), {"scalar_oracles": 30, "synthetic_inserted_I_gzip_control": True})

    def test_all_clue_key_phases_roundtrip(self):
        source = ALPHABET * 3
        for key in KEYS:
            for phase in range(len(key)):
                encoded = periodic25(source, key, phase, "plus")
                self.assertEqual(periodic25(encoded, key, phase, "minus"), source)
                encoded = periodic25(source, key, phase, "beaufort")
                self.assertEqual(periodic25(encoded, key, phase, "beaufort"), source)
        for key, kind in (("", "plus"), ("BLOOM", "unknown")):
            with self.assertRaises(ValueError):
                periodic25(source, key, 0, kind)

    def test_zero_and_invalid_digits(self):
        self.assertEqual(decode25("A", ALPHABET, 0), b"\x00")
        self.assertEqual(decode25("A", ALPHABET, 1), b"\x01")
        self.assertEqual(decode25("ZA", ALPHABET, 0), (24 * 25).to_bytes(2, "big"))
        for text, alphabet, bias in (("", ALPHABET, 0), ("I", ALPHABET, 0),
                                     ("a", ALPHABET, 0), ("A", "A" * 25, 0),
                                     ("A", ALPHABET, 2)):
            with self.assertRaises(ValueError):
                decode25(text, alphabet, bias)

    def test_paths_are_explicit_and_unique(self):
        outputs = list(variants("ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 3))
        self.assertEqual(len(outputs), 169)
        self.assertTrue(all(set(text) <= set(ALPHABET) and text for text, _ in outputs))
        specs = [json.dumps(spec, sort_keys=True) for _, spec in outputs]
        self.assertEqual(len(set(specs)), 169)
        self.assertEqual({spec["order"] for _, spec in outputs},
                         {"remove-I", "remove-I-then-mod25", "mod26-then-remove-I"})


if __name__ == "__main__":
    unittest.main()
