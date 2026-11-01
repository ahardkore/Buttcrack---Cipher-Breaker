"""Short keyed payloads must not be discarded by a prose-only scoring gate."""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from buttcrack.lang import LanguageModel
from scripts.stego_channel_scan import (
    Scanner, best_keyed_window, keyed_group_matches, main, scan_keyed_groups,
    scan_keyed_windows, scan_whitespace,
)


def encrypt_groups(groups: list[list[str]], key: str) -> list[str]:
    phase = 0
    result = []
    for row in groups:
        encrypted = []
        for word in row:
            encrypted.append("".join(
                chr((ord(c) - 65 + ord(key[(phase + i) % len(key)]) - 65) % 26 + 65)
                for i, c in enumerate(word)
            ))
            phase += len(word)
        result.append("   " + " ".join(encrypted))
    return result


class KeyedGroupTests(unittest.TestCase):
    def test_known_vigenere_vector_and_one_based_coordinates(self):
        # ATTACKATDAWN with key LEMON is LXFOPVEFRNHR. Break the
        # ciphertext into uneven groups to catch accidental key resets.
        result = keyed_group_matches(
            ["  LXFOP VEF", "RNHR"], "lemon", {"attac": 1, "kat": 1, "dawn": 1}
        )
        self.assertEqual(result, [
            (1, 1, 1, "LXFOP", "ATTAC"),
            (1, 2, 2, "VEF", "KAT"),
            (2, 1, 3, "RNHR", "DAWN"),
        ])

    def test_isolated_word_among_nonwords(self):
        body = encrypt_groups([["QZXJK", "HELLO"], ["ZXQKJ", "I"]], "PLANT")
        result = keyed_group_matches(body, "PLANT", {"hello": 20, "i": 100})
        self.assertEqual(result, [(1, 2, 2, body[0].split()[1], "HELLO")])

    def test_no_dictionary_match(self):
        self.assertEqual(keyed_group_matches(["AAAAA"], "A", {"hello": 1}), [])

    def test_invalid_key(self):
        with self.assertRaisesRegex(ValueError, "ASCII letter"):
            keyed_group_matches(["AAAAA"], "123!?", {"hello": 1})

    def test_cli_accepts_a_single_encrypted_word(self):
        body = encrypt_groups([["HELLO"]], "PLANT")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.txt"
            path.write_text(body[0] + "\n", encoding="ascii")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                result = main([str(path), "--group-key", "PLANT"])
        self.assertEqual(result, 0)
        self.assertIn("-> HELLO", output.getvalue())

    def test_cli_accepts_exactly_one_prose_window(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.txt"
            path.write_text(" ".join(["QZXKJ"] * 12) + "\n", encoding="ascii")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                result = main([str(path)])
        self.assertIn(result, (0, 1))
        self.assertIn("best 60-letter window", output.getvalue())
        self.assertNotIn("file carries no", output.getvalue())

    def test_short_candidate_bypasses_prose_gate(self):
        body = encrypt_groups([["HELLO"]], "PLANT")
        # No fitness() exists: dictionary matching must not go through the
        # prose scorer, which rejects payloads shorter than 24 letters.
        model = SimpleNamespace(words={"hello": 1})
        scanner = Scanner(model, threshold=-5.5)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            scan_keyed_groups(scanner, body, "PLANT")
        self.assertEqual(len(scanner.hits), 1)
        self.assertEqual(scanner.hits[0][1], "HELLO")
        self.assertIn("DICTIONARY CANDIDATE", output.getvalue())
        self.assertIn("coincidences", output.getvalue())


class KeyedWindowTests(unittest.TestCase):
    payload = "YOURCONTRACTCOMESDUE"

    def target_model(self):
        return SimpleNamespace(fitness=lambda s: 2.0 if s == self.payload else -20.0)

    def test_known_vector_with_exactly_one_window(self):
        model = SimpleNamespace(fitness=lambda s: 1.0 if s == "ATTACKATDAWN" else -20.0)
        self.assertEqual(
            best_keyed_window([" LXFOP VEF", "RNHR"], "lemon", model, 12),
            (1.0, 0, "ATTACKATDAWN"),
        )

    def test_unaligned_final_window_crosses_groups_and_rows(self):
        plain = "QZX" + self.payload
        body = encrypt_groups([[plain[:7], plain[7:13]], [plain[13:]]], "LEMON")
        self.assertEqual(
            best_keyed_window(body, "LEMON", self.target_model(), 20),
            (2.0, 3, self.payload),
        )

    def test_opt_in_short_window_bypasses_only_the_prose_gate(self):
        body = encrypt_groups([[self.payload]], "PLANT")
        scanner = Scanner(self.target_model(), threshold=1.0)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            scan_keyed_windows(scanner, body, "PLANT")
        self.assertEqual([s for _, s in scanner.hits], [self.payload])
        self.assertIn("SHORT-WINDOW CANDIDATE", output.getvalue())
        self.assertIn("not corrected", output.getvalue())

    def test_short_body_skips_without_calling_fitness(self):
        model = SimpleNamespace()
        self.assertIsNone(best_keyed_window(["AAAA"], "A", model, 20))
        scanner = Scanner(model, threshold=-5.5)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            scan_keyed_windows(scanner, ["AAAA"], "A", 20)
        self.assertEqual(scanner.hits, [])
        self.assertIn("shorter than", output.getvalue())

    def test_invalid_helper_arguments(self):
        with self.assertRaisesRegex(ValueError, "ASCII letter"):
            best_keyed_window(["AAAAA"], "!?123", self.target_model())
        with self.assertRaisesRegex(ValueError, "at least 4"):
            best_keyed_window(["AAAAA"], "A", self.target_model(), 3)

    def test_cli_recovers_a_twenty_letter_span(self):
        body = encrypt_groups([
            [self.payload[:5], self.payload[5:10]],
            [self.payload[10:15], self.payload[15:]],
        ], "BLPNM")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.txt"
            path.write_text("\n".join(body) + "\n", encoding="ascii")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                status = main([str(path), "--key-window", "BLPNM"])
        self.assertEqual(status, 0)
        self.assertIn("SHORT-WINDOW CANDIDATE", output.getvalue())
        self.assertIn(self.payload, output.getvalue())
        self.assertIn("letter offset 0", output.getvalue())

    def test_cli_rejects_invalid_options_before_reading_file(self):
        for options in (["--key-window-size", "3"], ["--key-window", "123!?"]):
            with self.subTest(options=options):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as result:
                        main(["nonexistent-input.txt", *options])
                self.assertEqual(result.exception.code, 2)


class ShortByteChannelTests(unittest.TestCase):
    payload = b"SPACES ARE THE KEY"

    def make_scanner(self):
        return Scanner(LanguageModel.get("english"), threshold=-5.5)

    def test_eighteen_byte_text_is_not_discarded(self):
        self.assertEqual(len(self.payload), 18)
        scanner = self.make_scanner()
        with contextlib.redirect_stdout(io.StringIO()):
            scanner.offer_bytes("short binary channel", self.payload)
        self.assertEqual(scanner.hits, [("short binary channel", self.payload.decode())])

    def test_regular_prose_gate_remains_conservative(self):
        scanner = self.make_scanner()
        scanner.offer("prose", self.payload.decode())
        self.assertEqual(scanner.hits, [])

    def test_short_binary_noise_and_punctuation_are_rejected(self):
        scanner = self.make_scanner()
        scanner.offer_bytes("control character", self.payload[:-1] + b"\x00")
        scanner.offer_bytes("punctuation", b"!!!!!!!!STAND!!!!!")
        self.assertEqual(scanner.hits, [])

    def test_one_bit_per_line_can_recover_an_eighteen_byte_message(self):
        bits = [int(bit) for byte in self.payload for bit in f"{byte:08b}"] + [0, 0]
        body = [" " * bit + "AAAAA" for bit in bits]
        self.assertEqual(len(body), 146)
        scanner = self.make_scanner()
        with contextlib.redirect_stdout(io.StringIO()):
            scan_whitespace(scanner, body)
        self.assertIn(self.payload.decode(), [text for _, text in scanner.hits])


if __name__ == "__main__":
    unittest.main()
