"""Independent reference controls and malformed-table rejections, not puzzle clues."""
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.nachtlorn_fieldwise_iblt_probe import (
    LAYOUTS,
    build_table,
    checksum,
    encode_number,
    encode_table,
    inspect_fields,
    letter_paths,
    main,
    murmur32,
    positions,
    scan,
    validate_table,
)
from scripts.nachtlorn_running_book_probe import transform

ROOT = Path(__file__).resolve().parents[1]


class FieldwiseIBLTTests(unittest.TestCase):
    def test_independent_cpp_reference_vectors_and_table(self):
        oracle = json.loads((ROOT / "docs/data/nachtlorn-fieldwise-iblt-oracle.json").read_text())
        self.assertEqual(len(oracle["hash_vectors"]), 20)
        for v in oracle["hash_vectors"]:
            self.assertEqual(murmur32(v["key_uint64"].to_bytes(8, "little"), v["seed"]), v["murmur32"])
        table = build_table(oracle["signed_items"], oracle["cell_count"])
        for row, expected in zip(table, oracle["cells"]):
            self.assertEqual(row[:2], [expected["count"], expected["key_sum"]])
            self.assertEqual(checksum(row[1]) == row[2], expected["checksum_matches_key_sum"])
        validated = validate_table(table)
        self.assertTrue(validated["valid"])
        self.assertEqual([(r["key_uint64"], r["sign"]) for r in validated["items"]],
                         [tuple(row) for row in oracle["signed_items"]])
        self.assertEqual(hashlib.sha256((ROOT / oracle["oracle_source"]).read_bytes()).hexdigest(),
                         oracle["oracle_source_sha256"])
        self.assertEqual(murmur32(b""), 0)
        self.assertEqual(murmur32(b"foo"), 0xf6a5c420)
        self.assertEqual(murmur32(b"hello"), 0x248bfa47)

    def test_signed_recovery_and_wire_reconstruction_both_layouts(self):
        table = build_table([(7, 1), (31, -1), ((1 << 64) - 1, 1)], 64)
        for layout in LAYOUTS:
            text = encode_table(table, layout)
            result = inspect_fields(text, layout)
            self.assertEqual(len(text), 64 * 28)
            self.assertEqual(result["status"], "validated_table")
            self.assertTrue(result["exact_wire_reconstruction"])
            self.assertFalse(result["table_validation"]["empty"])
            self.assertEqual(result["table_validation"]["items"],
                             [{"key_uint64": 7, "sign": 1}, {"key_uint64": 31, "sign": -1},
                              {"key_uint64": (1 << 64) - 1, "sign": 1}])

    def test_corruption_wrong_bucket_and_nonfirst_partition_residual(self):
        table = build_table([(7, 1), (31, -1)], 64)
        table[0][2] ^= 1
        self.assertFalse(validate_table(table)["valid"])
        key = 42
        wrong = next(i for i in range(16) if i not in positions(key, 16))
        table = [[0, 0, 0] for _ in range(16)]
        table[wrong] = [1, key, checksum(key)]
        self.assertEqual(validate_table(table)["reason"], "pure_cell_wrong_bucket")
        table = [[0, 0, 0] for _ in range(16)]
        table[-1][2] = 1
        self.assertEqual(validate_table(table)["reason"], "nonempty_residual")

    def test_overflow_is_not_truncated_and_count_bound_is_separate(self):
        empty = encode_table([[0, 0, 0] for _ in range(16)], "interleaved")
        invalid = encode_number(1 << 32, 7) + empty[7:]
        result = inspect_fields(invalid, "interleaved")
        self.assertEqual(result["unsigned_overflow_fields"]["count"], 1)
        self.assertEqual(result["status"], "field_constraints_failed")
        invalid = empty[:7] + encode_number(1 << 64, 14) + empty[21:]
        self.assertEqual(inspect_fields(invalid, "interleaved")["unsigned_overflow_fields"]["key"], 1)
        invalid = encode_number(1_000_001, 7) + empty[7:]
        self.assertEqual(inspect_fields(invalid, "interleaved")["out_of_bound_signed_counts"], 1)
        with self.assertRaises(ValueError):
            encode_table([[1 << 32, 0, 0]], "interleaved")
        with self.assertRaises(ValueError):
            encode_number(26 ** 7, 7)

    def test_empty_table_recognition_is_not_outlier_selection(self):
        result = inspect_fields("A" * (16 * 28), "interleaved")
        self.assertEqual(result["status"], "validated_table")
        self.assertTrue(result["table_validation"]["empty"])
        self.assertEqual(result["table_validation"]["items"], [])
        self.assertNotIn("outlier", result)

    def test_repeating_key_plus_marker_recovers_synthetic_table(self):
        table = build_table([(7, 1), (31, -1)], 64)
        plain = encode_table(table, "field-major")
        key = ("BLOOM" * ((len(plain) + 4) // 5))[:len(plain)]
        source = transform(plain, key, "minus", inverse=True) + "I"
        result = scan(source)
        self.assertEqual(result["configurations"], 40)
        self.assertTrue(any(r.get("key") == "BLOOM" and r["operation"] == "minus"
                            and r["drop_final_i"] and r["layout"] == "field-major"
                            and r["exact_wire_reconstruction"] for r in result["validated_tables"]))
        self.assertTrue(all(p["exact_letter_roundtrip"] for p, _ in letter_paths(source)))

    def test_dimensions_and_invalid_inputs(self):
        for text in ("A" * 27, "A" * 28, "A" * 113):
            self.assertEqual(inspect_fields(text, "interleaved")["status"], "incompatible_dimensions")
        for text, layout in (("abc", "interleaved"), ("ABC", "other")):
            with self.assertRaises(ValueError):
                inspect_fields(text, layout)
        self.assertFalse(validate_table([[0, 0, 0]])["valid"])
        with self.assertRaises(ValueError):
            positions(0, 3)
        with self.assertRaises(ValueError):
            build_table([(0, 0)], 16)

    def test_cli_and_source_overwrite_guard(self):
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
