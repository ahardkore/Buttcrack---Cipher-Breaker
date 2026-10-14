"""Known answers, negative controls and local API contracts for explicit labs."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from buttcrack import cli, server
from buttcrack.modern import enigma, rsa, run

HAS_CRYPTO = importlib.util.find_spec("cryptography") is not None


class RSATests(unittest.TestCase):
    def test_shared_prime_decrypts_and_verifies(self):
        result = run("rsa", {"keys": [{"n": "3233", "e": "17", "c": "2790"}, {"n": "2867", "e": "17"}], "fermat_steps": 0})
        self.assertEqual(len(result["findings"]), 2)
        finding = next(f for f in result["findings"] if f["key_index"] == 0)
        self.assertEqual(finding["raw_plaintext"]["utf8"], "A")
        self.assertTrue(finding["reencryption_verified"])
        self.assertEqual(int(finding["p"]) * int(finding["q"]), 3233)

    def test_fermat(self):
        result = run("rsa", {"keys": [{"n": str(1009 * 1013), "e": "65537"}]})
        self.assertEqual(result["findings"][0]["attack"], "bounded Fermat close-factor search")
        self.assertTrue(result["findings"][0]["factorization_verified"])

    def test_wiener(self):
        p, q, d = 1009, 100003, 5
        e = pow(d, -1, (p - 1) * (q - 1))
        result = run("rsa", {"keys": [{"n": str(p * q), "e": str(e), "c": str(pow(65, e, p * q))}], "fermat_steps": 0})
        self.assertEqual(result["findings"][0]["attack"], "Wiener small-private-exponent attack")
        self.assertEqual(result["findings"][0]["raw_plaintext"]["integer"], "65")

    def test_direct_root(self):
        result = run("rsa", {"keys": [{"n": "10807", "e": "3", "c": "1000"}], "fermat_steps": 0})
        self.assertEqual(result["findings"][0]["raw_plaintext"]["integer"], "10")

    def test_broadcast(self):
        moduli = [101 * 107, 113 * 131, 137 * 149]
        keys = [{"n": str(n), "e": "3", "c": str(pow(500, 3, n))} for n in moduli]
        result = run("rsa", {"keys": keys, "fermat_steps": 0})
        finding = next(f for f in result["findings"] if "broadcast" in f["attack"])
        self.assertEqual(finding["raw_plaintext"]["integer"], "500")
        self.assertTrue(finding["reencryption_verified"])

    def test_different_messages_do_not_claim_broadcast(self):
        moduli = [101 * 107, 113 * 131, 137 * 149]
        keys = [{"n": str(n), "e": "3", "c": str(pow(500 + i, 3, n))} for i, n in enumerate(moduli)]
        result = run("rsa", {"keys": keys, "fermat_steps": 0})
        self.assertFalse(any("broadcast" in f["attack"] for f in result["findings"]))

    def test_duplicate_moduli_are_not_shared_prime_findings(self):
        result = run("rsa", {"keys": [{"n": "3233", "e": "17"}] * 2, "fermat_steps": 0})
        self.assertFalse(result["findings"])

    def test_composite_shared_factors_do_not_make_a_private_key(self):
        result = run("rsa", {"keys": [{"n": "105", "e": "11"}, {"n": "165", "e": "13"}], "fermat_steps": 0})
        self.assertTrue(result["findings"])
        self.assertTrue(all("d" not in f for f in result["findings"]))

    def test_roots_and_nonperfect_roots(self):
        for degree in (2, 3, 5, 7):
            for value in (1, 2, 10, 100, 1 << 256):
                self.assertEqual(rsa.root(value ** degree, degree), (value, True))
                self.assertEqual(rsa.root(value ** degree + 1, degree), (value, False))

    def test_probable_prime_controls(self):
        for n in (2, 3, 101, 1009, 100003):
            self.assertTrue(rsa.probable_prime(n))
        for n in (0, 1, 9, 561, 1105, 3215031751):
            self.assertFalse(rsa.probable_prime(n))

    def test_bounded_negative_result_and_validation(self):
        result = run("rsa", {"keys": [{"n": "3233", "e": "17"}], "fermat_steps": 0})
        self.assertFalse(result["findings"])
        self.assertIn("not proof of security", result["limitations"])
        for options in ({"keys": []}, {"keys": [None]}, {"keys": [{"n": True, "e": 3}]}, {"keys": [{"n": "3233", "e": "17", "c": "3233"}]}, {"keys": [{"n": "3233", "e": "17"}], "fermat_steps": 20001}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                run("rsa", options)

    def test_budget_exhaustion_is_not_reported_as_security(self):
        with mock.patch.object(rsa.time, "monotonic", side_effect=[0, 6]):
            result = run("rsa", {"keys": [{"n": "3233", "e": "17"}]})
        self.assertTrue(result["budget_exhausted"])
        self.assertFalse(result["findings"])


class KeystreamTests(unittest.TestCase):
    def test_crib_recovers_corresponding_fragment_conditionally(self):
        key = bytes.fromhex("1122334455667788")
        plains = [b"ATTACK!!", b"DEFEND!!"]
        streams = [bytes(a ^ b for a, b in zip(plain, key)).hex() for plain in plains]
        result = run("keystream", {"ciphertexts": streams, "crib": "ATTACK", "offset": 0})
        self.assertEqual(result["fragments"][1]["hypothesis"]["utf8"], "DEFEND")
        self.assertIn("reuse is not proven", result["status"])
        self.assertIn("not verified plaintext", result["limitations"])

    def test_wrong_crib_is_not_verified(self):
        result = run("keystream", {"ciphertexts": ["112233", "112234"], "crib": "BAD"})
        self.assertNotIn("verified", result["fragments"][1])
        self.assertIn("hypothesis", result["fragments"][1])

    def test_unequal_lengths_and_byte_offsets(self):
        result = run("keystream", {"ciphertexts": ["0000000000", "010203"], "crib": "ABC", "offset": 2})
        self.assertEqual(result["pairs"][0]["overlap_bytes"], 3)
        self.assertEqual(result["fragments"][1]["hypothesis"]["bytes"], 1)

    def test_validation(self):
        for options in ({"ciphertexts": ["00"]}, {"ciphertexts": ["00", "zz"]}, {"ciphertexts": ["", "00"]}, {"ciphertexts": ["00", "00"], "crib": "too long"}, {"ciphertexts": ["00", "00"], "crib": "A", "message_index": -1}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                run("keystream", options)


class AESAnalysisTests(unittest.TestCase):
    def test_repeated_blocks_are_not_proof_of_ecb(self):
        result = run("aes", {"data": "ab" * 32 + "ff"})
        self.assertEqual(result["repeated_blocks"][0]["indices"], [0, 1])
        self.assertEqual(result["trailing_bytes"], 1)
        self.assertIn("do not prove AES or ECB", result["limitations"])

    def test_missing_provider_has_clear_error(self):
        with mock.patch.dict(sys.modules, {"cryptography": None}), self.assertRaisesRegex(ValueError, "optional provider"):
            run("aes", {"operation": "decrypt"})


@unittest.skipUnless(HAS_CRYPTO, "optional cryptography provider not installed")
class AESProviderTests(unittest.TestCase):
    def test_ecb_known_answer(self):
        result = run("aes", {"operation": "decrypt", "mode": "ECB", "key": "00" * 16, "data": "66e94bd4ef8a2c3b884cfa59ca342b2e"})
        self.assertEqual(result["output"]["hex"], "00" * 16)
        self.assertFalse(result["authenticated"])
        self.assertTrue(result["round_trip_verified"])

    def test_cbc_and_ctr_nist_vectors(self):
        key, plain = "2b7e151628aed2a6abf7158809cf4f3c", "6bc1bee22e409f96e93d7e117393172a"
        for mode, iv, cipher in (("CBC", "000102030405060708090a0b0c0d0e0f", "7649abac8119b246cee98e9b12e9197d"), ("CTR", "f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff", "874d6191b620e3261bef6864990db6ce")):
            with self.subTest(mode=mode):
                encrypted = run("aes", {"operation": "encrypt", "mode": mode, "iv": iv, "key": key, "data": plain})
                self.assertEqual(encrypted["output"]["hex"], cipher)
                decrypted = run("aes", {"operation": "decrypt", "mode": mode, "iv": iv, "key": key, "data": cipher})
                self.assertEqual(decrypted["output"]["hex"], plain)

    def test_gcm_known_answer_and_tampering(self):
        options = {"operation": "decrypt", "mode": "GCM", "key": "00" * 16, "iv": "00" * 12, "data": "0388dace60b6a392f328c2b971b2fe78", "tag": "ab6e47d42cec13bdf53a67b21257bddf"}
        self.assertEqual(run("aes", options)["output"]["hex"], "00" * 16)
        self.assertTrue(run("aes", options)["authenticated"])
        for changed in ({"tag": "00" * 16}, {"aad": "00"}, {"data": "00" * 16}, {"key": "01" * 16}):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "authentication failed"):
                run("aes", {**options, **changed})

    def test_gcm_aad_encrypt_decrypt(self):
        options = {"operation": "encrypt", "mode": "GCM", "key": "00" * 16, "iv": "01" * 12, "aad": "deadbeef", "data": "68656c6c6f"}
        encrypted = run("aes", options)
        plain = run("aes", {**options, "operation": "decrypt", "data": encrypted["output"]["hex"], "tag": encrypted["tag"]})
        self.assertEqual(plain["output"]["utf8"], "hello")
        self.assertTrue(plain["authenticated"])

    def test_padding_round_trip_and_bad_padding(self):
        options = {"operation": "encrypt", "mode": "CBC", "key": "00" * 16, "iv": "00" * 16, "data": "68656c6c6f", "padding": True}
        encrypted = run("aes", options)
        plain = run("aes", {**options, "operation": "decrypt", "data": encrypted["output"]["hex"]})
        self.assertEqual(plain["output"]["utf8"], "hello")
        with self.assertRaisesRegex(ValueError, "padding"):
            run("aes", {**options, "operation": "decrypt", "data": "66e94bd4ef8a2c3b884cfa59ca342b2e"})

    def test_input_validation(self):
        options = {"operation": "decrypt", "mode": "CBC", "key": "00" * 16, "iv": "00" * 16, "data": "00" * 16}
        for changed in ({"key": "00"}, {"iv": "00"}, {"data": "ab"}, {"mode": "GCM", "tag": ""}, {"mode": "CTR", "padding": True}, {"aad": "00"}, {"padding": "false"}, {"mode": "unknown"}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                run("aes", {**options, **changed})


class EnigmaTests(unittest.TestCase):
    def test_known_vectors(self):
        for plain, cipher in (("AAAAA", "BDZGO"), ("HELLOWORLD", "ILBDAAMTAZ")):
            with self.subTest(plain=plain):
                self.assertEqual(run("enigma", {"text": plain})["output"], cipher)
                self.assertEqual(run("enigma", {"text": cipher})["output"], plain)

    def test_double_stepping_and_ring_independent_notches(self):
        for rings in ("AAA", "BCD"):
            machine = enigma.Machine({"rings": rings})
            positions = list(map(enigma.ALPHABET.index, "ADU"))
            for expected in ("ADV", "AEW", "BFX"):
                machine.step(positions)
                self.assertEqual("".join(enigma.ALPHABET[p] for p in positions), expected)

    def test_rings_and_plugboard_round_trip(self):
        options = {"text": "MEETATNOON", "rings": "BDF", "positions": "QWE", "plugboard": "AB CD EF GH", "rotors": ["V", "III", "II"], "reflector": "C"}
        encrypted = run("enigma", options)
        self.assertTrue(encrypted["round_trip_verified"])
        self.assertEqual(run("enigma", {**options, "text": encrypted["output"]})["output"], "MEETATNOON")

    def test_search_recovers_initial_positions(self):
        result = run("enigma", {"operation": "search", "text": "ILBDAAMTAZ", "crib": "HELLOWORLD", "budget": 5})
        self.assertTrue(any(c["positions"] == "AAA" and c["plaintext"] == "HELLOWORLD" and c["reencryption_verified"] for c in result["candidates"]))

    def test_budget_exhaustion_is_explicit(self):
        with mock.patch.object(enigma.time, "monotonic", side_effect=[0, 6]):
            result = run("enigma", {"operation": "search", "text": "ILBDAAMTAZ", "crib": "HELLOWORLD"})
        self.assertTrue(result["budget_exhausted"])
        self.assertFalse(result["search_complete"])
        self.assertEqual(result["positions_examined"], 0)

    def test_validation(self):
        for changed in ({"rotors": ["I", "I", "II"]}, {"rings": "AB"}, {"positions": "AB1"}, {"plugboard": "AB AC"}, {"reflector": "Z"}, {"text": "ß"}, {"operation": "search", "crib": "short"}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                run("enigma", {"text": "HELLOWORLD", **changed})


class ModernAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = server.make_server("127.0.0.1", 0)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.httpd.server_address[1]}/api/modern"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(3)
        cls.httpd.server_close()

    def post(self, value):
        request = urllib.request.Request(self.url, data=json.dumps(value).encode(), headers={"Content-Type": "application/json"})
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def test_valid_local_request(self):
        status, result = self.post({"lab": "enigma", "options": {"text": "AAAAA"}})
        self.assertEqual(status, 200)
        self.assertEqual(result["output"], "BDZGO")

    def test_invalid_input_is_400_not_server_failure(self):
        for value in ({"lab": "unknown"}, {"lab": "rsa", "options": []}, {"lab": "rsa", "options": {"keys": []}}):
            with self.subTest(value=value):
                self.assertEqual(self.post(value)[0], 400)

    def test_concurrency_limit(self):
        with mock.patch.object(server, "LAB_SLOTS") as slots:
            slots.acquire.return_value = False
            self.assertEqual(self.post({"lab": "rsa"})[0], 429)
            slots.release.assert_not_called()

    def test_slot_released_after_validation_failure(self):
        with mock.patch.object(server, "LAB_SLOTS") as slots:
            slots.acquire.return_value = True
            self.assertEqual(self.post({"lab": "rsa"})[0], 400)
            slots.release.assert_called_once()


class ModernCLITests(unittest.TestCase):
    def test_cli_file_and_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text('{"text":"AAAAA"}')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.main(["modern", "enigma", "--input", str(path)]), 0)
            self.assertEqual(json.loads(output.getvalue())["output"], "BDZGO")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["modern", "rsa", "[]"]), 2)

    def test_dispatch_validation(self):
        for lab, options in (("invalid", {}), ("aes", []), ([], {})):
            with self.subTest(lab=lab), self.assertRaises(ValueError):
                run(lab, options)


if __name__ == "__main__":
    unittest.main()
