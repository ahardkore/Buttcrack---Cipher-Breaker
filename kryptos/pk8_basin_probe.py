#!/usr/bin/env python3
"""Basin probe: how wide is the attraction basin of the true PK8 wheels?

Start at the true wheels of a synthetic {4,5,6,7} instance, corrupt k wheel
coordinates at random, then run exact coordinate ascent.  If ascent recovers
the truth for large k, the failure of blind search is exploration (fixable
with restarts/annealing).  If even k=2 fails, the true key is a narrow spike
in a flat landscape and no local method can work -- the negative result on the
real PK8 would then be uninformative either way.
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


def main() -> None:
    ks = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else [1, 2, 3, 4, 6, 8]
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    rng = random.Random(4242)
    model = get_model()
    sc = SumClock()
    pool = english_pool()

    for k in ks:
        recovered = 0
        fits = []
        for _ in range(trials):
            plain = pool[rng.randrange(len(pool))]
            wheels = [[rng.randrange(26) for _ in range(p)] for p in PERIODS]
            ct = encrypt(plain, wheels)
            # corrupt k distinct coordinates
            coords = [(w, s) for w, p in enumerate(PERIODS) for s in range(p)]
            for w, s in rng.sample(coords, k):
                v = wheels[w][s]
                wheels[w][s] = (v + rng.randrange(1, 26)) % 26
            ctx = CrackContext.create(model=model, budget=3600.0)
            rw, fit = sc._ascend(ct, KRYPTOS_ALPHABET, PERIODS, ctx, rng, wheels=wheels)
            pt = decrypt(ct, rw)
            acc = sum(a == b for a, b in zip(pt, plain)) / N
            fits.append(fit)
            recovered += acc >= 0.99
        print(f"k={k:2d}: recovered {recovered}/{trials}  median fit {sorted(fits)[len(fits)//2]:.4f}")


if __name__ == "__main__":
    main()
