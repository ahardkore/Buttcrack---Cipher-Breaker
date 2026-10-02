#!/usr/bin/env python3
"""generate_pk9_letter_v2.py — PK9 crib corpus v2: missing opening framings.

PK9 is the narrator's short farewell letter to the Whitesmith (PK8: "I leave
the Whitesmith a short letter").  The v1 corpus covered salutations, ten-years
time markers, and bargain/needle confessions, but MISSED:

  - "THREE WEEKS IN" — the author's time-marker series (PK3 "Seventh month.",
    PK4 "Two years in.", PK5 "Fourteen days in the barn.", PK7 "Three weeks
    in.") makes this the single most likely opening for a note written at the
    end of the three weeks;
  - classic letter openers: "By the time you read this", "When you read
    this", "I am writing this", "My last night", "Thank you", "I will miss",
    "I will never forget", candlelight/lamplight atmosphere;
  - workshop imagery continuations from the verified PK6-PK8 vocabulary.

Each crib is >= 30 letters.  Output: one crib per line, deduped.
"""
from __future__ import annotations

import argparse
from pathlib import Path

THREE_WEEK_CONT = (
    "I WRITE THIS BY CANDLELIGHT", "THE WORKSHOP IS QUIET", "YOU ARE ASLEEP",
    "THE FORGE IS COLD", "THE BARN IS DARK", "I HAVE LEARNED ENOUGH",
    "I HAVE LEARNED NOTHING", "I KNOW WHAT THE BARGAIN WAS",
    "I HAVE NOT KEPT OUR BARGAIN", "I BREAK OUR BARGAIN TONIGHT",
    "I HAVE TAKEN ONE NEEDLE", "I TOOK ONE NEEDLE", "THE NEEDLE IS IN MY BAG",
    "MY HAND STILL FALTERS", "MY HAND NO LONGER FALTERS",
    "YOU TAUGHT ME THE FOUR STEPS", "YOU SHOWED ME EVERY STEP",
    "EACH NEEDLE IS DONE BY NOON", "WE ROSE BEFORE THE SUN",
    "I ROSE BEFORE THE SUN", "THE METAL IS PURIFIED", "THE WIRE IS DRAWN",
    "THE GUTTER IS FULL OF NEEDLES", "THE GUTTER RUNS WITH NEEDLES",
    "I AM NOT THE CRAFTSMAN YOU ARE", "I KNOW THIS IS NOT MY CALLING",
    "THE ARCHIVE IS MY TRUE CALLING", "THE KNOT AWAITS ME",
    "THE KNOT WILL NOT WAIT", "I MUST RETURN TO THE ARCHIVE",
    "I GO HOME TOMORROW", "I LEAVE AT MIDNIGHT", "I LEFT AT MIDNIGHT",
    "FORGIVE ME FOR LEAVING", "FORGIVE ME FOR THE NEEDLE",
    "I AM GRATEFUL FOR EVERYTHING", "I AM GRATEFUL FOR THE THREE WEEKS",
    "I AM GRATEFUL FOR THE TEN YEARS", "THANK YOU FOR YOUR PATIENCE",
    "THANK YOU FOR EVERY LESSON", "I OWE YOU TEN YEARS",
    "I OWE YOU MORE THAN A LETTER", "YOU WILL MAKE ONE EVERY DAY",
    "YOU MADE ONE EVERY DAY AND LOST COUNT",
    "THEY WERE ONLY THE RESIDUE OF PRACTICE",
    "ONE NEEDLE IS ONLY THE RESIDUE OF PRACTICE",
    "IT DREW NO BLOOD", "THE PRICK DREW NO BLOOD",
    "SO FINE IT PIERCED GLASS", "SO FINE IT SPLIT A HAIR",
    "I WISH I COULD STAY", "I CANNOT STAY", "I CANNOT WAIT TEN YEARS",
    "I COULD NOT WAIT TEN YEARS", "THE FIRE WAS NEVER MINE",
    "THE WIRE WAS NEVER MINE", "I HAVE MADE MY PEACE",
    "I MADE MY PEACE WITH IT", "THIS IS NOT MY CALLING",
    "I WILL SEND WORD FROM THE ARCHIVE", "I WILL WRITE FROM THE ARCHIVE",
    "REMEMBER THE BARGAIN WAS TEN YEARS", "THE BARGAIN WAS TEN YEARS",
    "TEN YEARS THEN ONE OF MY OWN MAKING", "I HAVE TAKEN ONE OF MY OWN MAKING",
    "IT IS NOT ONE OF MY OWN MAKING", "I HAVE NOT EARNED A NEEDLE",
    "I HAVE NOT FINISHED MY TEN YEARS", "MY TEN YEARS ARE NOT DONE",
    "KEEP THE NEEDLES COMING", "I LEARNED TO PURIFY THE METAL",
    "I LEARNED TO DRAW THE WIRE", "I WILL TRY THE NEEDLE ON THE KNOT",
    "THE NEEDLE WILL MEET THE KNOT", "I FOLLOW THE ROUTE TO THE ARCHIVE",
    "PELLEGRIN FOUND THE ROUTE", "THE LOST ARCHIVE OF PELLEGRIN",
)

