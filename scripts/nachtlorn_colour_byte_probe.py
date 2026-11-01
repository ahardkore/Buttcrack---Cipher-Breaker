#!/usr/bin/env python3
"""R10: direct byte-XOR role for four newly derived colour/poem strings."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.nachtlorn_colour_probe import buffers  # noqa: E402
from scripts.nachtlorn_running_book_probe import inspect_packet  # noqa: E402

KEYS = ("GLOOM", "WLOOM", "GLPNM", "WLPNM")
LITERAL_WORDS = ("BLACK", "GREEN", "WHITE")


def key_material(words=KEYS):
    words = tuple(words)
    if words not in (KEYS, LITERAL_WORDS):
        raise ValueError("registered key profile required")
    for word in words:
        for password in (word, word.lower(), word.title()):
            raw = password.encode("ascii")
            for kind, material in (("raw-ascii", raw), ("sha256", hashlib.sha256(raw).digest())):
                yield {"password": password, "derivation": kind}, material


def xor(data: bytes, key: bytes) -> bytes:
    if not key:
        raise ValueError("nonempty key required")
    return bytes(value ^ key[index % len(key)] for index, value in enumerate(data))


def inspect(data: bytes) -> dict:
    objects = inspect_packet(data)
    printable = len(data) >= 64 and all(value in (9, 10, 13) or 32 <= value <= 126 for value in data)
    diagnostics = [name for name, signature in (("npy", b"\x93NUMPY"), ("sqlite", b"SQLite format 3\0"))
                   if data.startswith(signature)]
    return {"objects": objects, "whole_printable_ascii_candidate": printable,
            "unvalidated_origin_signatures": diagnostics}


def scan(stream: str, words=KEYS) -> dict:
    words = tuple(words)
    if not re.fullmatch(r"[A-Z]+", stream) or len(stream) < 2:
        raise ValueError("literal uppercase source required")
    keys, seen, trials, representations, findings = list(key_material(words)), set(), 0, 0, []
    for marker in (False, True):
        if marker and not stream.endswith("I"):
            continue
        extracted = stream[:-1] if marker else stream
        for spec, data in buffers(extracted):
            representations += 1
            digest = hashlib.sha256(data).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            for key_spec, material in keys:
                decoded = xor(data, material)
                trials += 1
                result = inspect(decoded)
                if result["objects"] or result["whole_printable_ascii_candidate"] or result["unvalidated_origin_signatures"]:
                    if xor(decoded, material) != data:
                        raise ValueError("byte roundtrip failure")
                    findings.append({"drop_final_i": marker, **spec, **key_spec, **result,
                                     "input_binary_sha256": digest, "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
                                     "decoded_hex": decoded.hex(), "exact_byte_roundtrip": True})
    return {"hypothesis": "R10" if tuple(words) == KEYS else "R11", "source_letters": len(stream),
            "letter_sha256": hashlib.sha256(stream.encode()).hexdigest(),
            "representation_configurations": representations, "unique_buffers": len(seen),
            "key_specification": [spec for spec, _ in keys], "byte_xor_trials": trials, "findings": findings,
            "caution": "Only raw-body byte XOR at phase0; no prior letter cipher. Complete objects, printable candidates and unvalidated signatures are distinguished. A byte roundtrip or magic header is not a recovered population or outlier."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve() == args.path.resolve():
        parser.error("output must not overwrite source")
    raw = args.path.read_bytes()
    rows = raw.decode("ascii").splitlines()[8:]
    if not rows or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in rows):
        parser.error("expected literal original body")
    stream = "".join(c for row in rows for c in row if "A" <= c <= "Z")
    report = scan(stream)
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({name: len(report[name]) if name == "findings" else report[name]
                      for name in ("representation_configurations", "unique_buffers", "byte_xor_trials", "findings")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
