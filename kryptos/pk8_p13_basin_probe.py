#!/usr/bin/env python3
"""Basin probe, take two: the residual 13-ary problem.

With the plaintext's parity stream fixed (the parity sieve's output), each
wheel value is constrained to one of two parity classes, i.e. 13 values
instead of 26 -- equivalently one Z13 dial per wheel slot.  Is the quadgram
landscape over those Z13 dials any kinder than the Z26 one?  Corrupt k of
the 20 free dials (q4[1..3], q5, q6, q7; q4[0] frozen as gauge) from the
true wheels of a synthetic instance and measure recovery by coordinate
ascent, exactly like kryptos/pk8_basin_probe.py did for the full problem.

If the radius is wide (say >= 8), a Z13 SA with a decent budget can cross
the gap from a random start, and the parity sieve + this stage solves PK8.
If the radius is ~3 again, the barrier is fundamental to the problem class
and the frontier documentation is the honest finish.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from buttcrack.ciphers.base import CrackContext  # noqa: E402
from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET, SumClock  # noqa: E402
from buttcrack.lang import get_model  # noqa: E402
from kryptos.pk8_calibrated_recovery import N, PERIODS, decrypt, encrypt, english_pool  # noqa: E402

# free dials: (wheel, slot) with slot>0 for wheel 0, all slots for wheels 1..3
DIALS = [(w, s) for w, p in enumerate(PERIODS) for s in range(p) if not (w == 0 and s == 0)]


def ascend13(ct: str, wheels: list[list[int]], parity_p: list[list[int]],
             model, rng) -> tuple[list[list[int]], float]:
    """Coordinate ascent where each dial lives in a fixed parity class.

    wheels[w][s] = parity_p[w][s] + 2*x mod 26 ; x in 0..12 ; frozen q4[0]=0.
    Scored by the quadgram model through search_fitness.
    """
    sc = SumClock()
    ctx = CrackContext.create(model=model, budget=360000.0)
    best = ctx.model.search_fitness(decrypt(ct, wheels))
    improved = True
    guard = 0
    while improved and guard < 40:
        improved = False
        guard += 1
        order = DIALS[:]
        rng.shuffle(order)
        for w, s in order:
            cur_val = wheels[w][s]
            par = parity_p[w][s]
            x0 = ((cur_val - par) % 26) // 2
            bestv, bestf = x0, best
            for x in range(13):
                if x == x0:
                    continue
                wheels[w][s] = (par + 2 * x) % 26
                f = ctx.model.search_fitness(decrypt(ct, wheels))
                if f > bestf:
                    bestf, bestv = f, x
            wheels[w][s] = (par + 2 * bestv) % 26
            if bestf > best + 1e-9:
                best, improved = bestf, True
    return wheels, best


def main() -> None:
    ks = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else [3, 5, 7, 9, 11, 13]
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    rng = random.Random(60221023)
    model = get_model()
    pool = english_pool()

    for k in ks:
        recovered = 0
        fits = []
        for _ in range(trials):
            plain = pool[rng.randrange(len(pool))]
            wheels = [[rng.randrange(26) for _ in range(p)] for p in PERIODS]
            parity_p = [[v & 1 for v in wheel] for wheel in wheels]
            ct = encrypt(plain, wheels)
            # gauge-normalise truth into the frozen-q4[0]=0 class
            shift = wheels[0][0] & ~1 or 0  # keep parity of class; exact gauge not needed for probing
            trial_wheels = [list(wheel) for wheel in wheels]
            for w, s in rng.sample(DIALS, k):
                v = trial_wheels[w][s]
                par = v & 1
                x = ((v - par) % 26) // 2
                x = (x + rng.randrange(1, 13)) % 13
                trial_wheels[w][s] = (par + 2 * x) % 26
            rw, fit = ascend13(ct, trial_wheels, parity_p, model, rng)
            pt = decrypt(ct, rw)
            acc = sum(a == b for a, b in zip(pt, plain)) / N
            fits.append(fit)
            recovered += acc >= 0.99
        print(f"k={k:2d}: recovered {recovered}/{trials}  median fit {sorted(fits)[len(fits)//2]:.4f}",
              flush=True)


if __name__ == "__main__":
    main()