OPENERS = (
    "BY THE TIME YOU READ THIS I WILL HAVE LEFT",
    "BY THE TIME YOU READ THIS I AM GONE",
    "BY THE TIME YOU READ THIS I WILL BE GONE",
    "BY THE TIME YOU READ THIS THE BARN WILL BE EMPTY",
    "BY THE TIME YOU READ THIS I WILL HAVE TAKEN",
    "WHEN YOU READ THIS I WILL BE GONE",
    "WHEN YOU READ THIS I AM ALREADY GONE",
    "WHEN YOU READ THIS I WILL HAVE LEFT",
    "WHEN YOU READ THIS THE NEEDLE IS GONE",
    "I AM WRITING THIS BY CANDLElight".upper().replace("CANDLELIGHT", "CANDLELIGHT"),
    "I AM WRITING THIS IN THE BARN",
    "I AM WRITING THIS AT MIDNIGHT",
    "I AM WRITING THIS BY THE GUTTER",
    "I AM WRITING MY LAST LETTER",
    "I WRITE THIS BY CANDLELIGHT",
    "I WRITE THIS BY LAMPLIGHT",
    "I WRITE THIS BY THE LIGHT OF THE FORGE",
    "I WRITE THIS ON MY LAST NIGHT",
    "I WRITE THIS LAST LETTER AT MIDNIGHT",
    "MY LAST NIGHT IN THE WORKSHOP",
    "MY LAST NIGHT IN THE BARN",
    "MY LAST NIGHT BY THE FORGE",
    "MY LAST MORNING IN THE BARN",
    "THE CANDLE IS BURNING LOW",
    "THE LAMP IS BURNING LOW",
    "THE FORGE HAS GONE COLD",
    "THE LAST NEEDLE IS DONE",
    "THE LAST NEEDLE OF THE YEAR IS DONE",
    "THANK YOU FOR THE THREE WEEKS",
    "THANK YOU FOR THE TEN YEARS",
    "THANK YOU FOR YOUR PATIENCE",
    "THANK YOU FOR EVERY LESSON",
    "THANK YOU FOR EVERY NEEDLE",
    "THANK YOU FOR THE ROOF AND THE FIRE",
    "I WILL MISS THE SMELL OF THE METAL",
    "I WILL MISS THE SOUND OF THE ANVIL",
    "I WILL MISS THE QUIET OF THE BARN",
    "I WILL MISS THE GUTTER NEEDLES",
    "I WILL NEVER FORGET THE FOUR STEPS",
    "I WILL NEVER FORGET YOUR PATIENCE",
    "I WILL NEVER FORGET THE THREE WEEKS",
    "I WILL NEVER FORGET THE GUTTER",
)

OPENER_CONT = (
    "", "AND THE BARN", "AND THE FORGE", "AND THE GUTTER", "AND THE NEEDLES",
    "I AM GRATEFUL", "I AM SORRY", "FORGIVE ME", "THE NEEDLE IS WITH ME",
    "I HAVE TAKEN ONE NEEDLE", "THE ARCHIVE CALLS ME", "THE KNOT AWAITS",
    "I MUST GO HOME", "I MUST RETURN", "I GO TO THE ARCHIVE",
    "I CANNOT WAIT TEN YEARS", "I HAVE NOT KEPT OUR BARGAIN",
)

CONFESSION_TAILS = (
    "IT IS NOT ONE OF MY OWN MAKING",
    "I HAVE NOT EARNED IT",
    "I HAVE NOT FINISHED MY TEN YEARS",
    "FORGIVE ME FOR TAKING IT",
    "I AM GRATEFUL FOR EVERYTHING",
    "THE ARCHIVE IS MY TRUE CALLING",
    "THE KNOT AWAITS ME",
    "I WILL UNRAVEL THE KNOT",
    "I AM NOT THE CRAFTSMAN YOU ARE",
    "MY HAND STILL FALTERS",
    "I HAVE MADE MY PEACE",
)


def norm(s: str) -> str:
    return "".join(c for c in s.upper() if "A" <= c <= "Z")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("outfile")
    ap.add_argument("--length", type=int, default=30)
    ap.add_argument("--exclude", default="/tmp/pk9_letter30_corrected.txt",
                    help="skip cribs already present in this file")
    args = ap.parse_args()

    old = set()
    if args.exclude:
        p = Path(args.exclude)
        if p.exists():
            old = {l.strip() for l in p.read_text().splitlines() if l.strip()}

    cribs = set()

    def add(*parts):
        s = norm(" ".join(x for x in parts if x))
        while len(s) >= args.length:
            cribs.add(s[: max(args.length, 30)])
            return
        if len(s) >= 20:
            cribs.add(s)

    # "Three weeks in" + continuations (+ optional tails)
    for c in THREE_WEEK_CONT:
        add("THREE WEEKS IN", c)
        for t in CONFESSION_TAILS[:6]:
            add("THREE WEEKS IN", c, t)
    # openers (+ continuations)
    for o in OPENERS:
        add(o)
        for c in OPENER_CONT:
            add(o, c)
    # opener + needle confession core (most likely single content)
    CORE = "I HAVE TAKEN ONE NEEDLE FROM THE GUTTER"
    for o in OPENERS:
        add(o, CORE)
        add(o, CORE, "IT IS NOT ONE OF MY OWN MAKING")
    # bare cores
    for t in CONFESSION_TAILS:
        add(CORE, t)

    new = sorted(c for c in cribs if c not in old)
    Path(args.outfile).write_text("\n".join(new) + "\n")
    print(f"wrote {len(new)} new cribs ({len(cribs)} generated, "
          f"{len(cribs) - len(new)} already in v1) to {args.outfile}")


if __name__ == "__main__":
    main()
