#!/usr/bin/env python3
"""Generate PK9 openings from sentence patterns observed in verified PK8.

Unlike the semantic continuation lists, this corpus models PK8's syntax:
first-person present tense, temporal complements, subordinate BEFORE/AFTER
clauses, and BUT/AND pivots. The grammar independently generates PK8's real
20-letter opening, providing a limited positive calibration for coverage.
"""

from __future__ import annotations

import argparse
import re
from itertools import product
from pathlib import Path

LENGTH = 20
PK8_OPENING = "ILEAVEATMIDNIGHTBEFO"

SUBJECTS = (
    "I", "THE NEEDLE", "THE POINT", "THE KNOT", "THE THREAD", "THE ARCHIVE",
    "THE LETTER", "THE LETTERS", "THE CHARACTERS", "THE ROUTE",
)

VERBS = (
    "LEAVE", "RETURN", "RETURN TO", "GO", "GO TO", "ARRIVE AT", "REACH",
    "ENTER", "APPROACH", "FIND", "TAKE", "PICK UP", "CARRY", "HOLD", "PLACE",
    "LAY", "INSERT", "PASS", "PUSH", "PRESS", "PULL", "DRAW", "THREAD",
    "PIERCE", "PRICK", "CUT", "SPLIT", "LOOSEN", "UNTIE", "UNWIND",
    "UNRAVEL", "RELEASE", "REVEAL", "OPEN", "READ", "FOLLOW", "BEGIN",
    "BEGIN TO UNRAVEL", "CONTINUE", "WAIT", "AWAIT", "REMEMBER", "UNDERSTAND",
)

COMPLEMENTS = (
    "", "AT MIDNIGHT", "BEFORE DAWN", "AT DAWN", "IN THE DARK",
    "BY CANDLELIGHT", "IN SILENCE", "THE WORKSHOP", "THE WHITESMITH",
    "THE ARCHIVE", "TO THE ARCHIVE", "AT THE ARCHIVE", "IN THE ARCHIVE",
    "THE ARCHIVE DOOR", "THE KNOT", "THE FIRST KNOT", "THE INNER KNOT",
    "THE NEEDLE", "ONE NEEDLE", "THE POINT", "THE EYE", "THE THREAD",
    "THE FIRST THREAD", "THE INNER THREAD", "THE STRING", "THE LETTER",
    "THE SHORT LETTER", "THE MESSAGE", "THE ROUTE", "THE FIRST LETTER",
)

TAILS = (
    "", "BEFORE GOING", "BEFORE LEAVING", "BEFORE RETURNING", "BEFORE ENTERING",
    "AFTER LEAVING", "AFTER RETURNING", "AFTER WAITING", "WHEN I ARRIVE",
    "WHEN I RETURN", "WHEN I REACH THE ARCHIVE", "AS I LEAVE", "AS I RETURN",
    "WITH THE NEEDLE", "WITH ONE NEEDLE", "WITH GREAT CARE", "FOR THE LAST TIME",
    "AND TAKE THE NEEDLE", "AND PICK UP THE NEEDLE", "AND FIND THE KNOT",
    "AND BEGIN TO PULL", "BUT THE ARCHIVE CALLS", "BUT THE KNOT AWAITS",
    "BUT I CANNOT STAY", "UNTIL IT YIELDS", "UNTIL IT OPENS",
)

STATES = (
    "GRATEFUL", "READY", "ALONE", "AFRAID", "CERTAIN", "PREPARED", "AT THE ARCHIVE",
    "IN THE ARCHIVE", "BACK AT THE ARCHIVE", "CALLED TO THE ARCHIVE",
)

PIVOTS = (
    "BUT THE ARCHIVE IS MY TRUE CALLING", "BUT THE KNOT AWAITS",
    "BUT I MUST RETURN", "AND THE KNOT AWAITS", "AND I KNOW WHAT I MUST DO",
    "AND I TAKE ONE NEEDLE", "AND I RETURN TO THE ARCHIVE",
)

TEMPORAL = (
    "AT MIDNIGHT", "BEFORE DAWN", "AFTER MIDNIGHT", "WHEN I RETURN",
    "AS I LEAVE", "ON MY RETURN", "TEN YEARS LATER", "AT LAST", "ONCE MORE",
)

GERUNDS = (
    "LEAVING", "GOING", "RETURNING", "ENTERING", "TAKING THE NEEDLE",
    "PICKING UP THE NEEDLE", "OPENING THE LETTER", "FINDING THE KNOT",
    "UNRAVELING THE KNOT", "READING THE MESSAGE", "FOLLOWING THE ROUTE",
)


def normalize(text: str) -> str:
    return re.sub(r"[^A-Z]", "", text.upper())


def generate(length: int = LENGTH) -> list[str]:
    sentences: set[str] = set()
    for subject, verb, complement, tail in product(SUBJECTS, VERBS, COMPLEMENTS, TAILS):
        sentences.add(normalize(f"{subject} {verb} {complement} {tail}"))
    for state, pivot in product(STATES, PIVOTS):
        sentences.add(normalize(f"I AM {state} {pivot}"))
    for temporal, subject, verb, complement in product(TEMPORAL, SUBJECTS, VERBS, COMPLEMENTS):
        sentences.add(normalize(f"{temporal} {subject} {verb} {complement}"))
    for marker, gerund, verb, complement in product(("BEFORE", "AFTER"), GERUNDS, VERBS, COMPLEMENTS):
        sentences.add(normalize(f"{marker} {gerund} I {verb} {complement}"))
    return sorted({sentence[:length] for sentence in sentences if len(sentence) >= length})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--length", type=int, default=LENGTH, choices=range(16, 65), metavar="N")
    args = parser.parse_args()
    values = generate(args.length)
    if args.length == LENGTH and PK8_OPENING not in values:
        raise RuntimeError("style grammar lost its verified-PK8 opening control")
    args.output.write_text("\n".join(values) + "\n")
    control = "yes" if args.length == LENGTH and PK8_OPENING in values else "n/a"
    print(
        f"wrote {len(values):,} PK8-style {args.length}-letter openings to {args.output}; "
        f"verified_PK8_opening_present={control}"
    )


if __name__ == "__main__":
    main()
