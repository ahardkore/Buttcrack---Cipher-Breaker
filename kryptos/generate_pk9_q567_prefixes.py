#!/usr/bin/env python3
"""Generate broad fixed-length PK9 cribs for the Q(5)+Q(6)+Q(7)->T(8) test.

This deliberately over-generates grammatical and near-grammatical openings. The
companion C attack applies a much stronger independent requirement: all three
recovered wheels must be dictionary words. Output is deterministic, one crib per
line, and is intended as generated search input rather than evidence.
"""

from __future__ import annotations

import argparse
import re
from itertools import product
from pathlib import Path

SUBJECTS = [
    "I", "HE", "WE", "THE MASTER", "THE WHITESMITH", "THE SMITH", "MY MASTER",
    "THE OLD MAN", "THE APPRENTICE", "THE NEEDLE", "THE WIRE", "THE ROD",
    "THE STEEL", "THE IRON", "THE METAL", "THE WORK", "THE FIRE", "THE FLAME",
    "THE COALS", "THE BELLOWS", "THE HAMMER", "THE TONGS", "THE ANVIL",
    "THE DRAWPLATE", "THE POINT", "THE EYE", "EACH BLOW", "EVERY STROKE",
    "THE KNOT", "THE THREAD", "THE STRING", "THE FIBER", "THE STRAND",
    "THE LETTERS", "THE INSCRIPTION", "THE CHARACTERS", "THE SEQUENCE",
    "THE GRID", "THE COORDINATES", "THE CIPHERTEXT", "THE MESSAGE",
    "THE PASSAGE", "THE RECORD", "THE TREATISE", "THE BOOK", "THE ARCHIVE",
    "THE LOST ARCHIVE", "THE ROUTE", "THE KEY", "THE FIRST KEY", "THE SECRET",
    "THE ANSWER", "PELLEGRIN", "THE ANATOMIST", "THE INSTRUMENT",
]

VERBS = [
    "TOOK", "HELD", "DREW", "PULLED", "PLACED", "LAID", "SET", "LIFTED",
    "RAISED", "LOWERED", "REMOVED", "WITHDREW", "CARRIED", "STRUCK", "BEAT",
    "HAMMERED", "FORGED", "SHAPED", "WORKED", "TURNED", "HEATED", "REHEATED",
    "TEMPERED", "QUENCHED", "COOLED", "HARDENED", "SOFTENED", "ANNEALED",
    "RUBBED", "COATED", "OILED", "DIPPED", "PLUNGED", "PASSED", "FORCED",
    "SMOOTHED", "FILED", "GROUND", "POLISHED", "SHARPENED", "PIERCED",
    "PUNCHED", "BORED", "CUT", "TESTED", "EXAMINED", "MEASURED", "WEIGHED",
    "WATCHED", "TENDED", "PUMPED", "WAITED", "BEGAN", "CONTINUED", "FINISHED",
    "COMPLETED", "SHOWED", "TAUGHT", "TOLD", "WARNED", "EXPLAINED", "SAID",
    "SMILED", "NODDED", "HANDED", "GAVE", "MADE", "REACHED", "BECAME",
    "FOUND", "DISCOVERED", "RETURNED", "WROTE", "READ", "STUDIED", "FOLLOWED",
    "OPENED", "CLOSED", "UNRAVELED", "UNTIED", "LOOSENED", "PIERCED", "SPLIT",
    "REVEALED", "INSCRIBED", "ENGRAVED", "CONTAINED", "FORMED", "PROJECTED",
    "POINTED", "LED", "GUIDED", "DECODED", "DECIPHERED", "RECORDED", "COPIED",
    "TRACED", "COUNTED", "FOLDED", "WOUND", "THREADED", "PASSED", "PRESERVED",
]

