#!/usr/bin/env python3
"""R8: independently validated, key-only IBLT under explicit fieldwise base26.

The pinned C++ reference specifies logical fields and hashing, NOT this wire
format. Only complete peeling plus exact reconstruction validates a table; even
that would not identify the meaning of its keys or the final puzzle outlier.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.nachtlorn_running_book_probe import OPERATIONS, transform  # noqa: E402

FIELDS = (("count", 7, 32), ("key", 14, 64), ("checksum", 7, 32))
LAYOUTS = ("interleaved", "field-major")
KEYS = ("BLOOM", "GLOOM", "WLOOM")
MAX_COUNT = 1_000_000
MASK = (1 << 32) - 1


def murmur32(data: bytes, seed: int = 0) -> int:
    def rotate(value, bits):
        return ((value << bits) | (value >> (32 - bits))) & MASK

    def mix(value):
        return (rotate((value * 0xcc9e2d51) & MASK, 15) * 0x1b873593) & MASK

    h = seed & MASK
    end = len(data) - len(data) % 4
    for offset in range(0, end, 4):
        h ^= mix(int.from_bytes(data[offset:offset + 4], "little"))
        h = (rotate(h, 13) * 5 + 0xe6546b64) & MASK
    if end < len(data):
        h ^= mix(int.from_bytes(data[end:], "little"))
    h ^= len(data)
    h ^= h >> 16
    h = (h * 0x85ebca6b) & MASK
    h ^= h >> 13
    h = (h * 0xc2b2ae35) & MASK
    return (h ^ (h >> 16)) & MASK


def checksum(key: int) -> int:
    return murmur32(key.to_bytes(8, "little"), 11)


def positions(key: int, cells: int) -> list[int]:
    if cells < 4 or cells % 4:
        raise ValueError("positive four-partition table required")
    size, raw = cells // 4, key.to_bytes(8, "little")
    return [part * size + murmur32(raw, part) % size for part in range(4)]


def build_table(items: list[tuple[int, int]], cells: int) -> list[list[int]]:
    if cells < 4 or cells % 4:
        raise ValueError("positive four-partition table required")
    table = [[0, 0, 0] for _ in range(cells)]
    for key, sign in items:
        if not 0 <= key < 1 << 64 or sign not in (-1, 1):
            raise ValueError("uint64 key and +/-1 sign required")
        for index in positions(key, cells):
            table[index][0] += sign
            table[index][1] ^= key
            table[index][2] ^= checksum(key)
    return table


def validate_table(table: list[list[int]]) -> dict:
    cells = len(table)
    if cells < 4 or cells % 4 or any(len(row) != 3 for row in table):
        return {"valid": False, "reason": "dimensions"}
    if any(not -(1 << 31) <= c < 1 << 31 or not 0 <= k < 1 << 64 or not 0 <= h < 1 << 32
           for c, k, h in table):
        return {"valid": False, "reason": "field_ranges"}
    remaining, recovered = [row[:] for row in table], {}

    def pure(index):
        count, key, check = remaining[index]
        return abs(count) == 1 and checksum(key) == check

    queue = deque(i for i in range(cells) if pure(i))
    while queue:
        index = queue.popleft()
        if not pure(index):
            continue
        sign, key, check = remaining[index]
        buckets = positions(key, cells)
        if index not in buckets:
            return {"valid": False, "reason": "pure_cell_wrong_bucket"}
        if key in recovered or len(recovered) >= cells:
            return {"valid": False, "reason": "duplicate_or_overload"}
        recovered[key] = sign
        for bucket in buckets:
            remaining[bucket][0] -= sign
            remaining[bucket][1] ^= key
            remaining[bucket][2] ^= check
            if pure(bucket):
                queue.append(bucket)
    residual = sum(any(row) for row in remaining)
    if residual:
        return {"valid": False, "reason": "nonempty_residual", "residual_cells": residual,
                "peeled_keys": len(recovered)}
    items = sorted(recovered.items())
    if build_table(items, cells) != table:
        return {"valid": False, "reason": "forward_mismatch"}
    return {"valid": True, "cells": cells, "empty": not items,
            "items": [{"key_uint64": key, "sign": sign} for key, sign in items],
            "exact_table_reconstruction": True,
            "caution": "Numeric-key table only; no key meanings or puzzle outlier assigned."}


def encode_number(value: int, width: int) -> str:
    if value < 0 or width < 1:
        raise ValueError("nonnegative number and positive width required")
    letters = []
    for _ in range(width):
        value, digit = divmod(value, 26)
        letters.append(chr(65 + digit))
    if value:
        raise ValueError("number exceeds letter width")
    return "".join(reversed(letters))


def encode_table(table: list[list[int]], layout: str) -> str:
    if layout not in LAYOUTS:
        raise ValueError("registered layout required")
    if any(len(row) != 3 for row in table):
        raise ValueError("three fields per row required")
    if any(not -(1 << 31) <= c < 1 << 31 or not 0 <= k < 1 << 64 or not 0 <= h < 1 << 32
           for c, k, h in table):
        raise ValueError("field outside declared bit width")
    fields = [[encode_number(c % (1 << 32), 7), encode_number(k, 14), encode_number(h, 7)]
              for c, k, h in table]
    if layout == "interleaved":
        return "".join(part for row in fields for part in row)
    return "".join(row[column] for column in range(3) for row in fields)


def inspect_fields(text: str, layout: str) -> dict:
    if not re.fullmatch(r"[A-Z]+", text) or layout not in LAYOUTS:
        raise ValueError("literal uppercase text and registered layout required")
    cells, remainder = divmod(len(text), 28)
    if remainder or cells < 4 or cells % 4:
        return {"status": "incompatible_dimensions", "letters": len(text), "complete_cells": cells,
                "remainder_letters": remainder}
    overflows, count_violations, rows, exact = dict.fromkeys((f[0] for f in FIELDS), 0), 0, [], True
    for cell in range(cells):
        row, field_offset, array_offset = [], 0, 0
        for name, width, bits in FIELDS:
            start = cell * 28 + field_offset if layout == "interleaved" else array_offset + cell * width
            block = text[start:start + width]
            value = 0
            for character in block:
                value = value * 26 + ord(character) - 65
            exact = exact and encode_number(value, width) == block
            if value >= 1 << bits:
                overflows[name] += 1
            if name == "count" and value < 1 << 32:
                value = value if value < 1 << 31 else value - (1 << 32)
                count_violations += abs(value) > MAX_COUNT
            row.append(value)
            field_offset += width
            array_offset += cells * width
        rows.append(row)
    if not exact:
        raise ValueError("field-number roundtrip failure")
    result = {"status": "field_constraints_failed", "cells": cells, "unsigned_overflow_fields": overflows,
              "out_of_bound_signed_counts": count_violations, "exact_numeric_letter_roundtrip": exact}
    if not any(overflows.values()) and not count_violations:
        validation = validate_table(rows)
        result.update(status="validated_table" if validation["valid"] else "table_validation_failed",
                      table_validation=validation)
        if validation["valid"]:
            result["exact_wire_reconstruction"] = encode_table(rows, layout) == text
            if not result["exact_wire_reconstruction"]:
                raise ValueError("wire roundtrip failure")
    return result


def letter_paths(stream: str):
    if not re.fullmatch(r"[A-Z]+", stream) or len(stream) < 2:
        raise ValueError("literal uppercase source required")
    for marker in (False, True):
        if marker and not stream.endswith("I"):
            continue
        text = stream[:-1] if marker else stream
        yield {"drop_final_i": marker, "operation": "identity", "exact_letter_roundtrip": True}, text
        for key in KEYS:
            expanded = (key * ((len(text) + len(key) - 1) // len(key)))[:len(text)]
            for kind in OPERATIONS:
                decoded = transform(text, expanded, kind)
                exact = (transform(decoded, expanded, kind, inverse=True) + ("I" if marker else "")) == stream
                if not exact:
                    raise ValueError("letter roundtrip failure")
                yield {"drop_final_i": marker, "operation": kind, "key": key, "phase": 0,
                       "exact_letter_roundtrip": exact}, decoded


def scan(stream: str) -> dict:
    records = [{**path, "layout": layout, **inspect_fields(text, layout)}
               for path, text in letter_paths(stream) for layout in LAYOUTS]
    return {"hypothesis": "R8", "source_letters": len(stream),
            "letter_sha256": hashlib.sha256(stream.encode()).hexdigest(),
            "parameters": {"fields": [list(f) for f in FIELDS], "layouts": list(LAYOUTS),
                           "digit_convention": "A0", "letter_order": "most-significant first",
                           "signed_count": "two's complement32", "max_absolute_count": MAX_COUNT,
                           "hash_partitions": 4, "checksum_seed": 11, "values_bytes": 0},
            "configurations": len(records), "records": records,
            "validated_tables": [r for r in records if r["status"] == "validated_table"],
            "caution": "Hypothetical wire format, not an author-attributed or reference serializer. Divisibility and roundtrips alone do not validate plaintext. Numeric keys still require independent interpretation and an outlier rule."}


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
    print(json.dumps({"configurations": report["configurations"], "validated_tables": len(report["validated_tables"]),
                      "status_counts": {status: sum(r["status"] == status for r in report["records"])
                                        for status in sorted({r["status"] for r in report["records"]})}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
