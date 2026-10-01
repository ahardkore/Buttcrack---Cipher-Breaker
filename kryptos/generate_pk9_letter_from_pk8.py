#!/usr/bin/env python3
"""Generate focused PK9 cribs treating it as the short letter ending PK8.

PK8 ends, "I leave the Whitesmith a short letter."  This generator models the
literal contents of that letter: salutations, thanks, departure explanations,
the stolen/taken needle, the archive, the knot, warnings, and farewells.  It is
a deterministic hypothesis corpus, not a claim about PK9's plaintext.
"""

from __future__ import annotations

import argparse
import re
from itertools import product
from pathlib import Path

SALUTATIONS = (
    "", "DEAR TEACHER", "DEAR MASTER", "MASTER", "MY TEACHER",
    "TO MY TEACHER", "TO THE WHITESMITH", "WHITESMITH", "MY FRIEND",
)

LEADS = (
    "", "BY THE TIME YOU READ THIS", "WHEN YOU READ THIS",
    "IF YOU ARE READING THIS", "AS YOU READ THIS", "I WRITE TO TELL YOU",
    "I WRITE THESE WORDS", "I LEAVE THIS LETTER", "THIS LETTER IS MY FAREWELL",
    "PLEASE FORGIVE ME", "DO NOT BE ANGRY", "DO NOT THINK ME UNGRATEFUL",
    "AFTER TEN YEARS", "AT MIDNIGHT", "BEFORE DAWN", "TONIGHT",
)

STATEMENTS = (
    "I HAVE LEFT", "I AM GONE", "I WILL BE GONE", "I MUST LEAVE",
    "I HAD TO LEAVE", "I COULD NOT STAY", "I CANNOT STAY", "I CHOSE TO LEAVE",
    "I HAVE LEFT THE WORKSHOP", "I HAVE LEFT YOUR WORKSHOP",
    "I LEAVE THE WHITESMITH", "I HAVE RETURNED TO THE ARCHIVE",
    "I AM RETURNING TO THE ARCHIVE", "I MUST RETURN TO THE ARCHIVE",
    "I GO BACK TO THE ARCHIVE", "I HAVE CHOSEN THE ARCHIVE",
    "THE ARCHIVE IS MY TRUE CALLING", "MY TRUE CALLING IS THE ARCHIVE",
    "MY PLACE IS IN THE ARCHIVE", "THE ARCHIVE NEEDS ME", "THE KNOT AWAITS ME",
    "THE KNOT STILL AWAITS", "I MUST FACE THE KNOT", "I WILL UNRAVEL THE KNOT",
    "I HAVE TAKEN ONE NEEDLE", "I TOOK ONE NEEDLE", "I TOOK A SINGLE NEEDLE",
    "I PICKED UP ONE NEEDLE", "I FOUND ONE NEEDLE IN THE GUTTER",
    "THE NEEDLE IS WITH ME", "I CARRY THE NEEDLE", "I NEED THE NEEDLE",
    "YOUR NEEDLE WILL OPEN THE KNOT", "THE NEEDLE WILL UNRAVEL THE KNOT",
    "I KNOW NOW WHAT I MUST DO", "I UNDERSTAND MY PURPOSE", "MY CHOICE IS MADE",
    "TEN YEARS HAVE PREPARED ME", "MY TRAINING IS COMPLETE",
    "YOUR LESSONS HAVE PREPARED ME", "YOU HAVE TAUGHT ME WELL",
    "I AM GRATEFUL TO YOU", "I AM GRATEFUL FOR YOUR TEACHING",
    "THANK YOU FOR TEACHING ME", "THANK YOU FOR TEN YEARS", "I OWE YOU EVERYTHING",
    "DO NOT FOLLOW ME", "DO NOT SEARCH FOR ME", "DO NOT COME TO THE ARCHIVE",
    "KEEP THIS LETTER", "REMEMBER ME", "FAREWELL", "GOODBYE",
)

TAILS = (
    "", "BEFORE DAWN", "AT MIDNIGHT", "FOR THE LAST TIME", "ONCE MORE",
    "WITH ONE NEEDLE", "WITH YOUR NEEDLE", "WITH THE NEEDLE FROM THE GUTTER",
    "TO FACE THE KNOT", "TO UNRAVEL THE KNOT", "TO OPEN THE ARCHIVE",
    "BECAUSE THE KNOT AWAITS", "BECAUSE THE ARCHIVE CALLS ME",
    "BUT I CANNOT STAY", "AND I WILL NOT RETURN", "PLEASE FORGIVE ME",
    "THANK YOU MY TEACHER", "FAREWELL MY TEACHER",
)

FIXED = (
    "DEAR TEACHER BY THE TIME YOU READ THIS I WILL BE GONE",
    "DEAR TEACHER FORGIVE ME I HAVE RETURNED TO THE ARCHIVE",
    "MASTER I AM GRATEFUL BUT THE ARCHIVE IS MY TRUE CALLING",
    "MY TEACHER I HAVE TAKEN ONE NEEDLE FROM THE GUTTER",
    "I TOOK ONLY ONE NEEDLE THE REST REMAIN IN THE GUTTER",
    "I LEAVE AT MIDNIGHT WITH ONE NEEDLE AND YOUR LESSONS",
    "TEN YEARS HAVE TAUGHT ME HOW TO FACE THE KNOT",
    "THE NEEDLE YOU TAUGHT ME TO MAKE WILL UNRAVEL THE KNOT",
    "THE ARCHIVE IS MY TRUE CALLING AND THE KNOT AWAITS",
    "DO NOT FOLLOW ME TO THE ARCHIVE THE KNOT IS MINE",
    "WHEN YOU FIND THIS LETTER I WILL BE AT THE ARCHIVE",
    "BY THE TIME YOU READ THIS I WILL HAVE OPENED THE KNOT",
)


def normalize(text: str) -> str:
    return re.sub(r"[^A-Z]", "", text.upper())


def generate(length: int, all_windows: bool) -> list[str]:
    sentences: set[str] = {normalize(text) for text in FIXED}
    for salutation, lead, statement in product(SALUTATIONS, LEADS, STATEMENTS):
        sentences.add(normalize(f"{salutation} {lead} {statement}"))
    for salutation, statement, tail in product(SALUTATIONS, STATEMENTS, TAILS):
        sentences.add(normalize(f"{salutation} {statement} {tail}"))
    for lead, statement, tail in product(LEADS, STATEMENTS, TAILS):
        sentences.add(normalize(f"{lead} {statement} {tail}"))

    out: set[str] = set()
    for sentence in sentences:
        if len(sentence) < length:
            continue
        if all_windows:
            out.update(sentence[i : i + length] for i in range(len(sentence) - length + 1))
        else:
            out.add(sentence[:length])
    return sorted(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--length", type=int, default=20, choices=range(16, 65), metavar="N")
    parser.add_argument(
        "--all-windows",
        action="store_true",
        help="emit every window of each candidate letter rather than only openings",
    )
    args = parser.parse_args()
    values = generate(args.length, args.all_windows)
    args.output.write_text("\n".join(values) + "\n")
    kind = "windows" if args.all_windows else "openings"
    print(f"wrote {len(values):,} focused {args.length}-letter PK8-letter {kind} to {args.output}")


if __name__ == "__main__":
    main()