OBJECTS = [
    "THE STEEL", "THE IRON", "THE METAL", "THE WIRE", "THE ROD", "THE NEEDLE",
    "THE BLANK", "THE TIP", "THE POINT", "THE EYE", "THE HEAD", "THE PIECE",
    "THE TONGS", "THE HAMMER", "THE ANVIL", "THE PLATE", "THE DRAWPLATE",
    "THE HEARTH", "THE COALS", "THE FIRE", "THE FLAME", "THE BELLOWS",
    "THE WATER", "THE OIL", "THE FAT", "THE TALLOW", "THE ASHES", "THE SLAG",
    "THE CRUCIBLE", "THE FIRST HOLE", "THE NEXT HOLE", "EACH HOLE", "EACH WIRE",
    "A SLENDER WIRE", "A THIN ROD", "A FINE POINT", "A SINGLE HAIR", "HIS HAMMER",
    "HIS TONGS", "MY HAMMER", "MY HAND", "MY NEEDLE", "HIS WORK", "THE WORK",
    "THE KNOT", "THE THREAD", "THE STRING", "THE FIBERS", "THE STRAND", "A SINGLE STRAND",
    "THE LETTERS", "THE CHARACTERS", "THE INSCRIPTION", "THE SEQUENCE", "THE GRID",
    "THE COORDINATES", "THE CIPHERTEXT", "THE MESSAGE", "THE PASSAGE", "THE RECORD",
    "THE TREATISE", "THE BOOK", "THE MARGINALIA", "THE ARCHIVE", "THE LOST ARCHIVE",
    "THE ROUTE", "THE KEY", "THE FIRST KEY", "THE SECOND KEY", "THE SECRET", "THE ANSWER",
    "THE INSTRUMENT", "THE GLASS", "THE LENS", "THE WEAVE", "THE TENSION",
    "PELLEGRINS WORDS", "PELLEGRINS HAND", "HIS OWN HAND", "MY NOTES", "MY RECORD",
    "TO WORK", "TO FORGE", "TO DRAW", "TO BEGIN", "TO CONTINUE", "TO MAKE THE NEEDLE",
    "TO READ THE LETTERS", "TO UNRAVEL THE KNOT", "TO FIND THE ARCHIVE", "TO FOLLOW THE ROUTE",
]

LEADS = [
    "AT LAST", "THEN", "AND THEN", "NEXT", "NOW", "AFTERWARD", "ONCE MORE",
    "WITH CARE", "WITH GREAT CARE", "WITH LONG TONGS", "WITH STEADY HANDS",
    "WITH HIS TONGS", "WITH THE TONGS", "WITH HIS HAMMER", "WITH THE HAMMER",
    "UPON THE ANVIL", "ON THE ANVIL", "AT THE ANVIL", "AT THE HEARTH",
    "AT THE FORGE", "BY THE HEARTH", "FROM THE HEARTH", "FROM THE FIRE",
    "FROM THE FLAME", "FROM THE COALS", "OUT OF THE FIRE", "INTO THE WATER",
    "INTO THE OIL", "INTO THE FLAME", "THROUGH THE PLATE", "THROUGH THE DRAWPLATE",
    "BEFORE IT COOLED", "WHILE IT WAS HOT", "WHILE IT GLOWED", "AS IT GLOWED",
    "WHEN IT WAS READY", "WHEN THE STEEL WAS READY", "WHEN THE IRON WAS READY",
    "WHEN THE FIRE WAS READY", "WHEN THE COALS WERE WHITE", "ONCE THE STEEL WAS READY",
    "ONCE THE METAL WAS READY", "ONLY WHEN IT WAS READY", "AFTER NINE DAYS",
    "AFTER THE NINE DAYS", "FOR NINE DAYS", "ON THE NINTH DAY", "ON THE TENTH DAY",
    "WHEN NINE DAYS HAD PASSED", "AFTER TEN YEARS", "FOR TEN YEARS",
    "ON THE FIRST DAY", "EACH DAY", "EVERY DAY", "DAY AFTER DAY", "BLOW AFTER BLOW",
    "IN THE ARCHIVE", "AT THE ARCHIVE", "FROM THE ARCHIVE", "IN THE RECORDS",
    "IN HIS OWN HAND", "IN PELLEGRINS HAND", "BENEATH THE LENS", "UNDER THE LENS",
    "ALONG THE THREAD", "ALONG THE STRING", "WITH THE NEEDLE", "USING THE NEEDLE",
    "TO FIND THE KEY", "TO FIND THE ROUTE", "TO READ THE KNOT", "TO OPEN THE ARCHIVE",
    "AFTER I RETURNED", "WHEN I RETURNED", "WHEN THE KNOT OPENED", "WHEN THE THREAD PARTED",
]

CONTINUATIONS = [
    "FROM THE FIRE", "FROM THE FLAME", "FROM THE COALS", "FROM THE HEARTH",
    "INTO THE WATER", "INTO THE OIL", "INTO THE TROUGH", "INTO THE ASHES",
    "INTO THE COALS", "UPON THE ANVIL", "ON THE ANVIL", "ON THE HORN",
    "UNDER THE HAMMER", "WITH THE TONGS", "WITH THE HAMMER", "THROUGH THE HOLE",
    "THROUGH THE PLATE", "THROUGH THE DRAWPLATE", "UNTIL IT GLOWED",
    "UNTIL IT COOLED", "UNTIL IT WAS THIN", "UNTIL IT WAS READY", "AGAIN",
    "SLOWLY", "GENTLY", "CAREFULLY", "IN SILENCE", "WITHOUT PAUSE",
    "TO DRAW IT FINE", "TO MAKE IT SHARP", "TO SHAPE THE EYE", "TO SPLIT A HAIR",
    "TO READ THE KNOT", "FOR PELLEGRIN", "OF MY OWN MAKING", "IN THE ARCHIVE",
    "IN THE RECORDS", "ALONG THE THREAD", "ALONG THE STRING", "WITH THE NEEDLE",
    "UNDER THE LENS", "IN HIS OWN HAND", "TO REVEAL THE LETTERS", "TO FIND THE KEY",
    "TO FIND THE ROUTE", "TO OPEN THE ARCHIVE", "TOWARDS THE ARCHIVE", "TOWARDS BERN",
]

