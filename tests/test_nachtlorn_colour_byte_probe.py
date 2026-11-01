"""Synthetic direct-byte-key recovery, not another stacked encryption search."""
import contextlib
import gzip
import io
import tempfile
import unittest
from pathlib import Path

from scripts.nachtlorn_colour_byte_probe import inspect, key_material, main, scan, xor
from tests.test_nachtlorn_colour_probe import encode26


class ColourByteTests(unittest.TestCase):
    def test_registered_material_and_reversibility(self):
        keys = list(key_material())
        self.assertEqual(len(keys), 24)
        self.assertEqual(len({key for _, key in keys}), 24)
        self.assertNotIn("BLOOM", [spec["password"] for spec, _ in keys])
        data = bytes(range(256)) + b"\0" * 7
        for _, key in keys:
            self.assertEqual(xor(xor(data, key), key), data)
        with self.assertRaises(ValueError):
            xor(data, b"")

    def test_complete_gzip_recovery_and_final_marker(self):
        plain = gzip.compress(b'{"synthetic_control":"not puzzle evidence"}', mtime=0)
        source = encode26(xor(plain, b"GLPNM")) + "I"
        result = scan(source)
        self.assertEqual(result["representation_configurations"], 64)
        self.assertEqual(result["byte_xor_trials"], 24 * result["unique_buffers"])
        self.assertTrue(any(r["drop_final_i"] and r["password"] == "GLPNM"
                            and r["derivation"] == "raw-ascii"
                            and any(o["format"] == "gzip" for o in r["objects"])
                            and r["exact_byte_roundtrip"] for r in result["findings"]))
        self.assertEqual(inspect(plain[:-1])["objects"], [])

    def test_text_and_signature_flags_are_not_structured_acceptances(self):
        result = inspect(b"plain printable diagnostic, not JSON. " * 4)
        self.assertTrue(result["whole_printable_ascii_candidate"])
        self.assertEqual(result["objects"], [])
        result = inspect(b"\x93NUMPY" + b"invalid header" * 8)
        self.assertEqual(result["unvalidated_origin_signatures"], ["npy"])
        self.assertEqual(result["objects"], [])
        self.assertFalse(result["whole_printable_ascii_candidate"])
        with self.assertRaises(ValueError):
            scan("lowercase")

    def test_cli_and_source_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "source.txt", Path(directory) / "result.json"
            raw = b"blue\nlaughter\none\none\nmorning\n\nFind the outlier.\n\nABCDEFGHI\n"
            source.write_bytes(raw)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main([str(source), "--output", str(output)]), 0)
                with self.assertRaises(SystemExit):
                    main([str(source), "--output", str(source)])
            self.assertEqual(source.read_bytes(), raw)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
