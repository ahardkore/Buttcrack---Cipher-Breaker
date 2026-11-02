#!/usr/bin/env python3
"""Exact paired-indel lower bound for R18's hypothetical raw key64 fields."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

CELL_COUNT = 312
PROFILES = (("cell_interleaved", 28), ("field_major", 14))


def leading_capacity(bits: int, width: int, bias: int) -> int:
    if bits < 1 or width < 1 or bias not in (0, 1):
        raise ValueError("invalid field")
    place = 26 ** (width - 1)
    minimum_bias = bias * ((26 ** width - 1) // 25)
    return min(26, max(0, ((2 ** bits - 1 - minimum_bias) // place) + 1))


def longest_run(text: str, stride: int, capacity: int) -> dict:
    """Maximum stride-spaced source run using at most capacity distinct glyphs."""
    if not text or not re.fullmatch(r"[A-Z]+", text) or stride < 1 or not 1 <= capacity <= 26:
        raise ValueError("uppercase text, positive stride, capacity 1..26 required")
    best = {"length": 0, "source_start": None, "source_end": None, "distinct_glyphs": ""}
    for residue in range(min(stride, len(text))):
        row = text[residue::stride]
        counts = Counter()
        start = 0
        for end, glyph in enumerate(row):
            counts[glyph] += 1
            while len(counts) > capacity:
                old = row[start]
                counts[old] -= 1
                if counts[old] == 0:
                    del counts[old]
                start += 1
            if end - start + 1 > best["length"]:
                best = {"length": end - start + 1, "source_start": residue + start * stride,
                        "source_end": residue + end * stride,
                        "distinct_glyphs": "".join(sorted(counts))}
    return best


def verify_certificate(text: str, stride: int, capacity: int, certificate: dict) -> bool:
    """Replay the witness and upper bound; reject altered or malformed records."""
    try:
        start, end, length = (certificate[key] for key in ("source_start", "source_end", "length"))
        if (type(start) is not int or type(end) is not int or type(length) is not int
                or start < 0 or end >= len(text) or end < start or stride < 1
                or (end - start) % stride):
            return False
        witness = text[start:end + 1:stride]
        return (len(witness) == length and len(set(witness)) <= capacity
                and ''.join(sorted(set(witness))) == certificate['distinct_glyphs']
                and length == longest_run(text, stride, capacity)['length'])
    except (KeyError, TypeError, ValueError):
        return False


def minimum_pairs(leader_count: int, run_bound: int) -> int:
    if leader_count < 1 or run_bound < 1:
        raise ValueError("positive counts required")
    # N - m <= (2m + 1) R; only a necessary condition.
    return max(0, (leader_count - run_bound + (2 * run_bound)) // (2 * run_bound + 1))


def analyze(text: str) -> dict:
    if len(text) != CELL_COUNT * 28:
        raise ValueError("R20 requires the full 312-cell body")
    profiles = []
    for layout, stride in PROFILES:
        for bias in (0, 1):
            capacity = leading_capacity(64, 14, bias)
            certificate = longest_run(text, stride, capacity)
            bound = minimum_pairs(CELL_COUNT, certificate["length"])
            profiles.append({"layout": layout, "source_stride": stride, "bias": bias,
                             "leading_capacity": capacity, "longest_source_run": certificate,
                             "necessary_minimum_paired_edits": bound,
                             "single_pair_excluded": bound > 1})
    return {"hypothesis": "R20", "source_letters": len(text), "target_key_fields": CELL_COUNT,
            "source_letter_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "profiles": profiles,
            "inequality": "312 - m <= (2*m + 1) * R is necessary",
            "explanation": "At most m target key leaders are inserted. The remaining leaders occur in at most 2m+1 constant-displacement source runs, each a consecutive stride-spaced run with at most capacity glyphs. Each insertion/deletion introduces at most one boundary. Each source run has length <= R.",
            "scope": "Necessary capacity only; not an IBLT decoding. Paired arbitrary source-letter insertions/deletions, exact R18 raw key fields and fixed bijective alphabet. Other transforms and representations remain open."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        parser.error("output must not overwrite source")
    raw = args.path.read_bytes()
    rows = raw.decode("ascii").splitlines()[8:]
    if not rows or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in rows):
        parser.error("expected original ASCII body after eight-line preamble")
    stream = "".join(c for row in rows for c in row if "A" <= c <= "Z")
    result = analyze(stream)
    result["source_sha256"] = hashlib.sha256(raw).hexdigest()
    result["source_bytes"] = len(raw)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["profiles"]))


if __name__ == "__main__":
    main()
