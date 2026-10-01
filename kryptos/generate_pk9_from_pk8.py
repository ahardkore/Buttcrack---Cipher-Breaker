#!/usr/bin/env python3
"""Generate focused PK9 cribs from the now-public, reverified PK8 plaintext.

PK8 ends with the narrator leaving the whitesmith at midnight with a needle,
returning to the archive/knot, and leaving a short letter.  These templates
cover direct continuations and likely later clauses without claiming that the
narrative prediction is correct.
"""

from __future__ import annotations

import argparse
import re
from itertools import permutations, product
from pathlib import Path

OPENERS = [
    "AT MIDNIGHT", "BEFORE MIDNIGHT", "AFTER MIDNIGHT", "LATER THAT NIGHT",
    "THAT NIGHT", "BEFORE DAWN", "AT DAWN", "BY MORNING", "THE NEXT MORNING",
    "AFTER TEN YEARS", "AT LAST", "ONCE MORE", "WHEN I LEFT", "AS I LEFT",
    "BEFORE I LEFT", "AFTER I LEFT", "WHEN I RETURNED", "AS I RETURNED",
    "AFTER I RETURNED", "UPON MY RETURN", "ON MY RETURN", "BACK AT THE ARCHIVE",
    "AT THE ARCHIVE", "INSIDE THE ARCHIVE", "OUTSIDE THE ARCHIVE",
    "BEFORE THE ARCHIVE", "AT THE ARCHIVE DOOR", "IN THE ARCHIVE CELLAR",
    "WITH THE NEEDLE", "USING THE NEEDLE", "WITH MY OWN NEEDLE",
    "WITH THE KNOT BEFORE ME", "BENEATH THE LAMP", "BY CANDLELIGHT",
    "IN THE DARKNESS", "IN THE SILENCE", "WITHOUT DELAY", "WITH GREAT CARE",
]

SUBJECTS = [
    "I", "THE NEEDLE", "THE POINT", "THE EYE", "THE KNOT", "THE THREAD",
    "THE STRING", "THE LETTER", "THE SHORT LETTER", "THE ARCHIVE",
    "THE ARCHIVE DOOR", "THE LOCK", "THE FIRST KNOT", "THE INNER KNOT",
    "PELLEGRINS KNOT", "THE INSCRIPTION", "THE CHARACTERS", "THE ROUTE",
    "THE OLD RECORD", "THE ACCESSION LOG", "MY TEACHERS LETTER",
]

VERBS = [
    "RETURNED TO", "ARRIVED AT", "REACHED", "ENTERED", "APPROACHED", "OPENED",
    "UNLOCKED", "FOUND", "FOLLOWED", "READ", "REREAD", "EXAMINED", "STUDIED",
    "PLACED", "LAID", "HELD", "TOOK", "RAISED", "LOWERED", "INSERTED",
    "PUSHED", "PRESSED", "PASSED", "SLIPPED", "DREW", "PULLED", "THREADED",
    "PIERCED", "PRICKED", "CUT", "SPLIT", "LOOSENED", "UNTIED", "UNWOUND",
    "UNRAVELED", "RELEASED", "REVEALED", "SHOWED", "EXPOSED", "TOUCHED",
    "ENTERED", "PENETRATED", "TURNED", "MOVED", "YIELDED", "PARTED", "BROKE",
    "BEGAN", "CONTINUED", "WAITED", "AWAITED", "REMEMBERED", "UNDERSTOOD",
    "DISCOVERED", "REALIZED", "KNEW", "WROTE", "LEFT", "CARRIED",
]

OBJECTS = [
    "THE ARCHIVE", "THE LOST ARCHIVE", "THE ARCHIVE DOOR", "THE INNER DOOR",
    "THE LOCK", "THE KEYHOLE", "THE KNOT", "THE FIRST KNOT", "THE INNER KNOT",
    "PELLEGRINS KNOT", "THE THREAD", "THE STRING", "THE CORD", "THE CENTER",
    "THE CORE", "THE NEEDLE", "THE POINT", "THE EYE", "THE LETTER",
    "THE SHORT LETTER", "MY LETTER", "MY TEACHERS LETTER", "THE INSCRIPTION",
    "THE CHARACTERS", "THE FIRST LETTER", "THE NEXT LETTER", "THE MESSAGE",
    "THE PASSAGE", "THE ROUTE", "THE ACCESSION LOG", "THE OLD RECORD",
    "THE MARGINALIA", "THE GRID", "THE COORDINATES", "A HIDDEN COMPARTMENT",
    "A NARROW OPENING", "A SINGLE THREAD", "ANOTHER KNOT", "WHAT LAY WITHIN",
]

TAILS = [
    "WITH THE NEEDLE", "USING THE NEEDLE", "WITH ITS POINT", "WITH GREAT CARE",
    "BEFORE DAWN", "AT MIDNIGHT", "IN THE DARK", "BY CANDLELIGHT", "IN SILENCE",
    "ONCE MORE", "FOR THE FIRST TIME", "UNTIL IT YIELDED", "UNTIL IT PARTED",
    "UNTIL IT OPENED", "UNTIL THE THREAD BROKE", "AND BEGAN TO PULL",
    "AND FOUND THE FIRST LETTER", "AND REVEALED THE ROUTE", "TO FIND THE KEY",
    "TO REVEAL THE LETTERS", "TO OPEN THE ARCHIVE", "THROUGH THE KNOT",
    "INTO THE KNOT", "BENEATH THE THREAD", "ALONG THE THREAD",
]

