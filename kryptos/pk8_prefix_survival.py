#!/usr/bin/env python3
"""Does the true opening survive a quadgram beam?  (measurement before code)

The full-product annihilator of periods {4,5,6,7},

    prod_i (1 - E^p_i)  =  sum_S (-1)^|S| E^(sum S)      (degree 22, lead +1)

kills the key, so given any 22 consecutive plaintext letters the rest of the
message to the right is FORCED, letter by letter.  PK8 then reduces to
finding its first 22 letters -- provided a quadgram-scored left-to-right
beam keeps the true prefix until the deterministic tail can score it.

This script measures, on synthetic instances with known plaintexts, the beam
width at which the true prefix survives all levels 4..22.  If survival needs
only modest widths, a C beam that scores the *full* forced text will find
PK8's opening cheaply; if survival needs astronomical widths, the beam idea
is dead on arrival and must not be built.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kryptos.pk8_calibrated_recovery import N, PERIODS, encrypt, english_pool  # noqa: E402

FLOOR = -9.5


def load_quads(path: Path) -> dict[str, float]:
    table: dict[str, float] = {}
    with open(path) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) == 2 and len(parts[0]) == 4:
                table[parts[0]] = float(parts[1])
    return table


def beam_survival(quad: dict[str, float], true_open: str, width: int) -> tuple[bool, int]:
    """Beam over openings; returns (survived, first level where it died).

    Candidates are (score, string).  Score = sum of quadgram values so far.
    The beam keeps `width` best after each level; we check whether the true
    opening's current prefix is still in the beam.
    """
    candidates: dict[str, float] = {c: 0.0 for c in
                                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}
    for level in range(2, 23):
        nxt: dict[str, float] = {}
        for stem, sc in candidates.items():
            for k in range(26):
                ch = chr(65 + k)
                s2 = stem + ch
                add = 0.0
                if len(s2) >= 4:
                    add = quad.get(s2[-4:], FLOOR)
                nxt[s2] = sc + add
        if len(nxt) > width:
            # keep top `width`
            nxt = dict(sorted(nxt.items(), key=lambda kv: -kv[1])[:width])
        if true_open[:level] not in nxt:
            return False, level
        candidates = nxt
    return True, 23


def main() -> None:
    quad = load_quads(ROOT / "kryptos/english_quads.tsv")
    pool = english_pool()
    rng = random.Random(11)
    width = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 8

    survived = 0
    for i in range(trials):
        plain = pool[rng.randrange(len(pool))]
        ok, died = beam_survival(quad, plain[:22], width)
        survived += ok
        print(f"instance {i}: open={plain[:22]!r} survived={ok}"
              + ("" if ok else f" (died at level {died})"), flush=True)
    print(f"SURVIVAL at width {width}: {survived}/{trials}")


if __name__ == "__main__":
    main()