FIXED = [
    "INVESTIGATION LOG ITEM NINE", "INVESTIGATION LOG ITEM TEN",
    "THE NINTH MONTH I RETURNED", "THE TENTH YEAR HAD PASSED",
    "AT LAST THE WORK COULD BEGIN", "AT LAST THE STEEL WAS READY",
    "AT LAST THE NEEDLE WAS FINISHED", "AT LAST I HELD THE NEEDLE",
    "AFTER NINE DAYS IN THE FLAME", "WHEN NINE DAYS HAD PASSED",
    "ON THE TENTH DAY HE DREW THE STEEL", "FOR TEN YEARS I STUDIED HIS CRAFT",
    "HE DREW THE PURIFIED STEEL FROM THE FIRE", "HE PLACED THE STEEL UPON THE ANVIL",
    "HE DREW THE WIRE THROUGH THE DRAWPLATE", "HE PULLED THE WIRE THROUGH SMALLER HOLES",
    "HE FLATTENED THE HEAD OF THE NEEDLE", "HE PUNCHED THE EYE OF THE NEEDLE",
    "WITH A SLENDER PUNCH HE PIERCED THE EYE", "HE FILED THE EDGES SMOOTH",
    "HE TEMPERED THE POINT IN OIL", "HE QUENCHED THE HOT NEEDLE IN WATER",
    "THE NEEDLE WAS AS FINE AS A HAIR", "THE POINT WAS FINE ENOUGH TO SPLIT A HAIR",
    "THE NEEDLE WAS ONE OF MY OWN MAKING", "HE HANDED ME THE FINISHED NEEDLE",
    "I TOOK THE NEEDLE IN MY HAND", "I RETURNED TO THE ARCHIVE WITH THE NEEDLE",
    "THE KNOT BEGAN TO UNRAVEL", "I PIERCED THE KNOT WITH THE NEEDLE",
    "THE THREAD REVEALED FURTHER LETTERS", "THE ROUTE TO THE LOST ARCHIVE",
]


def clean_prefix(text: str, length: int) -> str | None:
    text = re.sub(r"[^A-Z]", "", text.upper())
    return text[:length] if len(text) >= length else None


def generate(length: int = 16) -> list[str]:
    phrases: set[str] = set()

    def add(text: str) -> None:
        value = clean_prefix(text, length)
        if value:
            phrases.add(value)

    for phrase in FIXED:
        add(phrase)

    # Broad direct clauses. Objects and continuations often begin after the
    # 16-letter boundary, but retaining them handles short subject/verb pairs.
    for subject, verb, obj in product(SUBJECTS, VERBS, OBJECTS):
        add(f"{subject} {verb} {obj}")
    for subject, verb, tail in product(SUBJECTS, VERBS, CONTINUATIONS):
        add(f"{subject} {verb} {tail}")

    # Adverbial/time openings followed by the compact narrator subjects most
    # characteristic of PK6/PK7.
    for lead, subject, verb in product(LEADS, ["I", "HE", "WE", "THE MASTER", "THE WHITESMITH"], VERBS):
        add(f"{lead} {subject} {verb}")
    for lead, verb, obj in product(LEADS, VERBS, OBJECTS):
        add(f"{lead} {verb} {obj}")

    # Common infinitive/gerund-style openings.
    for stem in ["TO MAKE", "TO FORGE", "TO SHAPE", "TO TEMPER", "TO HARDEN", "TO FINISH",
                 "DRAWING", "FORGING", "HAMMERING", "TEMPERING", "QUENCHING", "POLISHING"]:
        for obj, tail in product(OBJECTS, CONTINUATIONS):
            add(f"{stem} {obj} {tail}")

    return sorted(phrases)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path, nargs="?", default=Path("pk9_q567_prefixes.txt"))
    parser.add_argument("--length", type=int, default=16, choices=range(16, 65), metavar="N")
    args = parser.parse_args()
    prefixes = generate(args.length)
    args.output.write_text("\n".join(prefixes) + "\n")
    print(f"wrote {len(prefixes):,} unique {args.length}-letter prefixes to {args.output}")


if __name__ == "__main__":
    main()
