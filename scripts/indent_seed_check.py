#!/usr/bin/env python3
"""Verify a supplied Python Random seed against literal leading-space counts.

An exact match identifies a reproducible layout generator, not plaintext, the
only possible seed, or proof that the layout has no further purpose. No seed
search is performed and the input is never modified.

Example: python3 scripts/indent_seed_check.py transcript.txt --seed 4300 --body-start 9
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

UPPERCASE_ROW = re.compile(r" *[A-Z]+(?: +[A-Z]+)* *")


def check_indent_seed(body: list[str], seed: int, width: int = 8) -> dict:
    """Compare every supplied row to consecutive native ``randrange(width)`` draws.

    Row numbers are one-based within ``body``. Only literal ASCII spaces count;
    other leading whitespace is rejected rather than silently normalized.
    A local RNG leaves the caller's global random state unchanged.
    """
    if not body:
        raise ValueError("at least one body row is required")
    if width < 1:
        raise ValueError("width must be at least 1")
    observed = []
    for number, row in enumerate(body, 1):
        leading = row[: len(row) - len(row.lstrip())]
        if any(char != " " for char in leading):
            raise ValueError(f"row {number} has non-space leading whitespace")
        observed.append(len(row) - len(row.lstrip(" ")))
    rng = random.Random(seed)
    predicted = [rng.randrange(width) for _ in body]
    mismatches = [
        {"body_row": number, "observed": actual, "predicted": expected}
        for number, (actual, expected) in enumerate(zip(observed, predicted), 1)
        if actual != expected
    ]
    return {
        "seed": seed,
        "algorithm": f"random.Random(seed).randrange({width})",
        "rows": len(body),
        "matches": len(body) - len(mismatches),
        "exact_match": not mismatches,
        "observed": observed,
        "predicted": predicted,
        "mismatches": mismatches,
        "caution": "A layout-generator match, not recovered plaintext or proof of seed uniqueness.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path, help="unaltered UTF-8 transcript")
    parser.add_argument("--seed", required=True, type=int, help="integer seed to verify")
    parser.add_argument("--width", type=int, default=8, help="exclusive randrange bound (default 8)")
    parser.add_argument("--body-start", type=int, metavar="LINE",
                        help="first body line, one-based; otherwise select all-uppercase rows")
    args = parser.parse_args(argv)
    if args.width < 1:
        parser.error("--width must be at least 1")
    if args.body_start is not None and args.body_start < 1:
        parser.error("--body-start must be at least 1")
    try:
        lines = args.path.read_text(encoding="utf-8").splitlines()
        if args.body_start is None:
            body = [line for line in lines if UPPERCASE_ROW.fullmatch(line)]
        else:
            body = lines[args.body_start - 1:]
        result = check_indent_seed(body, args.seed, args.width)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))
    return 0 if result["exact_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
