#!/usr/bin/env python3
"""Exact leading-glyph capacity certificates for the registered R8 field schema.

Passing a necessary width bound is not table recovery. No solver, alphabet
search, source transform, checksum guessing, or candidate-word scoring is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
FIELDS = (("count", 7, 32), ("key", 14, 64), ("checksum", 7, 32))
LAYOUTS = ("cell_interleaved", "field_major")
ORDERS = ("most_significant_first", "least_significant_first")


def leading_capacity(base: int, width: int, bits: int, bias: int) -> int:
    """Number of possible most-significant zero-based digits, a relaxation.

    Suffix glyph digits are relaxed to independent zeros; repeated-glyph and
    bijection constraints can only make the actual admissible set smaller.
    """
    if base < 2 or width < 1 or bits < 1 or bias not in (0, 1):
        raise ValueError("base>=2, positive width/bits, bias0/1 required")
    shift = bias * (base ** width - 1) // (base - 1)
    maximum_digit = ((1 << bits) - 1 - shift) // base ** (width - 1)
    return max(0, min(base, maximum_digit + 1))


def validate(text, fields, layout, order, bias, alphabet):
    if (not text or not 2 <= len(alphabet) <= 26 or len(set(alphabet)) != len(alphabet)
            or not set(text) <= set(alphabet) or layout not in LAYOUTS or order not in ORDERS
            or bias not in (0, 1) or not fields or len({f[0] for f in fields}) != len(fields)
            or any(width < 1 or bits < 1 for _name, width, bits in fields)):
        raise ValueError("valid nonempty source, schema, layout, order, bias and alphabet required")


def analyze(text: str, layout: str, order: str, bias: int, *, fields=FIELDS, alphabet=ALPHABET) -> dict:
    validate(text, fields, layout, order, bias, alphabet)
    stride = sum(width for _name, width, _bits in fields)
    common = {"layout": layout, "digit_order": order, "bias": bias, "retained_letters": len(text)}
    if len(text) % stride:
        return {**common, "status": "dimension_failure", "exact_exclusion": True,
                "cell_letters": stride, "remainder": len(text) % stride, "fields": []}
    cells = len(text) // stride
    records, before = [], 0
    for name, width, bits in fields:
        local = 0 if order == "most_significant_first" else width - 1
        if layout == "cell_interleaved":
            positions = [cell * stride + before + local for cell in range(cells)]
        else:
            positions = [cells * before + cell * width + local for cell in range(cells)]
        first = {}
        for index in positions:
            first.setdefault(text[index], index)
        capacity = leading_capacity(len(alphabet), width, bits, bias)
        excluded = len(first) > capacity
        witnesses = [{"glyph": glyph, "body_letter_index": index}
                     for glyph, index in list(first.items())[:capacity + 1]] if excluded else []
        records.append({"name": name, "letters": width, "bits": bits,
                        "distinct_leading_glyphs": len(first), "permitted_leading_digits": capacity,
                        "capacity_exceeded": excluded, "certificate": witnesses})
        before += width
    excluded = any(f["capacity_exceeded"] for f in records)
    return {**common, "cells": cells, "fields": records, "exact_exclusion": excluded,
            "status": "leading_capacity_exclusion" if excluded else "necessary_bound_only"}


def verify_certificate(text: str, layout: str, order: str, bias: int, field_name: str,
                       certificate: list[dict], *, fields=FIELDS, alphabet=ALPHABET) -> bool:
    """Replay a finite witness with independent digit arithmetic and index checks.

    This intentionally does not call leading_capacity or analyze, and enumerates
    at most 26 candidate leading digits, not alphabet permutations.
    """
    validate(text, fields, layout, order, bias, alphabet)
    names = [f[0] for f in fields]
    stride = sum(f[1] for f in fields)
    if field_name not in names or len(text) % stride:
        return False
    slot = names.index(field_name)
    _name, width, bits = fields[slot]
    base = len(alphabet)
    minimum_bias = sum(bias * base ** j for j in range(width))
    allowed = sum(d * base ** (width - 1) + minimum_bias < 2 ** bits for d in range(base))
    if len(certificate) != allowed + 1:
        return False
    cells = len(text) // stride
    before = sum(f[1] for f in fields[:slot])
    seen = set()
    for witness in certificate:
        glyph, index = witness.get("glyph"), witness.get("body_letter_index")
        if (not isinstance(glyph, str) or len(glyph) != 1 or glyph not in alphabet
                or glyph in seen or type(index) is not int
                or not 0 <= index < len(text) or text[index] != glyph):
            return False
        local = 0 if order == "most_significant_first" else width - 1
        offset = index - local
        if layout == "cell_interleaved":
            valid_position = offset >= before and (offset - before) % stride == 0
        else:
            start = cells * before
            valid_position = start <= offset < start + cells * width and (offset - start) % width == 0
        if not valid_position:
            return False
        seen.add(glyph)
    return True


def scan(text: str) -> dict:
    if not text.endswith("I"):
        raise ValueError("expected original terminal I for the explicitly registered variants")
    cases = []
    for drop in (False, True):
        retained = text[:-1] if drop else text
        for layout in LAYOUTS:
            for order in ORDERS:
                for bias in (0, 1):
                    case = analyze(retained, layout, order, bias)
                    for field in case["fields"]:
                        if field["capacity_exceeded"] and not verify_certificate(
                                retained, layout, order, bias, field["name"], field["certificate"]):
                            raise AssertionError("certificate failed independent replay")
                    cases.append({"drop_final_i": drop, **case})
    return {"status": "Necessary fixed-width representation tests, not table recovery.",
            "schema": [{"name": n, "letters": w, "bits": b} for n, w, b in FIELDS],
            "index_convention": "zero-based index in retained original body letters, excluding whitespace",
            "cases": cases,
            "limits": ["No header, offset, padding, letter cipher or varying per-cell alphabet is tested.",
                       "Capacity failure applies even with a separate bijective alphabet per field type.",
                       "Passing a bound does not validate a table, population or final outlier."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        parser.error("output must not overwrite the source")
    raw = args.path.read_bytes()
    rows = raw.decode("ascii").splitlines()[8:]
    if not rows or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in rows):
        parser.error("expected original eight-line preamble and ASCII body")
    text = "".join(c for row in rows for c in row if "A" <= c <= "Z")
    result = scan(text)
    result["source_sha256"] = hashlib.sha256(raw).hexdigest()
    result["source_bytes"] = len(raw)
    result["source_letters"] = len(text)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(result["cases"]),
                      "statuses": {status: sum(c["status"] == status for c in result["cases"])
                                   for status in sorted({c["status"] for c in result["cases"]})}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
