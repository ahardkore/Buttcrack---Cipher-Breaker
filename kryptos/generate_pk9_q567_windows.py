#!/usr/bin/env python3
"""Generate exact fixed-length source windows for the PK9 Q567/T8 crib test."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERIFIED = ROOT / "pk_verified_solutions.json"
THEOPHILUS = ROOT / "theophilus_book3_english.txt"


def normalize(text: str) -> str:
    return "".join(re.findall(r"[A-Z]", text.upper()))


def windows(documents: list[str], length: int) -> list[str]:
    result: set[str] = set()
    for document in documents:
        stream = normalize(document)
        result.update(stream[i : i + length] for i in range(len(stream) - length + 1))
    return sorted(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--length", type=int, default=18, choices=range(16, 65), metavar="N")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--theophilus", action="store_true", help="use the local Book III corpus")
    source.add_argument(
        "--verified",
        nargs="+",
        choices=[f"PK{i}" for i in range(1, 9)],
        metavar="PKN",
        help="use selected verified Paradigm plaintexts",
    )
    args = parser.parse_args()

    if args.theophilus:
        documents = [THEOPHILUS.read_text(errors="ignore")]
        label = str(THEOPHILUS.relative_to(ROOT.parent))
    else:
        data = json.loads(VERIFIED.read_text())
        documents = [data[name]["plaintext"] for name in args.verified]
        label = ",".join(args.verified)

    values = windows(documents, args.length)
    args.output.write_text("\n".join(values) + "\n")
    print(f"wrote {len(values):,} unique {args.length}-letter windows from {label} to {args.output}")


if __name__ == "__main__":
    main()
