#!/usr/bin/env python3
"""PK10 stage 1, synthetic calibration: monogram clock recovery.

PK10's model is a 3-clock {7,8,9} (lcm = 504 = N, one full cycle) under an
outer transposition.  A transposition cannot change *which* letters occur,
so the wheels can be attacked with transposition-invariant statistics --
monogram log-likelihood / IoC -- with no need to solve the transposition
first.  Measure on synthetic instances (English -> wheels -> columnar
transpose -> ciphertext) whether monogram coordinate descent recovers the
true wheels, and at what accuracy, before trusting any result on the real
PK10.
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kryptos.pk8_calibrated_recovery import english_pool  # noqa: E402

PERIODS = [7, 8, 9]
N = 504


def encrypt_std(plain: str, wheels: list[list[int]]) -> list[int]:
    return [
        (ord(ch) - 65 + sum(w[t % len(w)] for w in wheels)) % 26
        for t, ch in enumerate(plain)
    ]


def monogram_loglik(letters: list[int], logref: list[float]) -> float:
    counts = Counter(letters)
    return sum(c * logref[ch] for ch, c in counts.items())


def columnar_scramble(text: str, w: int, rng: random.Random) -> str:
    h = len(text) // w
    perm = list(range(w))
    rng.shuffle(perm)
    rows = [text[r * w : (r + 1) * w] for r in range(h)]
    return "".join(rows[r][perm[c]] for c in range(w) for r in range(h))


def main() -> None:
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    rng = random.Random(777001)
    pool = english_pool()

    # longer windows for N=504: pool windows are 153; stitch four different ones
    # reference frequencies from the same corpus
    big = "".join(pool)
    ref = Counter(big)
    total = sum(ref.values())
    logref = [math.log(max(ref.get(chr(65 + i), 1), 1) / total) for i in range(26)]

    solved = 0
    for trial in range(trials):
        plain = "".join(rng.choice(pool) for _ in range(4))[:N]
        wheels = [[rng.randrange(26) for _ in range(p)] for p in PERIODS]
        # gauge: fixing q7[0] loses no generality?  keep full truth for scoring
        z = encrypt_std(plain, wheels)
        ct_str = "".join(chr(65 + v) for v in z)
        ct = columnar_scramble(ct_str, 12, rng)
        ct_idx = [ord(c) - 65 for c in ct]

        # coordinate descent on monogram log-likelihood (transposition-proof)
        w_try = [[rng.randrange(26) for _ in range(p)] for p in PERIODS]
        best = -1e18

        def score(ws):
            return monogram_loglik(
                [(c - (ws[0][t % 7] + ws[1][t % 8] + ws[2][t % 9])) % 26 for t, c in enumerate(ct_idx)],
                logref,
            )

        cur = score(w_try)
        improved, guard = True, 0
        while improved and guard < 30:
            improved, guard = False, guard + 1
            for wi, p in enumerate(PERIODS):
                for s in range(p):
                    orig = w_try[wi][s]
                    bv, bf = orig, cur
                    for v in range(26):
                        if v == orig:
                            continue
                        w_try[wi][s] = v
                        f = score(w_try)
                        if f > bf:
                            bf, bv = f, v
                    w_try[wi][s] = bv
                    if bf > cur + 1e-9:
                        cur, improved = bf, True
        # accuracy via detransposed plaintext is impossible here (scramble is
        # part of the instance); measure wheel agreement instead: decode the
        # unscrambled z and compare letters
        z_dec = "".join(
            chr(65 + (z[t] - (w_try[0][t % 7] + w_try[1][t % 8] + w_try[2][t % 9])) % 26)
            for t in range(N)
        )
        acc = sum(a == b for a, b in zip(z_dec, plain)) / N
        ok = acc >= 0.99
        solved += ok
        print(f"trial {trial}: monogram-descent wheel accuracy {acc * 100:.1f}% solved={ok}", flush=True)
    print(f"PK10-STAGE1 RECOVERY: {solved}/{trials}")


if __name__ == "__main__":
    main()
