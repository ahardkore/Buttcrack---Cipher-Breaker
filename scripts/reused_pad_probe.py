#!/usr/bin/env python3
"""Read-only likelihood screen for two aligned texts sharing a modular pad.

A sum cancels opposite-sign pads; a difference cancels same-sign pads. Fit an
unknown Caesar shift in each phase to the distribution expected from two English
letters. This is a construction screen, not plaintext recovery or a p-value.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

ENGLISH_WEIGHTS = (
    8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966,
    .153, .772, 4.025, 2.406, 6.749, 7.507, 1.929, .095, 5.987, 6.327,
    9.056, 2.758, .978, 2.360, .150, 1.974, .074,
)
UPPERCASE_ROW = re.compile(r" *[A-Z]+(?: +[A-Z]+)* *")
CAUTION = (
    "English-frequency construction screen only; not recovered plaintext or a "
    "solution probability. Fitted phases and overlapping pairs require "
    "multiple-testing/dependence caution. Input file unchanged."
)


def pair_likelihoods(first: str, second: str, phases: int = 5) -> dict:
    """Fit phase-local shifts to both modular sum/difference distributions.

    Strings must be equal-length uppercase ASCII. Phases start at the beginning
    of these supplied windows. Scores are natural-log likelihood ratios against
    uniform modular differences/sums, not calibrated significance estimates.
    """
    if not re.fullmatch(r"[A-Z]+", first) or not re.fullmatch(r"[A-Z]+", second):
        raise ValueError("both windows must contain only uppercase ASCII letters")
    if len(first) != len(second):
        raise ValueError("aligned windows must have equal lengths")
    if not 1 <= phases <= len(first):
        raise ValueError("phases must be between 1 and the number of pairs")
    weight = sum(ENGLISH_WEIGHTS)
    frequencies = [x / weight for x in ENGLISH_WEIGHTS]
    results = {}
    for operation in ("difference", "sum"):
        expected = [
            sum(frequencies[a] * frequencies[
                (a - d) % 26 if operation == "difference" else (d - a) % 26
            ] for a in range(26))
            for d in range(26)
        ]
        counts = [[0] * 26 for _ in range(phases)]
        for i, (a, b) in enumerate(zip(first, second)):
            value = ord(a) - ord(b) if operation == "difference" else ord(a) + ord(b) - 130
            counts[i % phases][value % 26] += 1
        shifts, scores = [], []
        for row in counts:
            options = [sum(n * math.log(26 * expected[(d - shift) % 26])
                           for d, n in enumerate(row)) for shift in range(26)]
            shift = max(range(26), key=options.__getitem__)
            shifts.append(shift)
            scores.append(options[shift])
        results[operation] = {
            "log_likelihood_ratio": sum(scores),
            "fitted_phase_shifts": shifts,
            "phase_scores": scores,
            "modular_counts": counts,
        }
    return {"pairs": len(first), "phases": phases, "results": results, "caution": CAUTION}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--first-start", type=int, default=0, help="zero-based letter offset")
    parser.add_argument("--second-start", type=int, required=True, help="zero-based letter offset")
    parser.add_argument("--pairs", type=int, required=True)
    parser.add_argument("--phases", type=int, default=5)
    parser.add_argument("--body-start", type=int, metavar="LINE",
                        help="one-based body line; otherwise select grouped uppercase rows")
    args = parser.parse_args(argv)
    if args.first_start < 0 or args.second_start < 0:
        parser.error("window offsets must be nonnegative")
    if args.pairs < 1 or not 1 <= args.phases <= args.pairs:
        parser.error("require pairs >= 1 and 1 <= phases <= pairs")
    if args.body_start is not None and args.body_start < 1:
        parser.error("--body-start must be at least 1")
    try:
        lines = args.path.read_text(encoding="utf-8").splitlines()
        if args.body_start is None:
            body = [line for line in lines
                    if UPPERCASE_ROW.fullmatch(line) and len(line.split()) > 1]
        else:
            body = lines[args.body_start - 1:]
            if any(not UPPERCASE_ROW.fullmatch(line) for line in body):
                raise ValueError("explicit body contains a non-uppercase ciphertext row")
        stream = "".join(c for line in body for c in line if "A" <= c <= "Z")
        if max(args.first_start, args.second_start) + args.pairs > len(stream):
            raise ValueError("requested window extends beyond the letter stream")
        report = pair_likelihoods(
            stream[args.first_start:args.first_start + args.pairs],
            stream[args.second_start:args.second_start + args.pairs], args.phases,
        )
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    report.update({"first_start": args.first_start, "second_start": args.second_start})
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
