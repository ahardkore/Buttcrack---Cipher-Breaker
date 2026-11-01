from __future__ import annotations

import contextlib
import io
import json
import math
import random
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.nachtlorn_numeric_probe import PARITY_MASKS, PERIODS, bit_profile, controls, main, numeric_candidates


class NachtlornNumericProbeTests(unittest.TestCase):
    def test_known_constant_bit_score(self):
        result = bit_profile(b"\xff" * 1024)
        self.assertEqual(result["ones"], 512)
        self.assertEqual(result["observations"], 512)
        self.assertAlmostEqual(result["score"], math.sqrt(512))

    def test_independent_scalar_replay_and_reversal_invariance(self):
        rng = random.Random(271828)
        data = bytes(rng.randrange(256) for _ in range(5133))
        maximum = 0
        for period in PERIODS:
            for phase in range(period):
                lane = data[phase::period]
                if len(lane) < 64:
                    continue
                for mask in PARITY_MASKS:
                    ones = sum(sum((c >> b) & 1 for b in range(8) if mask & (1 << b)) % 2 for c in lane)
                    maximum = max(maximum, abs(2 * ones - len(lane)) / math.sqrt(len(lane)))
        self.assertAlmostEqual(bit_profile(data)["score"], maximum)
        self.assertAlmostEqual(bit_profile(data[::-1])["score"], maximum)
        self.assertLess(maximum, 8)

    def test_four_structured_controls_survive_byte_masks(self):
        result = controls()
        self.assertEqual(len(result), 4)
        self.assertTrue(all(r["synthetic"] and r["profile"]["score"] >= 8 for r in result))

    def test_numeric_interpreter_recovers_the_control_outlier(self):
        rng = random.Random(314159)
        values = [rng.gauss(0, 1) for _ in range(640)]
        values[431] = 37.0
        data = b"NACHTLORN" + struct.pack("<I", 640) + struct.pack("<640d", *values)
        candidates = numeric_candidates(data)
        self.assertTrue(any(r["byte_mask"]["kind"] == "identity" and not r["reverse_bytes"]
                            and r["offset"] == 13 and r["float_format"] == "<d"
                            and r["outlier_index"] == 431 and r["outlier_value"] == "37.0"
                            for r in candidates))

    def test_balanced_marginals_do_not_hide_exponent_parity(self):
        rng = random.Random(271828)
        words = [(rng.getrandbits(1) << 63) | (rng.randrange(986, 1024) << 52)
                 | rng.getrandbits(52) for _ in range(320)]
        words += [word ^ ((1 << 64) - 1) for word in words]
        data = struct.pack("<640Q", *words)
        values = struct.unpack("<640d", data)
        self.assertTrue(all(1e-12 <= abs(v) <= 1e12 for v in values))
        result = bit_profile(data)
        self.assertEqual(result["parity_mask"], 0x60)
        self.assertIsNone(result["bit"])
        self.assertGreater(result["score"], 8)

    def test_terminal_I_extraction_is_recorded_and_readonly(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "original.txt", Path(directory) / "report.json"
            raw = ("synthetic header\n" * 8 + "ABCDEFGHI\n").encode("ascii")
            source.write_bytes(raw)
            result = {"path_configurations": 1, "binary_profiles": 1, "flagged": 0,
                      "best_profiles": [{"score": 0}]}
            with patch("scripts.nachtlorn_numeric_probe.scan", return_value=result) as probe, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(source), "--mode", "periodic-then-route",
                                       "--drop-final-i", "--output", str(output)]), 0)
            probe.assert_called_once_with("ABCDEFGH", "periodic-then-route")
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(json.loads(output.read_text())["source_extraction"],
                             {"original_body_letters": 9, "retained_body_letters": 8, "removed_terminal": "I"})

    def test_global_random_state_is_not_changed(self):
        state = random.getstate()
        controls()
        self.assertEqual(random.getstate(), state)


if __name__ == "__main__":
    unittest.main()
