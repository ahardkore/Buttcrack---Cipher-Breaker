#!/usr/bin/env python3
"""Answer-blind role checks: pinned reference facts and bounded Bloom containers.

This does not guess an answer or query a candidate-word dictionary. Raw schemas
are checked without selecting a cipher, password, route, or hidden byte offset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path

FILTER = struct.Struct("<dQQQQ")
SCALABLE = struct.Struct("<idQd")
MAX_BITS = 8 * 1024 * 1024
MAX_SLICES = 64
MAX_CHILDREN = 64
QUERIES = {"blue": r"blue", "bowl": r"bowl\w*", "stairs": r"stair\w*",
           "laughter": r"laugh\w*", "morning": r"morning"}


def inspect_filter(data: bytes) -> dict | None:
    if len(data) < FILTER.size:
        return None
    error, slices, bits_per_slice, capacity, count = FILTER.unpack_from(data)
    if (not math.isfinite(error) or not 2.0 ** -MAX_SLICES <= error < 1
            or not 1 <= slices <= MAX_SLICES or not capacity or count > capacity
            or not bits_per_slice or slices * bits_per_slice > MAX_BITS):
        return None
    expected_slices = int(math.ceil(math.log(1.0 / error, 2)))
    expected_bits = int(math.ceil(capacity * abs(math.log(error)) / (slices * math.log(2) ** 2)))
    bits = slices * bits_per_slice
    if slices != expected_slices or bits_per_slice != expected_bits or len(data) != FILTER.size + (bits + 7) // 8:
        return None
    payload = data[FILTER.size:]
    if bits % 8 and payload[-1] >> (bits % 8):
        return None
    return {"format": "pybloom-filter-candidate", "error_rate": error, "slices": slices,
            "bits_per_slice": bits_per_slice, "capacity": capacity, "count": count,
            "bits": bits, "set_bits": sum(v.bit_count() for v in payload),
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "scope": "Container structure only; no item set or outlier has been recovered."}


def inspect_scalable(data: bytes) -> dict | None:
    if len(data) < SCALABLE.size + 4:
        return None
    scale, ratio, capacity, error = SCALABLE.unpack_from(data)
    if (scale not in (2, 4) or not math.isfinite(ratio) or not 0 < ratio < 1
            or not capacity or not math.isfinite(error) or not 0 < error < 1):
        return None
    count, = struct.unpack_from("<l", data, SCALABLE.size)
    if not 0 <= count <= MAX_CHILDREN or len(data) < SCALABLE.size + 4 + 8 * count:
        return None
    sizes = struct.unpack_from("<" + "Q" * count, data, SCALABLE.size + 4)
    offset = SCALABLE.size + 4 + 8 * count
    if sum(sizes) != len(data) - offset:
        return None
    children = []
    for size in sizes:
        if not FILTER.size <= size <= FILTER.size + MAX_BITS // 8:
            return None
        child = inspect_filter(data[offset:offset + size])
        if child is None:
            return None
        children.append(child)
        offset += size
    return {"format": "pybloom-scalable-candidate", "scale": scale, "ratio": ratio,
            "initial_capacity": capacity, "error_rate": error, "children": children,
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "scope": "Container structure only; no item set or outlier has been recovered."}


def decode26(stream: str, bias: int) -> bytes:
    if not re.fullmatch(r"[A-Z]+", stream) or bias not in (0, 1):
        raise ValueError("literal uppercase letters and bias zero/one required")
    digits = stream.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "0123456789abcdefghijklmnop"))
    value = 0
    for start in range(0, len(digits), 512):
        block = digits[start:start + 512]
        value = value * 26 ** len(block) + int(block, 26)
    if bias:
        value += (26 ** len(stream) - 1) // 25
    return value.to_bytes(max(1, (value.bit_length() + 7) // 8), "big")


def scan_containers(stream: str) -> dict:
    seen, candidates = set(), []
    trials = 0
    for remove_marker in (False, True):
        if remove_marker and not stream.endswith("I"):
            continue
        text = stream[:-1] if remove_marker else stream
        for bias in (0, 1):
            big = decode26(text, bias)
            for order, minimal in (("big", big), ("little", big[::-1])):
                for zeros in range(8):
                    data = b"\0" * zeros + minimal if order == "big" else minimal + b"\0" * zeros
                    trials += 1
                    digest = hashlib.sha256(data).digest()
                    if digest in seen:
                        continue
                    seen.add(digest)
                    for parser in (inspect_filter, inspect_scalable):
                        result = parser(data)
                        if result is not None:
                            candidates.append({"drop_final_i": remove_marker, "retained_letters": len(text),
                                               "bias": bias, "byteorder": order, "restored_zero_bytes": zeros,
                                               "container": result})
    return {"representation_configurations": trials, "unique_buffers": len(seen),
            "candidates": candidates, "filter_header_bytes": FILTER.size,
            "scalable_header_bytes": SCALABLE.size, "schema_checks_per_buffer": 2,
            "caution": "Only unmasked whole-base26 A0/A1, both byte orders, optional terminal I, and 0..7 lost zero bytes. No cipher or password is assumed."}


def book_facts(raw: bytes, poem: list[str]) -> dict:
    text = raw.decode("utf-8-sig").replace("\r\n", "\n")
    title = re.search(r"^Title:\s*(.+)$", text, re.M)
    author = re.search(r"^Author:\s*(.+)$", text, re.M)
    number = re.search(r"\[EBook #(\d+)\]", text)
    start = text.find("Stately, plump Buck Mulligan")
    if start < 0:
        raise ValueError("expected the pinned reference's Stately opening")
    end = re.search(r"^\[\s*2\s*\]", text[start:], re.M)
    if end is None:
        raise ValueError("expected the next numbered episode boundary")
    opening = text[start:start + end.start()]
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", opening)]
    matches = {name: [i for i, w in enumerate(words) if re.fullmatch(pattern, w)]
               for name, pattern in QUERIES.items()}
    normalized = " ".join(opening.lower().split())
    return {"reference_sha256": hashlib.sha256(raw).hexdigest(), "reference_bytes": len(raw),
            "title": title.group(1).strip() if title else None,
            "author": author.group(1).strip() if author else None,
            "gutenberg_id": int(number.group(1)) if number else None,
            "episode": 1, "ascii_word_tokens": len(words),
            "fixed_query_token_positions": matches,
            "literal_poem_line_matches_in_episode": [" ".join(line.lower().split()) in normalized for line in poem],
            "opening_excerpt": " ".join(opening[:opening.find('—Introibo')].split()),
            "caution": "Exploratory consistency audit, not a held-out or significance test. Neither literary populations nor a body cipher follow from these facts."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--book", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.path.resolve(), args.book.resolve()):
        parser.error("output must not overwrite either input")
    raw = args.path.read_bytes()
    lines = raw.decode("ascii").splitlines()
    if len(lines) < 9 or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in lines[8:]):
        parser.error("expected original source layout")
    stream = "".join(c for row in lines[8:] for c in row if "A" <= c <= "Z")
    report = {"status": "Role assessment only; no recovered answer.",
              "source_sha256": hashlib.sha256(raw).hexdigest(),
              "reference": book_facts(args.book.read_bytes(), lines[:5]),
              "named_construction": scan_containers(stream)}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"reference": report["reference"]["title"],
                      "representation_configurations": report["named_construction"]["representation_configurations"],
                      "container_candidates": len(report["named_construction"]["candidates"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