FIXED = [
    "I LEFT THE WHITESMITH AT MIDNIGHT", "I RETURNED TO THE ARCHIVE AT MIDNIGHT",
    "AT MIDNIGHT I RETURNED TO THE ARCHIVE", "BEFORE DAWN I REACHED THE ARCHIVE",
    "THE ARCHIVE WAS DARK WHEN I RETURNED", "THE KNOT AWAITED ME IN THE ARCHIVE",
    "THE KNOT LAY WHERE I HAD LEFT IT", "I PLACED THE KNOT BENEATH THE LAMP",
    "I TOOK THE NEEDLE FROM MY POCKET", "I HELD MY NEEDLE TO THE LIGHT",
    "I INSERTED THE NEEDLE INTO THE KNOT", "I PASSED THE NEEDLE THROUGH THE KNOT",
    "THE NEEDLE ENTERED THE KNOT EASILY", "THE FINE POINT SLIPPED BENEATH THE THREAD",
    "THE POINT SEPARATED A SINGLE THREAD", "THE FIRST THREAD YIELDED TO THE NEEDLE",
    "THE KNOT BEGAN TO LOOSEN", "THE KNOT BEGAN TO UNRAVEL", "THE KNOT OPENED",
    "EACH THREAD REVEALED ANOTHER LETTER", "THE CHARACTERS FORMED A NEW MESSAGE",
    "THE LETTERS REVEALED THE ROUTE", "THE ROUTE LED DEEPER INTO THE ARCHIVE",
    "PELLEGRINS INSCRIPTION WAS COMPLETE", "I READ THE WORDS IN PELLEGRINS HAND",
    "MY TEACHERS SHORT LETTER SAID", "THE WHITESMITHS LETTER SAID", "I OPENED HIS LETTER",
    "THE LETTER CONTAINED ONLY A FEW WORDS", "MASTERY IS ONLY THE BEGINNING",
    "THE ARCHIVE IS MY TRUE CALLING", "THE KNOT HAD WAITED TEN YEARS",
]


def clean(text: str, length: int) -> str | None:
    value = re.sub(r"[^A-Z]", "", text.upper())
    return value[:length] if len(value) >= length else None


def generate(length: int) -> list[str]:
    out: set[str] = set()

    def add(text: str) -> None:
        value = clean(text, length)
        if value:
            out.add(value)

    for text in FIXED:
        add(text)
    for subject, verb, obj in product(SUBJECTS, VERBS, OBJECTS):
        add(f"{subject} {verb} {obj}")
    for subject, verb, tail in product(SUBJECTS, VERBS, TAILS):
        add(f"{subject} {verb} {tail}")
    for opener, subject, verb in product(OPENERS, ["I", "THE NEEDLE", "THE KNOT", "THE THREAD"], VERBS):
        add(f"{opener} {subject} {verb}")
    for opener, verb, obj in product(OPENERS, VERBS, OBJECTS):
        add(f"{opener} {verb} {obj}")
    for verb, obj, tail in product(VERBS, OBJECTS, TAILS):
        add(f"I {verb} {obj} {tail}")
    return sorted(out)


PK8_KEYS = ("METE", "METER", "METIER", "MASTERY")


def generate_key_sequences(length: int) -> list[str]:
    """Generate windows from every unseparated ordering of the four PK8 keys."""
    out: set[str] = set()
    for order in permutations(PK8_KEYS):
        stream = "".join(order)
        out.update(stream[i : i + length] for i in range(len(stream) - length + 1))
    return sorted(out)


def generate_key_disclosures(length: int) -> list[str]:
    """Generate windows that would disclose PK8's now-known key sequence."""
    keys = PK8_KEYS
    prefixes = (
        "", "THELETTERREADS", "HISLETTERREADS", "THELETTERSAID",
        "MYTEACHERWROTE", "THEWHITESMITHWROTE", "THEKEYIS", "THEKEYSARE",
        "THEWORDSARE", "THEFOURWORDSARE", "REMEMBER", "USE", "FIRSTUSE",
    )
    suffixes = (
        "", "INTHATORDER", "INREVERSEORDER", "THESEARETHEKEYS",
        "WILLUNRAVELTHEKNOT", "WILLOPENTHEARCHIVE",
    )
    connectors = ("", "AND", "THEN", "FOLLOWEDBY")
    sentences: set[str] = set()
    for order in permutations(keys):
        for connector in connectors:
            sequence = connector.join(order)
            for prefix, suffix in product(prefixes, suffixes):
                sentences.add(prefix + sequence + suffix)
    for key in keys:
        for prefix, suffix in product(prefixes, suffixes):
            sentences.add(prefix + key + suffix)

    out: set[str] = set()
    for sentence in sentences:
        stream = re.sub(r"[^A-Z]", "", sentence.upper())
        out.update(stream[i : i + length] for i in range(len(stream) - length + 1))
    return sorted(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--length", type=int, default=20, choices=range(16, 65), metavar="N")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--key-disclosures",
        action="store_true",
        help="generate possible statements of PK8's METE/METER/METIER/MASTERY keys",
    )
    mode.add_argument(
        "--key-sequences",
        action="store_true",
        help="generate windows from every unseparated ordering of the four PK8 keys",
    )
    args = parser.parse_args()
    if args.key_disclosures:
        values, label = generate_key_disclosures(args.length), "PK8-key-disclosure"
    elif args.key_sequences:
        values, label = generate_key_sequences(args.length), "PK8-key-sequence"
    else:
        values, label = generate(args.length), "PK8-continuation"
    args.output.write_text("\n".join(values) + "\n")
    print(f"wrote {len(values):,} focused {args.length}-letter {label} cribs to {args.output}")


if __name__ == "__main__":
    main()
