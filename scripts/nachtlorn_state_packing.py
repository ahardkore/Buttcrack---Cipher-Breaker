#!/usr/bin/env python3
"""Necessary-condition test for 32/64-bit objects encoded as base-26 blocks.

8736 = 1248*7 = 624*14 suggests a packed-integer hypothesis, not a conclusion.
Unknown five-phase alphabets are allowed. Capacity violations are minimized over
all possible leading-symbol subsets; no English score or chosen word is used.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.nachtlorn_clue_ledger import vigenere  # noqa: E402


def leading_capacity(text: str, width: int, bits: int, alignment: int = 0,
                     order: str = "big", phases: int = 5) -> dict:
    """Lower bound on symbol replacements needed for the leading-digit bound.

    Each complete block can contribute at most one such violation. Five unknown
    bijective digit alphabets cannot expand a K-symbol permitted leading set.
    Choosing each phase's K most frequent symbols gives the exact relaxed bound.
    This condition is necessary, not sufficient, for uint32/uint64 recovery.
    """
    if (width < 1 or bits < 1 or phases < 1 or not 0 <= alignment < width or
            order not in ("big", "little") or not re.fullmatch(r"[A-Z]+", text)):
        raise ValueError("invalid capacity parameters or nonliteral text")
    allowed = min(26, ((1 << bits) - 1) // (26 ** (width - 1)) + 1)
    counts = [Counter() for _ in range(phases)]
    blocks = 0
    for start in range(alignment, len(text) - width + 1, width):
        position = start + (0 if order == "big" else width - 1)
        counts[position % phases][text[position]] += 1
        blocks += 1
    edits = sum(sum(c.values()) - sum(n for _, n in c.most_common(allowed)) for c in counts)
    return {"width": width, "bits": bits, "alignment": alignment, "order": order,
            "complete_blocks": blocks, "permitted_leading_symbols": allowed,
            "distinct_symbols_by_phase": [len(c) for c in counts],
            "minimum_leading_symbol_replacements": edits}


def permutation(length: int, unit: int, indent_draws: int) -> list[int]:
    if length < 1 or unit < 1 or indent_draws < 0:
        raise ValueError("invalid permutation parameters")
    rng = random.Random(4300)
    for _ in range(indent_draws):
        rng.randrange(8)
    indices = list(range((length + unit - 1) // unit))
    rng.shuffle(indices)
    return indices


def permute(text: str, unit: int, indices: list[int], *, inverse: bool = False) -> str:
    """Invert ragged-unit shuffles using each original unit's known length.

    A short final unit may move into the middle. Splitting the shuffled stream
    at uniform widths would therefore be an incorrect inverse.
    """
    if unit < 1:
        raise ValueError("unit must be positive")
    lengths = [min(unit, len(text) - i) for i in range(0, len(text), unit)]
    if sorted(indices) != list(range(len(lengths))):
        raise ValueError("indices must permute all units exactly once")
    if not inverse:
        chunks = [text[i:i + unit] for i in range(0, len(text), unit)]
        return "".join(chunks[i] for i in indices)
    chunks = [""] * len(indices)
    cursor = 0
    for original in indices:
        count = lengths[original]
        chunks[original] = text[cursor:cursor + count]
        cursor += count
    return "".join(chunks)


def scan(text: str) -> dict:
    if not re.fullmatch(r"[A-Z]+", text):
        raise ValueError("text must contain uppercase ASCII letters only")
    routes = []
    for draws in (0, 145, 146):
        for unit in (1, 5, 7, 14, 60):
            indices = permutation(len(text), unit, draws)
            for inverse in (False, True):
                routes.append((draws, unit, indices, inverse))
    best = []
    audit_digest = hashlib.sha256()
    minimum_by_width = {7: None, 14: None}
    readings = capacity_cases = single_exception_candidates = 0
    for key in (None, "BLOOM", "BLPNM", "BLNPM"):
        decoded = vigenere(text, key) if key else text
        variants = [(decoded, {"route": "identity", "pre_key": key}),
                    (decoded[::-1], {"route": "reverse", "pre_key": key})]
        variants.extend((permute(decoded, unit, indices, inverse=inverse),
                         {"route": "inverse-shuffle" if inverse else "shuffle",
                          "unit": unit, "seed": 4300, "indent_draws": draws, "pre_key": key})
                        for draws, unit, indices, inverse in routes)
        for value, spec in variants:
            readings += 1
            for width, bits in ((7, 32), (14, 64)):
                for alignment in range(width):
                    for order in ("big", "little"):
                        result = leading_capacity(value, width, bits, alignment, order)
                        capacity_cases += 1
                        audit_digest.update((json.dumps({**spec, **result}, sort_keys=True,
                                                       separators=(",", ":")) + "\n").encode())
                        loss = result["minimum_leading_symbol_replacements"]
                        if minimum_by_width[width] is None or loss < minimum_by_width[width]:
                            minimum_by_width[width] = loss
                        if result["minimum_leading_symbol_replacements"] <= 1:
                            single_exception_candidates += 1
                        best.append({**spec, **result})
            best = heapq.nsmallest(12, best,
                                  key=lambda r: r["minimum_leading_symbol_replacements"])
    return {
        "status": "Necessary-condition construction test; no English gate or semantic answer.",
        "letters": len(text), "letter_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "readings": readings, "capacity_cases": capacity_cases,
        "capacity_case_sha256": audit_digest.hexdigest(),
        "minimum_by_width": minimum_by_width,
        "single_exception_candidates": single_exception_candidates, "best_cases": best,
        "specification": {"packed_objects": [{"width": 7, "bits": 32}, {"width": 14, "bits": 64}],
                          "phase_alphabets": 5, "all_block_alignments": True,
                          "digit_orders": ["big", "little"],
                          "pre_keys": [None, "BLOOM", "BLPNM", "BLNPM"],
                          "routes": ["identity", "reverse", "shuffle", "inverse-shuffle"],
                          "shuffle_seed": 4300, "shuffle_units": [1, 5, 7, 14, 60],
                          "shuffle_after_indent_draws": [0, 145, 146]},
        "caution": "Unknown transpositions, longer/changing alphabets, other integer encodings and insertion/deletion shifts remain outside this test.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.output and args.output.resolve() == args.path.resolve():
        parser.error("output must not overwrite source")
    try:
        raw = args.path.read_bytes()
        body = raw.decode("ascii").splitlines()[8:]
        if not body or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in body):
            raise ValueError("expected original uppercase body beginning on line9")
        text = "".join(c for row in body for c in row if "A" <= c <= "Z")
        report = scan(text)
        report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError, UnicodeError) as error:
        parser.error(str(error))
    serialized = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized)
        print(json.dumps({"readings": report["readings"], "capacity_cases": report["capacity_cases"],
                          "single_exception_candidates": report["single_exception_candidates"],
                          "minimum_symbol_edits": report["best_cases"][0]["minimum_leading_symbol_replacements"]}))
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
