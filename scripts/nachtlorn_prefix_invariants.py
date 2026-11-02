#!/usr/bin/env python3
"""Exact header compatibility under arbitrary whole-numeral digit relabelling.

This is a necessary-format test, not a packet decoder or an answer search.
Interval subtrees are counted symbolically; no alphabet-permutation cutoff is
used. Bytes are big-endian and minimal; numeral leading zeros may be retained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def validate(text: str, alphabet: str, bias: int) -> None:
    if (not text or not 2 <= len(alphabet) <= 26 or len(set(alphabet)) != len(alphabet)
            or not set(text) <= set(alphabet) or bias not in (0, 1)):
        raise ValueError("nonempty numeral, distinct alphabet of size2..26, and bias0/1 required")


def numeral(text: str, mapping: dict[str, int], base: int, bias: int = 0) -> int:
    value = 0
    for glyph in text:
        value = value * base + mapping[glyph] + bias
    return value


def numeric_bounds(text: str, alphabet: str = ALPHABET, bias: int = 0) -> tuple[int, int]:
    """Exact extrema over complete digit permutations, by rearrangement."""
    validate(text, alphabet, bias)
    base = len(alphabet)
    weights = dict.fromkeys(alphabet, 0)
    power = 1
    for glyph in reversed(text):
        weights[glyph] += power
        power *= base
    ordered = sorted(weights.values(), reverse=True)
    shift = bias * (power - 1) // (base - 1)
    return (sum(i * weight for i, weight in enumerate(ordered)) + shift,
            sum((base - 1 - i) * weight for i, weight in enumerate(ordered)) + shift)


def count_interval(text: str, lower: int, upper: int, *, alphabet: str = ALPHABET,
                   bias: int = 0, fixed: dict[str, int] | None = None) -> dict:
    """Count complete bijections whose numeral lies in an inclusive interval.

    Each interval-contained prefix contributes (base-assigned)! completions.
    Only intersecting boundary prefixes need further traversal. This also counts
    permutations of unused glyphs, deliberately: the objects counted are complete
    digit alphabets, not distinct integer values.
    """
    validate(text, alphabet, bias)
    base = len(alphabet)
    fixed = dict(fixed or {})
    if (lower > upper or not set(fixed) <= set(alphabet)
            or any(not isinstance(v, int) or not 0 <= v < base for v in fixed.values())
            or len(set(fixed.values())) != len(fixed)):
        raise ValueError("ordered interval and injective in-range fixed assignments required")
    span = base ** len(text)
    shift = bias * (span - 1) // (base - 1)
    low, high = max(0, lower - shift), min(span - 1, upper - shift)
    total = nodes = closed = depth = 0
    witness = None
    stack = [(0, 0, span, fixed)] if low <= high else []
    while stack:
        index, start, width, mapping = stack.pop()
        nodes += 1
        depth = max(depth, index)
        end = start + width - 1
        if end < low or start > high:
            continue
        if low <= start and end <= high:
            total += math.factorial(base - len(mapping))
            closed += 1
            if witness is None:
                witness = dict(mapping)
                free = iter(sorted(set(range(base)) - set(witness.values())))
                for glyph in alphabet:
                    if glyph not in witness:
                        witness[glyph] = next(free)
            continue
        unit = width // base
        glyph = text[index]
        first = (max(low, start) - start) // unit
        last = (min(high, end) - start) // unit
        used = set(mapping.values())
        choices = [mapping[glyph]] if glyph in mapping else range(first, last + 1)
        for digit in choices:
            if not first <= digit <= last or (glyph not in mapping and digit in used):
                continue
            following = mapping if glyph in mapping else {**mapping, glyph: digit}
            stack.append((index + 1, start + digit * unit, unit, following))
    return {"alphabet_mappings": total, "nodes": nodes, "closed_subtrees": closed,
            "max_prefix_letters": depth, "witness_mapping": witness}


def header_catalog() -> dict[str, tuple[bytes, ...]]:
    return {
        "gzip": tuple(b"\x1f\x8b\x08" + bytes([flags]) for flags in range(32)),
        "zlib": tuple(bytes([cmf, flg]) for cmf in range(8, 121, 16) for flg in range(256)
                      if (256 * cmf + flg) % 31 == 0),
        "bzip2": tuple(b"BZh" + bytes([level]) + marker for level in range(49, 58)
                       for marker in (bytes.fromhex("314159265359"), bytes.fromhex("177245385090"))),
        "xz": (bytes.fromhex("fd377a585a00"),),
    }


def prefix_interval(header: bytes, byte_length: int) -> tuple[int, int]:
    if not header or header[0] == 0 or byte_length < len(header):
        raise ValueError("a nonzero-leading header fitting the minimal byte width is required")
    tail_bits = 8 * (byte_length - len(header))
    prefix = int.from_bytes(header, "big")
    return prefix << tail_bits, ((prefix + 1) << tail_bits) - 1


def scan(text: str) -> dict:
    validate(text, ALPHABET, 0)
    catalog = header_catalog()
    cases = []
    for drop in (False, True):
        if drop and not text.endswith("I"):
            continue
        retained = text[:-1] if drop else text
        for bias in (0, 1):
            lower, upper = numeric_bounds(retained, bias=bias)
            lengths = list(range(max(1, (lower.bit_length() + 7) // 8),
                                 max(1, (upper.bit_length() + 7) // 8) + 1))
            formats = []
            for name, headers in catalog.items():
                compatible = canonical = trials = nodes = 0
                positive = []
                witness = None
                max_depth = 0
                for byte_length in lengths:
                    for header in headers:
                        if len(header) > byte_length:
                            continue
                        lo, hi = prefix_interval(header, byte_length)
                        result = count_interval(retained, lo, hi, bias=bias)
                        count = result["alphabet_mappings"]
                        zero_count = 0
                        if bias == 0 and count:
                            zero_result = count_interval(retained, lo, hi, bias=bias, fixed={retained[0]: 0})
                            zero_count = zero_result["alphabet_mappings"]
                            nodes += zero_result["nodes"]
                        trials += 1
                        nodes += result["nodes"]
                        max_depth = max(max_depth, result["max_prefix_letters"])
                        compatible += count
                        canonical += count - zero_count
                        if not count:
                            continue
                        positive.append({"bytes": byte_length, "header_hex": header.hex(),
                                         "alphabet_mappings": count, "canonical_mappings": count - zero_count})
                        if witness is None:
                            mapping = result["witness_mapping"]
                            value = numeral(retained, mapping, 26, bias)
                            raw = value.to_bytes(byte_length, "big")
                            if not raw.startswith(header) or len(raw) != max(1, (value.bit_length() + 7) // 8):
                                raise AssertionError("prefix compatibility witness failed")
                            witness = {"digit_alphabet": "".join(sorted(mapping, key=mapping.get)),
                                       "bytes": byte_length, "prefix_hex": raw[:16].hex(),
                                       "binary_sha256": hashlib.sha256(raw).hexdigest(),
                                       "canonical_numeral": bias == 1 or mapping[retained[0]] != 0,
                                       "scope": "Arbitrary completion certifies a header only; not a recovered packet or key."}
                formats.append({"format": name, "header_byte_length_trials": trials,
                                "alphabet_mappings": compatible, "canonical_mappings": canonical,
                                "positive_header_intervals": positive, "witness": witness,
                                "search_nodes": nodes, "max_prefix_letters_examined": max_depth})
            cases.append({"drop_final_i": drop, "retained_letters": len(retained), "bias": bias,
                          "feasible_minimal_byte_lengths": lengths, "formats": formats})
    return {"status": "Exact raw big-endian numeral/header compatibility; no packet or answer recovered.",
            "letter_sha256": hashlib.sha256(text.encode("ascii")).hexdigest(), "source_letters": len(text),
            "alphabet_permutations_per_model": math.factorial(26),
            "headers": {name: [h.hex() for h in headers] for name, headers in catalog.items()},
            "cases": cases,
            "limitations": ["No little-endian, digit reversal, block packing, letterwise cipher or book stage tested.",
                            "Positive counts prove header compatibility only, not checksum-valid payloads.",
                            "Fixed-width A0 counts permit a zero-valued first glyph; canonical counts exclude it.",
                            "Counts are descriptive, not p-values or author-provenance evidence."]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        parser.error("output must not overwrite the original source")
    raw = args.path.read_bytes()
    rows = raw.decode("ascii").splitlines()[8:]
    if not rows or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in rows):
        parser.error("expected the original ASCII body after its eight-line preamble")
    text = "".join(c for row in rows for c in row if "A" <= c <= "Z")
    result = scan(text)
    result["source_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for case in result["cases"]:
        print(json.dumps({"drop_final_i": case["drop_final_i"], "bias": case["bias"],
                          "compatible_alphabets": {f["format"]: f["alphabet_mappings"] for f in case["formats"]}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
