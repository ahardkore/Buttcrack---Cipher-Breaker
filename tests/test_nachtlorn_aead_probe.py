from __future__ import annotations

import contextlib
import gzip
import hashlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts.nachtlorn_aead_probe import AES, MODES, ChaCha20_Poly1305, derive_keys, main, probe_packet, scan
from scripts.nachtlorn_binary_research import apply_periodic
from tests.test_binary_envelope_probe import encode_bytes


@unittest.skipIf(AES is None, "optional PyCryptodome research dependency is not installed")
class NachtlornAEADProbeTests(unittest.TestCase):
    def test_all_declared_modes_and_packet_layouts_authenticate_and_reject_corruption(self):
        key = derive_keys(("synthetic",))[0]
        plaintext = b"This is synthetic authenticated control data, not a recovered puzzle message."
        for mode, length in MODES:
            nonce = bytes(range(1, length + 1))
            if mode == "AES-GCM":
                cipher = AES.new(key["key"], AES.MODE_GCM, nonce=nonce, mac_len=16)
            elif mode == "AES-EAX":
                cipher = AES.new(key["key"], AES.MODE_EAX, nonce=nonce, mac_len=16)
            else:
                cipher = ChaCha20_Poly1305.new(key=key["key"], nonce=nonce)
            ciphertext, tag = cipher.encrypt_and_digest(plaintext)
            for framing, packet in (("nonce-ciphertext-tag", nonce + ciphertext + tag),
                                    ("nonce-tag-ciphertext", nonce + tag + ciphertext)):
                result = probe_packet(packet, [key])
                self.assertTrue(any(r["mode"] == mode and r["nonce_length"] == length
                                    and r["framing"] == framing and r["plaintext_hex"] == plaintext.hex()
                                    for r in result["accepted"]))
                corrupted = bytearray(packet)
                corrupted[length + 2] ^= 1
                self.assertEqual(probe_packet(bytes(corrupted), [key])["accepted"], [])

    def test_full_marker_vigenere_base26_aead_gzip_control(self):
        key = derive_keys(("bloom",))[0]
        payload = b'{"synthetic":true,"outlier":"CONTROL ONLY","note":"not a recovered puzzle answer"}'
        compressed = gzip.compress(payload, mtime=0)
        nonce = bytes(range(1, 13))
        cipher = AES.new(key["key"], AES.MODE_GCM, nonce=nonce, mac_len=16)
        ciphertext, tag = cipher.encrypt_and_digest(compressed)
        letters = encode_bytes(nonce + ciphertext + tag)
        source = apply_periodic(letters, {"kind": "plus", "key": "BLOOM", "phase": 0}) + "I"
        report = scan(source, [key])
        self.assertTrue(any(record["drop_final_i"] and record["periodic"] == {"kind": "minus", "key": "BLOOM", "phase": 0}
                            and record["plaintext_hex"] == compressed.hex()
                            and any(obj["classification"]["sha256"] == hashlib.sha256(payload).hexdigest()
                                    for obj in record["binary_objects"])
                            for record in report["accepted"]))
        self.assertEqual(sum(report["attempts_by_mode"].values()), report["authentication_attempts"])

    def test_key_specification_is_deterministic_and_cli_cannot_overwrite_source(self):
        records = derive_keys()
        self.assertEqual(records, derive_keys())
        self.assertEqual(len(records), len({r["key"] for r in records}))
        self.assertTrue(all(len(r["key"]) in (16, 32) for r in records))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "original.txt"
            path.write_bytes(b"unchanged")
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                with self.assertRaises(SystemExit) as failure:
                    main([str(path), "--output", str(path)])
            self.assertEqual(failure.exception.code, 2)
            self.assertIn("must not overwrite", errors.getvalue())
            self.assertEqual(path.read_bytes(), b"unchanged")


if __name__ == "__main__":
    unittest.main()
