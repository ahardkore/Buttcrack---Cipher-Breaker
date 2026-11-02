#!/usr/bin/env python3
"""Reproduce the existing hypothetical final-I-zero vertical-strip counts.

One original row is one strip. For counterclockwise rotation, letters in larger
original columns are above the guide. Spaces establish columns but are not
counted as letters. The final I is an assumed guide, not an established clue.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

BODY = re.compile(r" *[A-Z]+(?: +[A-Z]+)* *")


def parse_rows(raw: bytes) -> list[str]:
    lines = raw.decode("ascii").splitlines()
    if len(lines) < 9 or any(not BODY.fullmatch(line) for line in lines[8:]):
        raise ValueError("expected eight-line preamble and original ASCII body")
    return lines[8:]


def summarize_ranges(records: list[dict]) -> dict:
    """Describe exact per-row count pairs and ties, without selecting a cutoff."""
    if not records:
        raise ValueError("at least one row required")
    pairs = Counter((r["below"], r["above"]) for r in records)
    minimum = min(r["above"] for r in records)
    maximum = max(r["above"] for r in records)
    return {"distinct_count_ranges": len(pairs),
            "unique_count_range_rows": [r["body_row"] for r in records if pairs[(r["below"], r["above"])] == 1],
            "above_minimum": minimum,
            "above_minimum_rows": [r["body_row"] for r in records if r["above"] == minimum],
            "above_maximum": maximum,
            "above_maximum_rows": [r["body_row"] for r in records if r["above"] == maximum]}


def count_strips(rows: list[str]) -> dict:
    if not rows or any(not BODY.fullmatch(row) for row in rows):
        raise ValueError("nonempty uppercase rows with literal spaces required")
    last = rows[-1].rstrip(" ")
    if not last.endswith("I"):
        raise ValueError("the hypothetical final-I guide requires a terminal I")
    zero = len(last) - 1
    records = []
    for index, row in enumerate(rows, 1):
        positions = [i for i, char in enumerate(row) if "A" <= char <= "Z"]
        below = sum(pos < zero for pos in positions)
        on = sum(pos == zero for pos in positions)
        above = sum(pos > zero for pos in positions)
        records.append({"body_row": index, "indent": len(row) - len(row.lstrip(" ")),
                        "letters": len(positions), "below": below, "on": on, "above": above,
                        "signed_range": [-below, above]})
    patterns = Counter((r["indent"], r["below"], r["on"], r["above"]) for r in records[:-1])
    return {"status": "Descriptive reproduction only; final I = zero is a user hypothesis, not a solution.",
            "axis": {"guide": "column of final printed I", "zero_based_source_column": zero,
                     "rotation": "counterclockwise", "above": "larger source column",
                     "below": "smaller source column", "on_zero": "excluded from both counts",
                     "spaces": "preserved as physical columns, never counted as letters"},
            "rows": records,
            "range_summary_all_rows": summarize_ranges(records),
            "range_summary_nonfinal_rows": summarize_ranges(records[:-1]) if len(records) > 1 else None,
            "nonfinal_pattern_counts": [{"indent": k[0], "below": k[1], "on": k[2], "above": k[3], "rows": n}
                                        for k, n in sorted(patterns.items())],
            "interpretation": "No statistical fence or answer rule is selected here. The short final row is a known layout fact, not an independently recovered final-layer outlier."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        parser.error("output must not overwrite source")
    try:
        raw = args.path.read_bytes()
        report = count_strips(parse_rows(raw))
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    report["source_bytes"] = len(raw)
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(report["rows"]), "guide_column": report["axis"]["zero_based_source_column"],
                      "final_row": report["rows"][-1], "nonfinal_patterns": report["nonfinal_pattern_counts"]}))


if __name__ == "__main__":
    main()
