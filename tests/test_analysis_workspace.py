"""Diagnostic calculations, honest limits and local API behavior."""

from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

from buttcrack import server
from buttcrack.analysis_workspace import MAX_LETTERS, MAX_RAW_CHARS, analyze
from buttcrack.ciphers import get

PLAIN = (
    "The archive contains original manuscripts and private letters. Each document reveals the history of the city, "
    "its people and the everyday struggles of their lives. Scholars compare independent evidence before deciding "
    "what a surviving message might mean. A convincing story alone cannot establish the identity of a writer or the "
    "meaning of an uncertain phrase. We must study the language carefully and preserve every alternative reading. "
) * 8


class MeasurementTests(unittest.TestCase):
    def test_counts_ic_and_entropy_have_declared_units(self):
        data = analyze({"ciphertext": "AaBb!"})["ciphertext"]
        self.assertEqual(data["letters"], 4)
        self.assertEqual(data["frequencies"][0]["count"], 2)
        self.assertEqual(data["frequencies"][1]["proportion"], .5)
        self.assertAlmostEqual(data["ic"], 1 / 3)
        self.assertAlmostEqual(data["letter_entropy"], 1.0)
        self.assertAlmostEqual(data["symbol_entropy"], 2.32192809489)

    def test_ascii_only_does_not_expand_unicode_or_shift_positions(self):
        data = analyze({"ciphertext": "abcßЖé 12!"})
        self.assertEqual(data["ciphertext"]["letters"], 3)
        self.assertEqual([row["ciphertext"] for row in data["alignment"]["rows"]], list("ABC"))
        self.assertIn("ASCII", data["normalization"])

    def test_empty_and_one_letter_ic_are_not_measurable(self):
        empty = analyze({})
        self.assertIsNone(empty["ciphertext"]["ic"])
        self.assertIsNone(empty["plaintext"]["letter_entropy"])
        self.assertEqual(empty["ciphertext"]["key_length_estimates"], [])
        one = analyze({"ciphertext": "A"})
        self.assertIsNone(one["ciphertext"]["ic"])
        self.assertEqual(one["ciphertext"]["letter_entropy"], 0)

    def test_transposition_preserves_frequency_ic_and_letter_entropy(self):
        plain = "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOG"
        data = analyze({"ciphertext": plain[::-1], "plaintext": plain})
        for field in ("ic", "letter_entropy", "frequencies"):
            self.assertEqual(data["ciphertext"][field], data["plaintext"][field])
        self.assertIn("transposition preserves", data["caveat"])

    def test_sampling_and_external_prefix_limits_are_visible(self):
        data = analyze({"ciphertext": "A" * (MAX_RAW_CHARS + 1), "plaintext": "B" * 20, "plaintext_truncated": True})
        self.assertEqual(data["ciphertext"]["letters"], MAX_LETTERS)
        self.assertTrue(data["ciphertext"]["raw_prefix_truncated"])
        self.assertTrue(data["ciphertext"]["letter_sample_truncated"])
        self.assertTrue(data["plaintext"]["raw_prefix_truncated"])
        self.assertTrue(any("bounded prefix" in warning for warning in data["plaintext"]["warnings"]))


class PeriodTests(unittest.TestCase):
    def test_repeated_pattern_positions_and_adjacent_distances(self):
        data = analyze({"ciphertext": "ABCXABCYABC"})["ciphertext"]
        repeat = next(row for row in data["repeated_patterns"] if row["pattern"] == "ABC")
        self.assertEqual(repeat["positions"], [0, 4, 8])
        self.assertEqual(repeat["adjacent_distances"], [4, 4])
        self.assertIn(2, repeat["supporting_periods"])
        self.assertIn(4, repeat["supporting_periods"])

    def test_zero_column_ic_is_not_discarded_as_missing(self):
        data = analyze({"ciphertext": "ABCD"})["ciphertext"]
        period = next(row for row in data["periods"] if row["period"] == 2)
        self.assertEqual(period["weighted_column_ic"], 0)
        self.assertEqual(period["mean_column_ic"], 0)
        self.assertTrue(period["insufficient_sample"])
        self.assertEqual(period["lag_matches"], 0)
        self.assertEqual(period["lag_comparisons"], 2)

    def test_real_vigenere_key_length_is_among_hypotheses(self):
        cipher = get("vigenere").encrypt(PLAIN, "LEMON")
        data = analyze({"ciphertext": cipher, "plaintext": PLAIN})
        lengths = [row["period"] for row in data["ciphertext"]["key_length_estimates"]]
        self.assertIn(5, lengths)
        period = next(row for row in data["ciphertext"]["periods"] if row["period"] == 5)
        self.assertGreater(period["weighted_column_ic"], data["ciphertext"]["ic"])
        self.assertGreater(period["kasiski_votes"], 0)
        self.assertIn("not a probability", data["method"])

    def test_repetitive_input_is_bounded_and_warned(self):
        data = analyze({"ciphertext": "ABC" * 3000, "max_period": 40})["ciphertext"]
        self.assertLessEqual(len(data["repeated_patterns"]), 30)
        self.assertTrue(all(len(row["positions"]) <= 20 for row in data["repeated_patterns"]))
        self.assertTrue(any(row["positions_truncated"] for row in data["repeated_patterns"]))
        self.assertTrue(any("Low letter diversity" in warning for warning in data["warnings"]))
        self.assertEqual(len(data["periods"]), 40)

    def test_reference_language_is_explicit_and_not_a_cipher_identification(self):
        data = analyze({"ciphertext": "ABCABCABC", "language": "french"})
        self.assertEqual(data["reference"]["language"], "french")
        self.assertAlmostEqual(data["reference"]["uniform_random_ic"], 1 / 26)
        self.assertIn("do not prove a cipher", data["caveat"])


