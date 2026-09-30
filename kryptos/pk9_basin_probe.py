#!/usr/bin/env python3
"""Basin probe for the PK9 joint problem.

pk9_sa_cal2.c run #1 failed to recover a synthetic instance (best fit -4.86
vs truth -4.05).  Why - budget or geometry?  Same question the
pk8_basin_probe answered for PK8: start at the true (p1, p2, shifts) of a
synthetic instance, corrupt k coordinates (column swaps in p1/p2, shifts
re-drawn), and see whether greedy descent (28-shift coordinate sweep + full
swap-descent on the permutations) finds the truth again.  If even k = 3-4
fails, the landscape is needle-shaped and no amount of annealing budget
matters; if k ~ 10 recovers, joint SA just needs to be lucky once.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from buttcrack.ciphers.base import CrackContext  # noqa: E402
from buttcrack.lang import get_model  # noqa: E402
from kryptos.pk8_calibrated_recovery import english_pool  # noqa: E402

W1, H1, W2, H2, P28, N = 18, 8, 8, 18, 28, 144


def forward(plain: list[int], p1, p2, s):
    mid = [plain[r * W1 + p1[c]] for c in range(W1) for r in range(H1)]
    z = [mid[r * W2 + p2[c]] for c in range(W2) for r in range(H2)]
    return [(z[t] + s[t % P28]) % 26 for t in range(N)]


def invert(ct, p1, p2, s):
    z = [(ct[t] - s[t % P28]) % 26 for t in range(N)]
    mid = [0] * N
    idx = 0
    for c in range(W2):
        for r in range(H2):
            mid[r * W2 + p2[c]] = z[idx]
            idx += 1
    pt = [0] * N
    idx = 0
    for c in range(W1):
        for r in range(H1):
            pt[r * W1 + p1[c]] = mid[idx]
            idx += 1
    return pt


def score(ct, p1, p2, s, ctx) -> float:
    pt = invert(ct, p1, p2, s)
    return ctx.model.search_fitness("".join(chr(65 + v) for v in pt))


def greedy(ct, p1, p2, s, ctx, rng):
    best = score(ct, p1, p2, s, ctx)
    improved, guard = True, 0
    while improved and guard < 20:
        improved, guard = False, guard + 1
        for c in range(P28):
            orig = s[c]
            bv, bf = orig, best
            for v in range(26):
                if v == orig:
                    continue
                s[c] = v
                f = score(ct, p1, p2, s, ctx)
                if f > bf:
                    bf, bv = f, v
            s[c] = bv
            if bf > best + 1e-9:
                best, improved = bf, True
        for perm, w in ((p2, W2), (p1, W1)):
            for a in range(w):
                for b in range(a + 1, w):
                    perm[a], perm[b] = perm[b], perm[a]
                    f = score(ct, p1, p2, s, ctx)
                    if f > best + 1e-9:
                        best, improved = f, True
                    else:
                        perm[a], perm[b] = perm[b], perm[a]
    return p1, p2, s, best


def main() -> None:
    ks = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else [2, 3, 4, 6, 8]
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    rng = random.Random(1717)
    model = get_model()
    ctx = CrackContext.create(model=model, budget=360000.0)
    pool = english_pool()

    for k in ks:
        recovered = 0
        fits = []
        for _ in range(trials):
            plain = [ord(c) - 65 for c in pool[rng.randrange(len(pool))][:N]]
            p1 = list(range(W1)); rng.shuffle(p1)
            p2 = list(range(W2)); rng.shuffle(p2)
            s = [rng.randrange(26) for _ in range(P28)]
            ct = forward(plain, p1, p2, s)
            t1, t2, ts = list(p1), list(p2), list(s)
            # corrupt: k times either a p1 swap, a p2 swap, or a shift re-draw
            for _c in range(k):
                what = rng.randrange(3)
                if what == 0:
                    a, b = rng.sample(range(W1), 2)
                    t1[a], t1[b] = t1[b], t1[a]
                elif what == 1:
                    a, b = rng.sample(range(W2), 2)
                    t2[a], t2[b] = t2[b], t2[a]
                else:
                    ts[rng.randrange(P28)] = rng.randrange(26)
            r1, r2, rs, fit = greedy(ct, t1, t2, ts, ctx, rng)
            pt = invert(ct, r1, r2, rs)
            acc = sum(a == b for a, b in zip(pt, plain)) / N
            fits.append(fit)
            recovered += acc >= 0.99
        print(f"k={k:2d}: recovered {recovered}/{trials}  median fit {sorted(fits)[len(fits)//2]:.4f}",
              flush=True)


if __name__ == "__main__":
    main()
