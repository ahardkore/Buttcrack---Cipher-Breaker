#!/usr/bin/env python3
"""Generate present-tense PK9 narrative cribs continuing the verified PK8 story.

PK8 switches into immediate present tense ("I leave", "I pick up", "the knot
awaits"). Earlier continuation grammars overemphasized past-tense actions. This
generator targets the narrator's return to the archive and use of the needle on
the knot in the same present-tense style.
"""

from __future__ import annotations

import argparse
import re
from itertools import product
from pathlib import Path

OPENERS = (
    "", "AT MIDNIGHT", "BEFORE DAWN", "IN THE DARK", "BY CANDLELIGHT",
    "BACK AT THE ARCHIVE", "BACK IN THE ARCHIVE", "AT THE ARCHIVE",
    "INSIDE THE ARCHIVE", "WHEN I RETURN", "AS I RETURN", "ON MY RETURN",
    "WITH THE NEEDLE", "WITH MY NEEDLE", "WITH THE KNOT BEFORE ME",
    "BENEATH THE LAMP", "FOR THE FIRST TIME", "AT LAST", "ONCE MORE",
)

SUBJECTS = (
    "I", "THE NEEDLE", "THE POINT", "THE EYE", "THE KNOT", "THE THREAD",
    "THE STRING", "THE FIRST THREAD", "THE INNER THREAD", "THE ARCHIVE",
    "THE ARCHIVE DOOR", "THE LOCK", "THE LETTERS", "THE CHARACTERS",
)

VERBS = (
    "RETURN TO", "GO TO", "ENTER", "APPROACH", "REACH", "OPEN", "UNLOCK",
    "FIND", "FOLLOW", "READ", "EXAMINE", "STUDY", "PLACE", "LAY", "HOLD",
    "TAKE", "RAISE", "LOWER", "INSERT", "PUSH", "PRESS", "PASS", "SLIP",
    "DRAW", "PULL", "THREAD", "PIERCE", "PRICK", "CUT", "SPLIT", "LOOSEN",
    "UNTIE", "UNWIND", "UNRAVEL", "RELEASE", "REVEAL", "SHOW", "EXPOSE",
    "TOUCH", "ENTER", "PENETRATE", "TURN", "MOVE", "YIELD", "PART", "BREAK",
    "BEGIN", "CONTINUE", "WAIT", "REMEMBER", "UNDERSTAND", "DISCOVER", "KNOW",
)

OBJECTS = (
    "THE ARCHIVE", "THE LOST ARCHIVE", "THE ARCHIVE DOOR", "THE INNER DOOR",
    "THE LOCK", "THE KEYHOLE", "THE KNOT", "THE FIRST KNOT", "THE INNER KNOT",
    "PELLEGRINS KNOT", "THE THREAD", "THE FIRST THREAD", "THE INNER THREAD",
    "THE STRING", "THE CORD", "THE CENTER", "THE CORE", "THE NEEDLE",
    "THE POINT", "THE EYE", "THE LETTER", "THE SHORT LETTER", "THE INSCRIPTION",
    "THE CHARACTERS", "THE FIRST LETTER", "THE NEXT LETTER", "THE MESSAGE",
    "THE PASSAGE", "THE ROUTE", "THE ACCESSION LOG", "THE OLD RECORD",
    "THE MARGINALIA", "THE GRID", "THE COORDINATES", "A HIDDEN COMPARTMENT",
    "A NARROW OPENING", "A SINGLE THREAD", "ANOTHER KNOT", "WHAT LIES WITHIN",
)

TAILS = (
    "", "WITH THE NEEDLE", "USING THE NEEDLE", "WITH ITS POINT", "WITH CARE",
    "BEFORE DAWN", "AT MIDNIGHT", "IN THE DARK", "BY CANDLELIGHT", "IN SILENCE",
    "ONCE MORE", "FOR THE FIRST TIME", "UNTIL IT YIELDS", "UNTIL IT PARTS",
    "UNTIL IT OPENS", "UNTIL THE THREAD BREAKS", "AND BEGIN TO PULL",
    "AND FIND THE FIRST LETTER", "AND REVEAL THE ROUTE", "TO FIND THE KEY",
    "TO REVEAL THE LETTERS", "TO OPEN THE ARCHIVE", "THROUGH THE KNOT",
    "INTO THE KNOT", "BENEATH THE THREAD", "ALONG THE THREAD",
)

FIXED = (
    "I RETURN TO THE ARCHIVE AT MIDNIGHT", "AT MIDNIGHT I RETURN TO THE ARCHIVE",
    "I REACH THE ARCHIVE BEFORE DAWN", "BACK AT THE ARCHIVE I FIND THE KNOT",
    "THE KNOT LIES WHERE I LEFT IT", "THE KNOT AWAITS ME IN THE DARK",
    "I PLACE THE KNOT BENEATH THE LAMP", "I TAKE THE NEEDLE FROM MY POCKET",
    "I HOLD THE NEEDLE TO THE LIGHT", "I INSERT THE NEEDLE INTO THE KNOT",
    "I PASS THE NEEDLE THROUGH THE KNOT", "THE NEEDLE ENTERS THE KNOT EASILY",
    "THE FINE POINT SLIPS BENEATH THE THREAD", "THE POINT SEPARATES ONE THREAD",
    "THE FIRST THREAD YIELDS TO THE NEEDLE", "THE KNOT BEGINS TO LOOSEN",
    "THE KNOT BEGINS TO UNRAVEL", "EACH THREAD REVEALS ANOTHER LETTER",
    "THE CHARACTERS FORM A NEW MESSAGE", "THE LETTERS REVEAL THE ROUTE",
    "THE ROUTE LEADS DEEPER INTO THE ARCHIVE", "I BEGIN TO UNRAVEL THE KNOT",
    "I KNOW NOW HOW TO OPEN THE KNOT", "MASTERY IS ONLY THE BEGINNING",
)


def normalize(text: str) -> str:
    return re.sub(r"[^A-Z]", "", text.upper())


def generate(length: int, all_windows: bool) -> list[str]:
    sentences: set[str] = {normalize(text) for text in FIXED}
    for subject, verb, obj in product(SUBJECTS, VERBS, OBJECTS):
        sentences.add(normalize(f"{subject} {verb} {obj}"))
    for opener, subject, verb in product(OPENERS, SUBJECTS, VERBS):
        sentences.add(normalize(f"{opener} {subject} {verb}"))
    for opener, verb, obj in product(OPENERS, VERBS, OBJECTS):
        sentences.add(normalize(f"{opener} I {verb} {obj}"))
    for verb, obj, tail in product(VERBS, OBJECTS, TAILS):
        sentences.add(normalize(f"I {verb} {obj} {tail}"))

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
    parser.add_argument("--all-windows", action="store_true")
    args = parser.parse_args()
    values = generate(args.length, args.all_windows)
    args.output.write_text("\n".join(values) + "\n")
    kind = "windows" if args.all_windows else "openings"
    print(f"wrote {len(values):,} present-tense {length_label(args.length)} PK8 continuations ({kind}) to {args.output}")


def length_label(length: int) -> str:
    return f"{length}-letter"


if __name__ == "__main__":
    main()
