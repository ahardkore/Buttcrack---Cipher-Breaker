#!/usr/bin/env python3
"""Find PK9 wheel triples with PK8-like word structure.

This is a candidate generator, not a solver.  It deliberately does not claim
that related words are keys; it narrows the dictionary search to triples that
share an insertion/edit relationship, while retaining every candidate for
reproducibility.
"""
from __future__ import annotations
import argparse
from pathlib import Path


def load(path: Path) -> list[str]:
    return sorted({x.strip().upper() for x in path.read_text().splitlines()
                   if x.strip().isalpha() and 5 <= len(x.strip()) <= 7})


def subseq(a: str, b: str) -> bool:
    it = iter(b)
    return all(c in it for c in a)


def edit_distance(a: str, b: str) -> int:
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        new = [i]
        for j, y in enumerate(b, 1):
            new.append(min(new[-1] + 1, row[j] + 1,
                           row[j - 1] + (x != y)))
        row = new
    return row[-1]


def related(a: str, b: str) -> bool:
    # PK8's METE -> METER -> METIER relation is an insertion/extension
    # relation, but allow a small edit distance for a different word family.
    return (subseq(a, b) or subseq(b, a) or edit_distance(a, b) <= 2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("v5", type=Path)
    ap.add_argument("v6", type=Path)
    ap.add_argument("v7", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    w5, w6, w7 = map(load, (args.v5, args.v6, args.v7))
    pairs56 = [(a, b) for a in w5 for b in w6 if related(a, b)]
    pairs67 = {(b, c) for b in w6 for c in w7 if related(b, c)}
    triples = [(a, b, c) for a, b in pairs56 for c in w7
               if (b, c) in pairs67]
    args.out.write_text("\n".join("%s %s %s" % t for t in triples) +
                       ("\n" if triples else ""))
    print(f"5-wheel words: {len(w5)}")
    print(f"6-wheel words: {len(w6)}")
    print(f"7-wheel words: {len(w7)}")
    print(f"related 5/6 pairs: {len(pairs56)}")
    print(f"related 6/7 pairs: {len(pairs67)}")
    print(f"structured triples: {len(triples)}")
    print(f"wrote: {args.out}")


if __name__ == "__main__":
    main()