class AlignmentTests(unittest.TestCase):
    def test_known_vigenere_alignment_and_wrong_phase(self):
        plain = "ATTACKATDAWN"
        options = {"ciphertext": "LXFOPVEFRNHR", "plaintext": plain, "cipher": "vigenere", "key": "LEMON"}
        result = analyze(options)["alignment"]
        self.assertEqual(result["positions_checked"], len(plain))
        self.assertEqual(result["mismatches"], 0)
        self.assertEqual("".join(row["key"] for row in result["rows"]), "LEMONLEMONLE")
        self.assertIn("not independent verification", result["detail"])
        shifted = analyze({**options, "key_offset": 1})["alignment"]
        self.assertGreater(shifted["mismatches"], 0)

    def test_display_offset_does_not_reset_key_phase(self):
        result = analyze({"ciphertext": "LXFOPVEFRNHR", "plaintext": "ATTACKATDAWN", "cipher": "vigenere", "key": "LEMON", "alignment_start": 6})["alignment"]
        self.assertEqual(result["rows"][0]["position"], 6)
        self.assertEqual(result["rows"][0]["key"], "E")
        self.assertEqual(result["mismatches"], 0)

    def test_supported_conventions_match_real_encryptors(self):
        for cipher, key in (("beaufort", "LEMON"), ("variant_beaufort", "LEMON"), ("gronsfeld", "31415"), ("caesar", "7")):
            with self.subTest(cipher=cipher):
                actual_key = int(key) if cipher == "caesar" else key
                ciphertext = get(cipher).encrypt("ATTACKATDAWN", actual_key)
                result = analyze({"ciphertext": ciphertext, "plaintext": "ATTACKATDAWN", "cipher": cipher, "key": key})["alignment"]
                self.assertEqual(result["mismatches"], 0)
                self.assertEqual(result["positions_checked"], 12)

    def test_unsupported_and_layered_models_do_not_invent_alignment(self):
        for cipher, steps in (("columnar", []), ("autokey", []), ("quagmire3", []), ("vigenere", ["base64"])):
            with self.subTest(cipher=cipher):
                options = {"ciphertext": "LXFOPVEFRNHR", "plaintext": "ATTACKATDAWN", "cipher": cipher, "key": "LEMON", "steps": steps}
                result = analyze(options)["alignment"]
                self.assertEqual(result["model"], "none")
                self.assertEqual(result["positions_checked"], 0)
                forced = analyze({**options, "alignment_model": "vigenere"})["alignment"]
                self.assertTrue(forced["explicit_hypothesis"])
                self.assertIn("manual model", forced["detail"])

    def test_unequal_lengths_and_empty_display_offset(self):
        result = analyze({"ciphertext": "AAAA", "plaintext": "BB"})["alignment"]
        self.assertFalse(result["lengths_match"])
        self.assertEqual(result["rows"][-1]["plaintext"], "")
        self.assertEqual(analyze({"ciphertext": "A", "alignment_start": 8})["alignment"]["rows"], [])

    def test_invalid_inputs_are_rejected(self):
        for options in ({"ciphertext": 123}, {"max_period": True}, {"max_period": 41}, {"key_offset": -1}, {"cipher": {}}, {"steps": "base64"}, {"plaintext_truncated": "yes"}, {"alignment_model": "unknown"}, {"cipher": "vigenere", "key": "123"}, {"cipher": "caesar", "key": "26"}, {"cipher": "gronsfeld", "key": "LEMON"}, {"alignment_start": 8001}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                analyze(options)
        json.dumps(analyze({"ciphertext": "AABB"}), allow_nan=False)


class WorkspaceAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = server.make_server("127.0.0.1", 0)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.httpd.server_address[1]}/api/analysis-workspace"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(3)
        cls.httpd.server_close()

    def post(self, value, headers=None):
        request = urllib.request.Request(self.url, data=json.dumps(value).encode(), headers={"Content-Type": "application/json", **(headers or {})})
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def test_local_request_and_validation(self):
        status, data = self.post({"ciphertext": "AABB"})
        self.assertEqual(status, 200)
        self.assertEqual(data["ciphertext"]["letters"], 4)
        self.assertEqual(self.post({"max_period": 100})[0], 400)

    def test_host_origin_protection_is_not_bypassed(self):
        self.assertEqual(self.post({"ciphertext": "TEXT"}, {"Origin": "https://evil.example"})[0], 403)

    def test_concurrency_limit_and_release_on_error(self):
        with mock.patch.object(server, "LAB_SLOTS") as slots:
            slots.acquire.return_value = False
            self.assertEqual(self.post({"ciphertext": "TEXT"})[0], 429)
            slots.release.assert_not_called()
        with mock.patch.object(server, "LAB_SLOTS") as slots:
            slots.acquire.return_value = True
            self.assertEqual(self.post({"max_period": 100})[0], 400)
            slots.release.assert_called_once()


if __name__ == "__main__":
    unittest.main()
