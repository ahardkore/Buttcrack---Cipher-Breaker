from __future__ import annotations

import contextlib
import io
import struct
import tempfile
import unittest
from pathlib import Path

from scripts.nachtlorn_role_probe import book_facts, decode26, inspect_filter, inspect_scalable, main, scan_containers


def fixture():
    # Independently fixed constructor example: capacity100, P=.01 => k7,
    # bits/slice137, total959, payload120 bytes. One bit per slice is set.
    payload = bytearray(120)
    for position in [j * 137 for j in range(6)] + [958]:
        payload[position // 8] |= 1 << (position % 8)
    return struct.pack("<dQQQQ", .01, 7, 137, 100, 1) + bytes(payload)


def encode26(raw, bias, order):
    value = int.from_bytes(raw, order)
    result = ""
    while value:
        value, digit = divmod(value - bias, 26)
        result = chr(65 + digit) + result
    return result or "A"


class NachtlornRoleProbeTests(unittest.TestCase):
    def test_fixed_filter_schema_and_boundaries(self):
        data = fixture()
        result = inspect_filter(data)
        self.assertEqual((result["bits"], result["slices"], result["set_bits"], result["bytes"]), (959, 7, 7, 160))
        for bad in (data[:-1], data + b"x", b"prefix" + data, b"\0" * 160,
                    struct.pack("<dQQQQ", .01, 7, 138, 100, 1) + data[40:],
                    struct.pack("<dQQQQ", float("nan"), 7, 137, 100, 1) + data[40:],
                    struct.pack("<dQQQQ", .01, 7, 137, 100, 101) + data[40:],
                    data[:-1] + bytes([data[-1] | 128])):
            self.assertIsNone(inspect_filter(bad))

    def test_scalable_header_uses_actual_struct_size_and_all_children(self):
        child = fixture()
        header = struct.pack("<idQd", 4, .9, 100, .01)
        self.assertEqual(len(header), 28)
        data = header + struct.pack("<lQ", 1, len(child)) + child
        result = inspect_scalable(data)
        self.assertEqual(len(result["children"]), 1)
        self.assertEqual(result["children"][0]["sha256"], inspect_filter(child)["sha256"])
        empty = header + struct.pack("<l", 0)
        self.assertEqual(inspect_scalable(empty)["children"], [])
        for bad in (data[:-1], data + b"x", header + struct.pack("<l", -1),
                    header + struct.pack("<l", 65), header + struct.pack("<lQ", 1, len(child) + 1) + child):
            self.assertIsNone(inspect_scalable(bad))

    def test_independent_radix_oracles_and_both_orders(self):
        for bias in (0, 1):
            text = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 20)[:513]
            expected = 0
            for char in text:
                expected = expected * 26 + ord(char) - 65 + bias
            self.assertEqual(int.from_bytes(decode26(text, bias), "big"), expected)
            for order in ("big", "little"):
                encoded = encode26(fixture(), bias, order)
                recovered = decode26(encoded, bias)
                self.assertEqual(recovered if order == "big" else recovered[::-1], fixture())
        for stream, bias in (("", 0), ("abc", 0), ("AB!", 0), ("ABC", 2)):
            with self.assertRaises(ValueError):
                decode26(stream, bias)

    def test_registered_packet_recovery_and_marker_without_any_cipher(self):
        for bias in (0, 1):
            for order in ("big", "little"):
                stream = encode26(fixture(), bias, order) + "I"
                report = scan_containers(stream)
                self.assertEqual(report["representation_configurations"], 64)
                self.assertTrue(any(r["drop_final_i"] and r["bias"] == bias and r["byteorder"] == order
                                    and r["restored_zero_bytes"] == 0 and r["container"]["bytes"] == 160
                                    for r in report["candidates"]))

        # A conventional .5 error-rate header starts with six zero bytes.
        # Minimal whole-integer encoding loses them; the registered restoration
        # must recover the complete packet, not move to an arbitrary offset.
        zero_prefixed = struct.pack("<dQQQQ", .5, 1, 145, 100, 1) + bytes(18) + b"\x01"
        encoded = encode26(zero_prefixed, 0, "big") + "I"
        report = scan_containers(encoded)
        self.assertTrue(any(r["drop_final_i"] and r["bias"] == 0 and r["byteorder"] == "big"
                            and r["restored_zero_bytes"] == 6 for r in report["candidates"]))

    def test_book_reference_is_a_literal_exploratory_audit(self):
        raw = ("Title: Example\nAuthor: Someone\nRelease Date: [EBook #4300]\n"
               "[ 1 ]\nStately, plump Buck Mulligan stood by a bowl on the stairhead in the morning.\n"
               "—Introibo.\n[ 2 ]\nblue laughter beyond the selected episode\n").encode()
        result = book_facts(raw, ["not a quote"] * 5)
        self.assertEqual((result["title"], result["gutenberg_id"]), ("Example", 4300))
        queries = result["fixed_query_token_positions"]
        self.assertEqual(queries["blue"], [])
        self.assertEqual(queries["laughter"], [])
        self.assertTrue(queries["bowl"] and queries["stairs"] and queries["morning"])
        self.assertEqual(result["literal_poem_line_matches_in_episode"], [False] * 5)
        with self.assertRaises(ValueError):
            book_facts(b"not the expected reference", ["x"] * 5)

    def test_cli_guards_both_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            source, book = Path(directory) / "source.txt", Path(directory) / "book.txt"
            source.write_bytes(b"source unchanged")
            book.write_bytes(b"book unchanged")
            for output in (source, book):
                original = output.read_bytes()
                with contextlib.redirect_stderr(io.StringIO()) as errors, self.assertRaises(SystemExit) as failure:
                    main([str(source), "--book", str(book), "--output", str(output)])
                self.assertEqual(failure.exception.code, 2)
                self.assertIn("must not overwrite", errors.getvalue())
                self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
