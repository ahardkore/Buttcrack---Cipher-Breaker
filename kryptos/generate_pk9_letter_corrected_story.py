#!/usr/bin/env python3
"""PK9 crib corpus grounded in the CORRECTED verified story (2026-10-02).

PK8 ends: "I leave the Whitesmith a short letter."  PK9 (144 letters) is a
strong candidate for that letter or for the narrator's next diary entry.
This generator uses only facts from the verified PK1-PK8 texts:

  - the PK6 bargain: study ten years, then take "one of my own making";
  - PK8 breaks it: he takes one needle FROM THE GUTTER at midnight;
  - the author's time-marker openings (Two years in. / Fourteen days in the
    barn. / Three weeks in. / Seventh month. / I leave at midnight.);
  - PK4/PK5 details (stone barn, winter fodder, inner door, drew no blood);
  - PK7 details (rise before the sun, done by noon, purify the metal, draw
    the wire, the same step four times, my hand falters, not my calling).

Outputs 30-letter openings for the exact split-crib and grouped-crib engines
(prefix mode; the engines also accept all-offset modes).
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

SALUTATIONS = (
    "", "DEAR TEACHER", "DEAR WHITESMITH", "TO MY TEACHER", "MY TEACHER",
    "MASTER", "DEAR MASTER", "MY FRIEND", "FRIEND",
)

TIME_MARKERS = (
    "TEN YEARS IN", "TEN YEARS IN THE WORKSHOP", "TEN YEARS HAVE PASSED",
    "THIS IS MY LAST NIGHT", "TONIGHT I LEAVE", "AT MIDNIGHT", "THIS MORNING",
    "BEFORE DAWN", "THE LAST MORNING", "MY LAST DAY", "THE FINAL MORNING",
    "ONE LAST TIME", "THE LAST NIGHT", "BEFORE THE SUN", "BEFORE NOON",
    "ELEVEN YEARS IN", "THE FIRST MORNING", "A YEAR SINCE", "AT NOON",
    "WHEN THE SUN ROSE", "AS THE SUN ROSE", "THE BELL HAS RUNG", "AT LAST",
)

CONFESSIONS = (
    "I HAVE TAKEN ONE NEEDLE FROM THE GUTTER",
    "I TOOK ONE NEEDLE FROM THE GUTTER",
    "I HAVE TAKEN A NEEDLE FROM THE GUTTER",
    "I PICKED UP ONE NEEDLE FROM THE GUTTER",
    "ONE NEEDLE FROM THE GUTTER IS WITH ME",
    "I CARRY ONE NEEDLE FROM THE GUTTER",
    "IT IS NOT ONE OF MY OWN MAKING",
    "THE NEEDLE IS NOT ONE OF MY OWN MAKING",
    "THE NEEDLE IS NOT OF MY OWN MAKING",
    "IT IS NOT MY OWN MAKING",
    "I HAVE NOT EARNED IT",
    "I KNOW I HAVE NOT EARNED IT",
    "I HAVE NOT MADE IT MYSELF",
    "I HAVE NOT FINISHED MY TEN YEARS",
    "MY TEN YEARS ARE NOT COMPLETE",
    "I HAVE NOT COMPLETED MY TEN YEARS",
    "I HAVE NOT SERVED MY TEN YEARS",
    "FORGIVE ME FOR TAKING IT",
    "FORGIVE ME FOR THE NEEDLE",
    "I AM SORRY FOR THE NEEDLE",
    "I KNOW WHAT THE BARGAIN WAS",
    "I KNOW THE BARGAIN WE MADE",
    "I BREAK OUR BARGAIN",
    "I HAVE BROKEN OUR BARGAIN",
    "I KNOW I BREAK OUR BARGAIN",
    "I COULD NOT WAIT",
    "I COULD NOT WAIT TEN YEARS",
    "THE KNOT WILL NOT WAIT",
    "THE KNOT COULD NOT WAIT",
    "THE ARCHIVE CALLS ME",
    "THE ARCHIVE IS MY TRUE CALLING",
    "THE ARCHIVE IS MY CALLING",
    "THE ARCHIVE IS MY TRUE HOME",
    "I MUST RETURN TO THE ARCHIVE",
    "I AM GOING TO THE ARCHIVE",
    "I GO TO THE ARCHIVE",
    "I GO BACK TO THE ARCHIVE",
    "I RETURN TO THE ARCHIVE",
    "I GO TO FIND THE ARCHIVE",
    "I GO TO FIND THE KNOT",
    "I GO TO FACE THE KNOT",
    "THE KNOT AWAITS ME",
    "THE KNOT AWAITS",
    "THE KNOT STILL AWAITS ME",
    "I WILL UNRAVEL THE KNOT",
    "I MUST UNRAVEL THE KNOT",
    "I WILL TRY THE KNOT",
    "I WILL TEST THE NEEDLE ON THE KNOT",
    "THE NEEDLE WILL MEET THE KNOT",
    "I WILL READ THE KNOT",
    "PELLEGRIN FOUND THE ROUTE",
    "I FOLLOW THE ROUTE TO THE ARCHIVE",
    "THE ROUTE TO THE LOST ARCHIVE",
    "THE LOST ARCHIVE OF PELLEGRIN",
    "TWELVE ARCHIVISTS FAILED",
    "TWELVE TRIED AND FAILED",
    "I WILL BE THE THIRTEENTH",
    "LET ME BE THE THIRTEENTH",
)

REGRETS = (
    "", "MY HAND FALTERS", "BUT MY HAND FALTERS", "AND MY HAND FALTERS",
    "I KNOW THIS IS NOT MY CALLING", "I HAVE MADE MY PEACE",
    "I MADE MY PEACE LONG AGO", "I AM PATIENT BUT NOT FOR THIS",
    "I AM NOT THE CRAFTSMAN YOU ARE", "I WILL NEVER MATCH YOUR HAND",
    "THE WIRE WAS NEVER MINE", "THE FIRE WAS NEVER MINE",
    "I LEARNED TO PURIFY THE METAL", "I LEARNED TO DRAW THE WIRE",
    "YOU SHOWED ME EVERY STEP", "YOU SHOWED ME ALL FOUR STEPS",
    "I REPEATED EACH STEP FOUR TIMES", "THE SAME STEP FOUR TIMES",
    "I ROSE BEFORE THE SUN", "WE ROSE BEFORE THE SUN",
    "EACH NEEDLE DONE BY NOON", "THE WORK DONE BY NOON",
    "THE BARN WAS COLD", "THE BARN IS QUIET",
    "THE INNER DOOR IS OPEN", "YOU OPENED THE INNER DOOR",
    "IT DREW NO BLOOD", "THE PRICK DREW NO BLOOD",
    "SO FINE IT DREW NO BLOOD", "I FELT IT PRICK MY FINGER",
    "YOU MADE ONE EVERY DAY", "YOU LOST COUNT LONG AGO",
    "ONLY THE RESIDUE OF PRACTICE", "THEY WERE ONLY YOUR PRACTICE",
    "I AM GRATEFUL FOR EVERYTHING", "I AM GRATEFUL FOR THE TEN YEARS",
    "I OWE YOU THE TEN YEARS", "I OWE YOU MORE THAN THIS",
    "YOU OWED ME NOTHING", "I OWE YOU TEN YEARS",
    "THANK YOU FOR THE TEN YEARS", "THANK YOU FOR YOUR PATIENCE",
    "DO NOT FOLLOW ME", "DO NOT LOOK FOR ME", "DO NOT SEARCH FOR ME",
    "I WILL NOT RETURN", "I WILL NOT COME BACK", "I AM NOT COMING HOME",
)

CLOSERS = (
    "", "FORGIVE ME", "FAREWELL", "GOODBYE", "YOUR APPRENTICE",
    "YOUR GRATEFUL APPRENTICE", "THE ONE WHO LEFT", "THE ARCHIVIST",
    "THE THIRTEENTH ARCHIVIST", "FAREWELL MY TEACHER", "GOODBYE MASTER",
    "I WILL SEND WORD", "I WILL WRITE AGAIN", "WHEN THE KNOT IS UNDONE",
    "IF I DO NOT RETURN", "WHEN YOU READ THIS I WILL BE GONE",
)


def normalize(text: str) -> str:
    return "".join(re.findall(r"[A-Z]", text.upper()))


def build_openings(length: int = 30) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for sal in SALUTATIONS:
        for tm in TIME_MARKERS:
            for c in CONFESSIONS:
                for prefix in (f"{sal} {tm}".strip(), sal, tm):
                    cand = f"{prefix} {c}".strip() if prefix else c
                    n = normalize(cand)[:length]
                    if len(n) == length and n not in seen:
                        seen.add(n)
                        out.append(n)
    for sal in SALUTATIONS:
        for c in CONFESSIONS:
            for r in REGRETS:
                cand = f"{sal} {c} {r}".strip() if sal else f"{c} {r}".strip()
                n = normalize(cand)[:length]
                if len(n) == length and n not in seen:
                    seen.add(n)
                    out.append(n)
    for c in CONFESSIONS:
        for r in REGRETS:
            for cl in CLOSERS:
                cand = f"{c} {r} {cl}".strip()
                n = normalize(cand)[:length]
                if len(n) == length and n not in seen:
                    seen.add(n)
                    out.append(n)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("output", type=Path)
    ap.add_argument("--length", type=int, default=30)
    args = ap.parse_args()
    openings = build_openings(args.length)
    args.output.write_text("\n".join(openings) + "\n")
    print(f"wrote {len(openings)} distinct {args.length}-letter openings to {args.output}")


if __name__ == "__main__":
    main()
