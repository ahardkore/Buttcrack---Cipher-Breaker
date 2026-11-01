"""Structural controls: count stripes are necessary clues, not decoded objects."""
import contextlib
import io
import random
import struct
import tempfile
import unittest
from pathlib import Path

from scripts.nachtlorn_signed_cells_probe import STRIDES, inspect_stripes, letter_paths, main, scan


class SignedCellTests(unittest.TestCase):
    def test_signed_counts_at_every_registered_stride_and_unaligned_header(self):
        for stride in STRIDES:
            for order, prefix in (("little", "<"), ("big", ">")):
                data = b"\x80" * 7 + b"".join(struct.pack(prefix + "i", 5 if i % 2 else -7)
                                                + b"\x80" * (stride - 4) for i in range(40))
                result = inspect_stripes(data)
                self.assertTrue(any(s["stride_bytes"] == stride and s["count_byteorder"] == order
                                    and s["longest_run"] == 40 and s["first_count_offset"] == 7
                                    for s in result["flags"]), (stride, order))

    def test_threshold_and_count_bound(self):
        data = b"".join(struct.pack("<i", 8) + b"\x80" * 12 for _ in range(31))
        self.assertEqual(inspect_stripes(data)["flags"], [])
        matching = [s for s in inspect_stripes(data, min_run=31)["flags"]
                    if s["stride_bytes"] == 16 and s["count_byteorder"] == "little"]
        self.assertTrue(matching)
        self.assertEqual(inspect_stripes(data, max_count=7)["flags"], [])

    def test_noise_control_and_degenerate_flag_is_not_object_acceptance(self):
        noise = random.Random(2026).randbytes(4096)
        self.assertEqual(inspect_stripes(noise)["flags"], [])
        result = inspect_stripes(b"\xff" * 1024)
        self.assertTrue(result["flags"])
        self.assertNotIn("accepted", result)
        self.assertNotIn("items", result)
        self.assertNotIn("outlier", result)

    def test_paths_and_input_validation(self):
        stream = "ABCDEFGHIJKLMNOPQRSTUVWXYZI"
        paths = list(letter_paths(stream))
        self.assertEqual(len(paths), 14)
        self.assertTrue(all(p["exact_letter_roundtrip"] for p, _ in paths))
        self.assertEqual(sum(p["operation"] == "identity" for p, _ in paths), 2)
        for value in ("", "I", "abc", "AB CD"):
            with self.assertRaises(ValueError):
                list(letter_paths(value))
        for settings in ({"max_count": -1}, {"min_run": 0}):
            with self.assertRaises(ValueError):
                inspect_stripes(b"", **settings)

    def test_bounded_small_scan_and_no_false_object_claim(self):
        report = scan("ABCDEFGHI")
        self.assertEqual(len(report["letter_paths"]), 14)
        self.assertEqual(report["representation_configurations"], 448)
        self.assertEqual(report["flagged_buffers"], [])
        self.assertNotIn("accepted_objects", report)
        self.assertIn("Preflight only", report["status"])

    def test_cli_and_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "source.txt", Path(directory) / "result.json"
            original = b"blue\nlaughter\none\none\nmorning\n\nFind the outlier.\n\nABCDEFGHI\n"
            source.write_bytes(original)
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(source), "--output", str(output)]), 0)
                with self.assertRaises(SystemExit):
                    main([str(source), "--output", str(source)])
            self.assertEqual(source.read_bytes(), original)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
