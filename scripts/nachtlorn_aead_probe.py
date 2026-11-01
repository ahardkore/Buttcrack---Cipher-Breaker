#!/usr/bin/env python3
"""Bounded authenticated-encryption endpoint checks; never accept a text score as a tag.

Optional research dependency: PyCryptodome 3.23.0. Install into ignored scratch
and add that target to PYTHONPATH; the application's dependencies are unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
try:
    import Crypto
    from Crypto.Cipher import AES, ChaCha20_Poly1305
except ImportError:
    Crypto = AES = ChaCha20_Poly1305 = None
from scripts.binary_envelope_probe import ALPHABETS, decode_base26, inspect_binary  # noqa: E402
from scripts.binary_text_probe import text_candidate  # noqa: E402
from scripts.nachtlorn_binary_research import KEYS, apply_periodic  # noqa: E402

PASSWORDS = ("BLOOM", "bloom", "BLPNM", "blpnm", "BLNPM", "blnpm",
             "NACHTLORN", "Nachtlorn", "nachtlorn", "4300", "ULYSSES", "Ulysses",
             "ulysses", "JOYCE", "Joyce", "joyce", "BLOOM4300", "bloom4300")
MODES = (("AES-GCM", 12), ("AES-GCM", 16), ("AES-EAX", 16),
         ("ChaCha20-Poly1305", 12), ("ChaCha20-Poly1305", 24))


def derive_keys(passwords=PASSWORDS):
    result, seen = [], set()
    for password in passwords:
        raw = password.encode("ascii")
        candidates = (("sha256", hashlib.sha256(raw).digest()),
                      ("sha256-first16", hashlib.sha256(raw).digest()[:16]),
                      ("md5", hashlib.md5(raw).digest()),
                      ("nul-pad16", raw.ljust(16, b"\0")),
                      ("nul-pad32", raw.ljust(32, b"\0")))
        for kind, key in candidates:
            if len(key) not in (16, 32) or key in seen:
                continue
            seen.add(key)
            result.append({"password": password, "derivation": kind, "key": key})
    return result


def probe_packet(data: bytes, keys: list[dict]) -> dict:
    if AES is None:
        raise RuntimeError("PyCryptodome research dependency is not installed")
    attempts, by_mode, accepted = 0, {}, []
    for mode, nonce_length in MODES:
        if len(data) <= nonce_length + 16:
            continue
        nonce = data[:nonce_length]
        rest = data[nonce_length:]
        for framing in ("nonce-ciphertext-tag", "nonce-tag-ciphertext"):
            ciphertext, tag = (rest[:-16], rest[-16:]) if framing == "nonce-ciphertext-tag" else (rest[16:], rest[:16])
            for key_record in keys:
                key = key_record["key"]
                if mode == "ChaCha20-Poly1305" and len(key) != 32:
                    continue
                attempts += 1
                by_mode[mode] = by_mode.get(mode, 0) + 1
                try:
                    if mode == "AES-GCM":
                        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce, mac_len=16)
                    elif mode == "AES-EAX":
                        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce, mac_len=16)
                    else:
                        cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
                    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
                except ValueError:
                    continue
                accepted.append({"mode": mode, "nonce_length": nonce_length, "framing": framing,
                                 "password": key_record["password"], "derivation": key_record["derivation"],
                                 "key_hex": key.hex(), "nonce_hex": nonce.hex(), "tag_hex": tag.hex(),
                                 "plaintext_sha256": hashlib.sha256(plaintext).hexdigest(),
                                 "plaintext_hex": plaintext.hex(), "text": text_candidate(plaintext),
                                 "binary_objects": inspect_binary(plaintext)["verified"]})
    return {"attempts": attempts, "by_mode": by_mode, "accepted": accepted}


def scan(source: str, keys: list[dict] | None = None) -> dict:
    if not re.fullmatch(r"[A-Z]+", source):
        raise ValueError("literal uppercase source required")
    keys = derive_keys() if keys is None else keys
    operations = [{"kind": "identity"}] + [{"kind": kind, "key": key, "phase": 0}
                  for key in KEYS for kind in ("minus", "plus", "beaufort")]
    seen, attempts, paths = set(), 0, 0
    accepted, by_mode = [], {}
    for marker in (False, True):
        if marker and not source.endswith("I"):
            continue
        extracted = source[:-1] if marker else source
        for operation in operations:
            paths += 1
            text = apply_periodic(extracted, operation)
            for name, alphabet, bias in ALPHABETS:
                big = decode_base26(text, alphabet, bias)
                for order, data in (("big", big), ("little", big[::-1])):
                    digest = hashlib.sha256(data).hexdigest()
                    if digest in seen:
                        continue
                    seen.add(digest)
                    report = probe_packet(data, keys)
                    attempts += report["attempts"]
                    for mode, count in report["by_mode"].items():
                        by_mode[mode] = by_mode.get(mode, 0) + count
                    for record in report["accepted"]:
                        accepted.append({"drop_final_i": marker, "retained_letters": len(extracted),
                                         "periodic": operation, "alphabet": name, "byteorder": order,
                                         "binary_sha256": digest, **record})
    return {"status": "Bounded AEAD test; tag verification is required for every acceptance.",
            "source_letters": len(source), "letter_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "paths": paths, "unique_binary_buffers": len(seen), "authentication_attempts": attempts,
            "attempts_by_mode": by_mode, "accepted": accepted,
            "key_specification": [{k: v for k, v in record.items() if k != "key"} for record in keys],
            "modes": [list(pair) for pair in MODES], "tag_bytes": 16, "associated_data": "empty",
            "caution": "No arbitrary passwords, salted KDFs, other packet layouts, transpositions or unauthenticated modes tested."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve() == args.path.resolve():
        parser.error("output must not overwrite source")
    if AES is None:
        parser.error("PyCryptodome 3.23.0 required; install the optional research dependency into scratch")
    raw = args.path.read_bytes()
    body = raw.decode("ascii").splitlines()[8:]
    if not body or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in body):
        parser.error("invalid original body")
    source = "".join(c for row in body for c in row if "A" <= c <= "Z")
    started = time.monotonic()
    report = scan(source)
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    report["crypto_version"] = Crypto.__version__
    report["elapsed_seconds"] = time.monotonic() - started
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: len(report[k]) if k == "accepted" else report[k]
                      for k in ("paths", "unique_binary_buffers", "authentication_attempts", "accepted", "elapsed_seconds")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
