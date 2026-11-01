from __future__ import annotations

import contextlib
import io
import json
import random
import tempfile
import unittest
from pathlib import Path

from scripts.nachtlorn_reset_audit import audit, format_body, main

ROOT = Path(__file__).resolve().parents[1]
PREAMBLE = ("blue at the bottom of the bowl.\n"
            "laughter, somewhere on the stairs.\n"
            "one given.\none taken.\nmorning. neither be right.\n\nFind the outlier.\n\n").encode("ascii")


class NachtlornResetAuditTests(unittest.TestCase):
    def test_original_has_a_complete_byte_exact_layout_reconstruction(self):
        raw = (ROOT / "docs/data/nachtlorn-transcript.txt").read_bytes()
        report = audit(raw)
        self.assertEqual(report["source_sha256"], "04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e")
        self.assertEqual(report["source_bytes"], 11129)
        self.assertEqual(report["poem"]["literal_initials"], "bloom")
        self.assertEqual(report["body"]["row_letter_counts"], {"36": 1, "60": 145})
        self.assertEqual(report["body"]["group_width_counts"], {"1": 1, "5": 1747})
        self.assertTrue(report["forward_layout"]["exact_body_reconstruction"])
        self.assertTrue(report["forward_layout"]["exact_file_with_literal_preamble"])
        self.assertEqual(report["forward_layout"]["letters_added_or_removed"], 0)
        self.assertIsNone(report["forward_layout"]["first_body_mismatch_byte"])

    def test_formatter_matches_an_independent_scalar_oracle(self):
        stream = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 7)[:137]
        rng = random.Random(4300)
        expected = bytearray()
        for row_start in range(0, len(stream), 60):
            expected.extend(b" " * rng.randrange(8))
            for local in range(min(60, len(stream) - row_start)):
                if local and local % 5 == 0:
                    expected.extend(b" ")
                expected.extend(stream[row_start + local].encode("ascii"))
            expected.extend(b"\n")
        self.assertEqual(format_body(stream), bytes(expected))

    def test_incomplete_final_group_is_not_added_as_padding(self):
        for stream in ("ABCDEI", "ABCDEZ", "ABCDEFGHIJ", "ABCDE"):
            output = format_body(stream)
            recovered = "".join(chr(c) for c in output if 65 <= c <= 90)
            self.assertEqual(recovered, stream)
        self.assertEqual(format_body(""), b"")
        self.assertEqual(audit(PREAMBLE + format_body("ABCDEZ"))["body"]["last_printed_group"], "Z")

    def test_body_letter_mutation_does_not_invalidate_a_layout_only_model(self):
        a = audit(PREAMBLE + format_body("ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 4))
        b = audit(PREAMBLE + format_body("ZBCDEFGHIJKLMNOPQRSTUVWXYZ" * 4))
        self.assertNotEqual(a["body"]["letter_sha256"], b["body"]["letter_sha256"])
        self.assertTrue(a["forward_layout"]["exact_body_reconstruction"])
        self.assertTrue(b["forward_layout"]["exact_body_reconstruction"])

    def test_space_and_line_ending_changes_are_detected_not_repaired(self):
        original = PREAMBLE + format_body("ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 4)
        body = original[len(PREAMBLE):]
        changed = body.replace(b"ABCDE FGHIJ", b"ABCDE  FGHIJ", 1)
        self.assertNotEqual(changed, body)
        for altered in (changed, body.replace(b"\n", b"\r\n"), body[:-1]):
            report = audit(PREAMBLE + altered)
            self.assertFalse(report["forward_layout"]["exact_body_reconstruction"])
            self.assertIsNotNone(report["forward_layout"]["first_body_mismatch_byte"])
            self.assertEqual(report["body"]["letters"], 104)

    def test_no_candidate_or_algorithm_assignment_is_emitted(self):
        report = audit((ROOT / "docs/data/nachtlorn-transcript.txt").read_bytes())
        self.assertEqual(set(report), {"status", "source_sha256", "source_bytes", "poem", "instruction", "body",
                                       "forward_layout", "interpretation_limits"})
        self.assertNotIn("key", report["poem"])
        self.assertNotIn("outlier", report["body"])
        self.assertNotIn("fragments", report)
        self.assertNotIn("candidates", report)

    def test_global_random_state_is_unchanged(self):
        state = random.getstate()
        audit(PREAMBLE + format_body("ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 4))
        self.assertEqual(random.getstate(), state)

    def test_cli_preserves_source_and_guards_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "source.txt", Path(directory) / "facts.json"
            raw = PREAMBLE + format_body("ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 4)
            source.write_bytes(raw)
            self.assertEqual(main([str(source), "--output", str(output)]), 0)
            self.assertEqual(source.read_bytes(), raw)
            self.assertTrue(json.loads(output.read_text())["forward_layout"]["exact_body_reconstruction"])
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                with self.assertRaises(SystemExit) as failure:
                    main([str(source), "--output", str(source)])
            self.assertEqual(failure.exception.code, 2)
            self.assertIn("must not overwrite", errors.getvalue())
            self.assertEqual(source.read_bytes(), raw)

    def test_malformed_sources_and_dimensions_are_rejected(self):
        for raw in (b"too short", PREAMBLE + b"ABCD\tEFGH\n", PREAMBLE + b"lowercase\n"):
            with self.assertRaises(ValueError):
                audit(raw)
        with self.assertRaises(ValueError):
            format_body("ABC!DEF")
        with self.assertRaises(ValueError):
            format_body("ABCDEF", group_letters=0)


if __name__ == "__main__":
    unittest.main()
