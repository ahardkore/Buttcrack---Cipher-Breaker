#!/usr/bin/env python3
"""Registered book-running-key test with structural, not word-based, endpoints.

No keyword/offset/phase search. Reuses a safe low-level envelope validator, not
historical guessed keys or candidate fragments. Recovered code is never executed.
"""
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
from scripts.binary_envelope_probe import inspect_binary  # noqa: E402
from scripts.nachtlorn_role_probe import decode26, inspect_filter, inspect_scalable  # noqa: E402

START = "*** START OF THIS PROJECT GUTENBERG EBOOK ULYSSES ***"
END = "*** END OF THIS PROJECT GUTENBERG EBOOK ULYSSES ***"
OPENING = "Stately, plump Buck Mulligan"
OPERATIONS = ("minus", "plus", "beaufort")


def key_domains(raw: bytes) -> dict[str, str]:
    text = raw.decode("utf-8-sig")
    if text.count(START) != 1 or text.count(END) != 1 or text.count(OPENING) != 1:
        raise ValueError("expected unique pinned book boundaries and opening")
    start, end = text.index(START) + len(START), text.index(END)
    opening = text.index(OPENING)
    if not start < opening < end:
        raise ValueError("book boundaries out of order")
    domains = {"raw-file": text, "gutenberg-body": text[start:end], "story": text[opening:end]}
    return {name: re.sub(r"[^A-Za-z]", "", value).upper() for name, value in domains.items()}


def transform(stream: str, key: str, kind: str, *, inverse: bool = False) -> str:
    if (kind not in OPERATIONS or not re.fullmatch(r"[A-Z]+", stream)
            or not re.fullmatch(r"[A-Z]+", key) or len(key) < len(stream)):
        raise ValueError("a declared operation, literal uppercase text and sufficient nonrepeating key are required")
    result = []
    for c, k in zip(stream, key):
        a, b = ord(c) - 65, ord(k) - 65
        if kind == "minus":
            v = a + b if inverse else a - b
        elif kind == "plus":
            v = a - b if inverse else a + b
        else:
            v = b - a
        result.append(chr(65 + v % 26))
    return "".join(result)


def inspect_packet(data: bytes) -> list[dict]:
    objects = []
    for record in inspect_binary(data)["verified"]:
        if record["format"] not in ("json", "gzip", "zlib", "bzip2", "xz"):
            continue
        if record["offset"] != 0 or record.get("trailing_bytes", 0) != 0:
            continue
        objects.append(record)
    for parser in (inspect_filter, inspect_scalable):
        container = parser(data)
        if container is not None:
            objects.append(container)
    return objects


def scan(stream: str, book: bytes) -> dict:
    return scan_domains(stream, key_domains(book), hashlib.sha256(book).hexdigest())


def scan_domains(stream: str, domains: dict[str, str], book_sha256: str) -> dict:
    if not re.fullmatch(r"[A-Z]+", stream):
        raise ValueError("literal uppercase source required")
    if (not domains or any(not name or not re.fullmatch(r"[A-Z]+", key) or len(key) < len(stream)
                           for name, key in domains.items())):
        raise ValueError("named uppercase key domains with sufficient material required")
    paths, trials, seen, records = 0, 0, set(), []
    roundtrips = []
    for remove_marker in (False, True):
        if remove_marker and not stream.endswith("I"):
            continue
        text = stream[:-1] if remove_marker else stream
        for name, key in domains.items():
            for operation in OPERATIONS:
                decoded = transform(text, key, operation)
                reconstructed = transform(decoded, key, operation, inverse=True) + ("I" if remove_marker else "")
                exact = reconstructed == stream
                if not exact:
                    raise ValueError("letter-stage roundtrip failed")
                paths += 1
                path = {"drop_final_i": remove_marker, "key_domain": name, "operation": operation}
                roundtrips.append({**path, "exact_original_letter_roundtrip": exact})
                for bias in (0, 1):
                    big = decode26(decoded, bias)
                    for order, minimal in (("big", big), ("little", big[::-1])):
                        for zeros in range(8):
                            data = b"\0" * zeros + minimal if order == "big" else minimal + b"\0" * zeros
                            trials += 1
                            digest = hashlib.sha256(data).hexdigest()
                            if digest in seen:
                                continue
                            seen.add(digest)
                            objects = inspect_packet(data)
                            if objects:
                                records.append({**path, "bias": bias, "byteorder": order,
                                                "restored_zero_bytes": zeros, "binary_sha256": digest,
                                                "objects": objects})
    return {"status": "Registered running-key object test; no answer is selected by word recognition.",
            "source_letters": len(stream), "letter_sha256": hashlib.sha256(stream.encode()).hexdigest(),
            "book_sha256": book_sha256,
            "key_domains": {name: {"letters": len(key), "sha256": hashlib.sha256(key.encode()).hexdigest(),
                                   "prefix32": key[:32]} for name, key in domains.items()},
            "letter_paths": paths, "representation_configurations": trials,
            "unique_binary_buffers": len(seen), "roundtrips": roundtrips, "accepted_records": records,
            "caution": "Only the declared key domains, start0, signs, encodings and whole-packet schemas. A roundtrip alone is not meaningful plaintext."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--book", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.path.resolve(), args.book.resolve()):
        parser.error("output must not overwrite either input")
    raw = args.path.read_bytes()
    body = raw.decode("ascii").splitlines()[8:]
    if not body or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in body):
        parser.error("expected original body")
    stream = "".join(c for row in body for c in row if "A" <= c <= "Z")
    report = scan(stream, args.book.read_bytes())
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"letter_paths": report["letter_paths"],
                      "representation_configurations": report["representation_configurations"],
                      "accepted_records": len(report["accepted_records"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
