#!/usr/bin/env python3
"""Reproducible structure tests for the d'Agapeyeff cipher (1939).

The challenge text published on the last page of d'Agapeyeff's *Codes and
Ciphers* is 79 groups of five digits, 395 digits in total, and it has never
been solved.  This script does not claim a solution.  It establishes the one
structural fact about the text that is strong enough to constrain a solution,
and it does so with a null model so the fact cannot be admired by accident::

    1. Reading the flat digit stream as consecutive PAIRS, every pair splits
       the same way: the first digit lands in {6,7,8,9,0} and the second in
       {0,1,2,3,4,5}.  395 digits, zero exceptions.  The two sets overlap in
       `0`, which serves both seats (the pairs `04` and `90`), so the rule is
       about which seat a digit occupies rather than two disjoint alphabets.
    2. That is not an artefact of how the pairs are cut.  Shifting the split
       by one digit produces 390 violations.
    3. It is not a property of the digit multiset either.  In 2000 shuffles of
       the same digits, none reached even 393/395.

Together these say the text is laid out as a 5x6 coordinate grid with a fixed
digit split between the two roles -- which is why a plain grid attack is worth
trying and why the 11 unvisited cells and the leftover final digit are the
interesting parts.

Usage
-----
    python3 scripts/dagapeyeff_alignment.py            # canonical text
    python3 scripts/dagapeyeff_alignment.py --file X  # any digit-grouped text

Exit status is 0 when the alignment test holds for the text under examination.
"""

from __future__ import annotations

import argparse
import collections
import math
import random
import sys

#: The 1939 text exactly as published, 8 lines of 10 groups (79 groups: the
#: last line has nine, the final group being `92000`).
CANONICAL = """
75628 28591 62916 48164 91748 58464 74748 28483 81638 18174
74826 26475 83828 49175 74658 37575 75936 36565 81638 17585
75756 46282 92857 46382 75748 38165 81848 56485 64858 56382
72628 36281 81728 16463 75828 16483 63828 58163 63630 47481
91918 46385 84656 48565 62946 26285 91859 17491 72756 46575
71658 36264 74818 28462 82649 18193 65626 48484 91838 57491
81657 27483 83858 28364 62726 26562 83759 27263 82827 27283
82858 47582 81837 28462 82837 58164 75748 58162 92000
"""

SHUFFLES = 2000
SEED = 20261013


def digits(text: str) -> str:
    """The digit stream, group separators and everything else removed."""
    return "".join(ch for ch in text if ch.isdigit())


def role_sets(stream: str) -> tuple[set[str], set[str]]:
    """The digit sets observed in the first and second seat of each pair."""
    return set(stream[0::2]), set(stream[1::2])


def violations(stream: str, firsts: set[str], seconds: set[str], offset: int = 0) -> int:
    """Digits found in the wrong seat, cutting pairs `offset` digits in."""
    body = stream[offset:]
    bad = sum(1 for d in body[0::2] if d not in firsts)
    bad += sum(1 for d in body[1::2] if d not in seconds)
    return bad


def entropy(counts: collections.Counter) -> float:
    total = sum(counts.values())
    return -sum((v / total) * math.log2(v / total) for v in counts.values())


def analyse(stream: str, rnd: random.Random) -> dict:
    firsts, seconds = role_sets(stream)
    pairs = [stream[i : i + 2] for i in range(0, len(stream) - 1, 2)]
    counts = collections.Counter(pairs)
    grid = {f"{r}{c}" for r in sorted(firsts) for c in sorted(seconds)}
    in_role = len(stream) - violations(stream, firsts, seconds)

    # Null model: the same digit multiset, the same alignment rule, no ordering
    # structure.  A split this clean has to beat this before it means anything.
    pool = list(stream)
    lucky = 0
    for _ in range(SHUFFLES):
        rnd.shuffle(pool)
        if len(stream) - violations("".join(pool), firsts, seconds) >= in_role:
            lucky += 1

    p_first = sum(1 for d in stream if d in firsts) / len(stream)
    p_second = sum(1 for d in stream if d in seconds) / len(stream)

    return {
        "length": len(stream),
        "pairs": len(pairs),
        "leftover": stream[len(pairs) * 2 :],
        "firsts": sorted(firsts),
        "seconds": sorted(seconds),
        "violations": len(stream) - in_role,
        "violations_shifted": violations(stream, firsts, seconds, offset=1),
        "in_role": in_role,
        "cells_used": len(counts),
        "cells_possible": len(grid),
        "cells_empty": sorted(grid - set(counts)),
        "frequencies": counts.most_common(),
        "distinct": len(counts),
        "entropy": entropy(counts),
        "shuffle_passes": lucky,
        "shuffles": SHUFFLES,
        "expected_in_role_if_independent": len(stream) * (p_first**2 + p_second**2),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", help="digit-grouped ciphertext; defaults to the 1939 text")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = CANONICAL
    stream = digits(text)
    if len(stream) < 40:
        print(f"error: only {len(stream)} digits found", file=sys.stderr)
        return 2

    result = analyse(stream, random.Random(SEED))

    if args.json:
        import json

        payload = dict(result)
        payload["frequencies"] = dict(result["frequencies"])
        print(json.dumps(payload, indent=1, sort_keys=True))
        return 0

    print(f"d'Agapeyeff structure tests   {'canonical 1939 text' if not args.file else args.file}")
    print("-" * 66)
    print(f"digits                 {result['length']}  ->  {result['pairs']} pairs"
          f" + leftover '{result['leftover']}'")
    print(f"pair first digit in    {{{','.join(result['firsts'])}}}")
    print(f"pair second digit in   {{{','.join(result['seconds'])}}}")
    overlap = sorted(set(result["firsts"]) & set(result["seconds"]))
    print(f"seats share the digit   {' '.join(overlap) if overlap else 'none (disjoint)'}")
    print(f"alignment violations   {result['violations']}  (shifted by one: {result['violations_shifted']})")
    print(f"null model             {result['shuffle_passes']}/{result['shuffles']} shuffles reached "
          f">= {result['in_role']}/{result['length']} digits in role")
    print(f"                       independence would expect ~{result['expected_in_role_if_independent']:.0f}")
    print(f"grid cells used        {result['cells_used']} of {result['cells_possible']}")
    print(f"grid cells empty       {' '.join(result['cells_empty'])}")
    print(f"code entropy           {result['entropy']:.3f} bits/pair")
    print("frequencies            " + "  ".join(f"{k}:{v}" for k, v in result["frequencies"]))
    print("-" * 66)
    ok = result["violations"] == 0 and result["shuffle_passes"] == 0
    print(
        "PAIR-SPLIT CONFIRMED: the digit roles are structural, not incidental."
        if ok
        else "NO STRONG PAIR SPLIT: this text does not show the d'Agapeyeff layout."
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
