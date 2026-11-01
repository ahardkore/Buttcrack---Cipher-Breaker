#!/usr/bin/env python3
"""Explicitly test the user's remove-I idea with a base-25 binary endpoint.

This is a lossy extraction hypothesis, not a correction to the source. Both
remove-I-before-mod25 and mod26-before-remove-I orders are recorded explicitly.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.binary_envelope_probe import inspect_binary, keyed_alphabet  # noqa: E402
from scripts.binary_text_probe import apply_mask, mask_specs, text_candidate  # noqa: E402
from scripts.nachtlorn_binary_research import (KEYS, apply_periodic, book_dictionaries, byte_prefix_plausible,
                                              periodic_specs)  # noqa: E402
from scripts.nachtlorn_numeric_probe import bit_profile  # noqa: E402

ALPHABET = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
ALPHABETS = (("A0-noI", ALPHABET, 0), ("A1-noI", ALPHABET, 1),
             ("J0-noI", ALPHABET[8:] + ALPHABET[:8], 0), ("reverse-noI", ALPHABET[::-1], 0),
             ("keyed-BLOOM-noI", keyed_alphabet("BLOOM").replace("I", ""), 0),
             ("keyed-NACHTLORN-noI", keyed_alphabet("NACHTLORN").replace("I", ""), 0))


def decode25(text: str, alphabet: str, bias: int) -> bytes:
    if bias not in (0, 1):
        raise ValueError("bias must be zero or one")
    if not text or set(text) - set(ALPHABET) or set(alphabet) != set(ALPHABET) or len(alphabet) != 25:
        raise ValueError("expected the 25-letter alphabet excluding I")
    digits = text.translate(str.maketrans(alphabet, "0123456789abcdefghijklmno"))
    value = 0
    for start in range(0, len(digits), 512):
        block = digits[start:start + 512]
        value = value * 25 ** len(block) + int(block, 25)
    value += bias * ((25 ** len(digits) - 1) // 24)
    return value.to_bytes(max(1, (value.bit_length() + 7) // 8), "big")


def periodic25(text: str, key: str, phase: int, kind: str) -> str:
    if not key or kind not in ("minus", "plus", "beaufort"):
        raise ValueError("a nonempty key and a supported operation are required")
    key_values = [ALPHABET.index(c) for c in key]
    output = []
    for i, c in enumerate(text):
        a, b = ALPHABET.index(c), key_values[(i + phase) % len(key)]
        v = a - b if kind == "minus" else a + b if kind == "plus" else b - a
        output.append(ALPHABET[v % 25])
    return "".join(output)


def variants(source: str):
    stripped = source.replace("I", "")
    yield stripped, {"order": "remove-I", "operation": "identity"}
    for key in KEYS:
        for phase in range(len(key)):
            for kind in ("minus", "plus", "beaufort"):
                yield periodic25(stripped, key, phase, kind), {
                    "order": "remove-I-then-mod25", "key": key, "phase": phase, "kind": kind}
    for spec in periodic_specs()[1:]:
        yield apply_periodic(source, spec).replace("I", ""), {"order": "mod26-then-remove-I", **spec}


def checks() -> dict:
    examples = 0
    for _, alphabet, bias in ALPHABETS:
        for length in (1, 5, 512, 513, 8411):
            text = (ALPHABET * ((length + 24) // 25))[:length]
            expected = 0
            for c in text:
                expected = 25 * expected + alphabet.index(c) + bias
            assert int.from_bytes(decode25(text, alphabet, bias), "big") == expected
            examples += 1
    payload = b"[1,2,3,999]"
    compressed = gzip.compress(payload, mtime=0)
    number = int.from_bytes(compressed, "big")
    letters = ""
    while number:
        number, digit = divmod(number, 25)
        letters = ALPHABET[digit] + letters
    encrypted = periodic25(letters, "BLOOM", 2, "plus")
    padded = "I".join(encrypted[i:i + 7] for i in range(0, len(encrypted), 7)) + "I"
    recovered = periodic25(padded.replace("I", ""), "BLOOM", 2, "minus")
    decoded = decode25(recovered, ALPHABET, 0)
    result = inspect_binary(decoded)
    assert any(o["format"] == "gzip" and o["classification"]["sha256"] == hashlib.sha256(payload).hexdigest()
               for o in result["verified"])
    return {"scalar_oracles": examples, "synthetic_inserted_I_gzip_control": True}


def scan(source: str, dictionaries: dict[int, bytes] | None = None) -> dict:
    seen = set()
    paths = binary_count = masks_count = selected = 0
    verified, texts, numeric = [], [], []
    masks = mask_specs(KEYS)
    for text, path in variants(source):
        paths += 1
        for name, alphabet, bias in ALPHABETS:
            big = decode25(text, alphabet, bias)
            profile = bit_profile(big)
            if profile["score"] >= 8:
                numeric.append({**path, "alphabet": name, "profile": profile})
            for byteorder, data in (("big", big), ("little", big[::-1])):
                digest = hashlib.sha256(data).digest()
                if digest in seen:
                    continue
                seen.add(digest)
                binary_count += 1
                for mask in masks:
                    masks_count += 1
                    if mask["kind"] != "identity" and not byte_prefix_plausible(apply_mask(data[:128], mask)):
                        continue
                    selected += 1
                    decoded = apply_mask(data, mask)
                    metadata = {**path, "letters": len(text), "alphabet": name, "byteorder": byteorder,
                                "byte_mask": mask, "binary_sha256": hashlib.sha256(decoded).hexdigest()}
                    result = inspect_binary(decoded, dictionaries)
                    if result["verified"]:
                        verified.append({**metadata, "objects": result["verified"]})
                    candidate = text_candidate(decoded)
                    if candidate:
                        texts.append({**metadata, "text": candidate})
    return {"paths": paths, "binary_buffers": binary_count, "byte_masks": masks_count,
            "selected": selected, "verified": verified, "text_candidates": texts,
            "numeric_flags": numeric, "source_letters": len(source),
            "remove_I_letters": len(source.replace("I", "")), "checks": checks(),
            "caution": "Explicit removal hypothesis only; no transposition or arbitrary key search."}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("path", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--dictionary", type=Path)
    args = p.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        p.error("output must not overwrite source")
    if args.dictionary and args.dictionary.resolve() == args.output.resolve():
        p.error("output must not overwrite dictionary")
    raw = args.path.read_bytes()
    body = raw.decode("ascii").splitlines()[8:]
    if not body or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in body):
        p.error("invalid original body")
    source = "".join(c for row in body for c in row if "A" <= c <= "Z")
    dictionaries, metadata = book_dictionaries(args.dictionary.read_bytes()) if args.dictionary else (None, [])
    report = scan(source, dictionaries)
    report["dictionary_variants"] = metadata
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] if not isinstance(report[k], list) else len(report[k])
                      for k in ("paths", "binary_buffers", "byte_masks", "verified", "text_candidates", "numeric_flags")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
