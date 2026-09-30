#!/usr/bin/env python3
"""Wiring check + posterior trace for the EM-DA solver.

1. Emission wiring: with the theta distributions pinned at the TRUE wheels,
   run one forward-backward pass and check the posterior letter at each
   position peaks at the true plaintext letter (should be ~100%).
2. Identifiability trace: run EM-DA on a synthetic instance and report,
   per iteration, the mean posterior mass on the true letter and the hard
   wheel accuracy -- tells us whether the loop converges to truth or drifts.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kryptos.pk8_calibrated_recovery import PERIODS, decrypt, encrypt, english_pool  # noqa: E402
from kryptos.pk8_emda import A26, EMDA, LETTER_OF, load_bigrams  # noqa: E402
from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET  # noqa: E402


def main() -> None:
    rng = random.Random(555)
    pool = english_pool()
    plain = pool[rng.randrange(len(pool))]
    wheels = [[rng.randrange(26) for _ in range(p)] for p in PERIODS]
    ct = encrypt(plain, wheels)
    print(f"truth  : {plain[:72]}")
    print(f"wheels : {wheels}")

    logp, logu = load_bigrams(ROOT / "buttcrack/data/english_bigrams.txt.gz")
    idx = {c: i for i, c in enumerate(KRYPTOS_ALPHABET)}
    ct_idx = [idx[c] for c in ct]
    letters = [ord(c) - 65 for c in plain]

    # -- 1. emission wiring with pinned-true wheels --------------------------
    em = EMDA(ct_idx, logp, logu, PERIODS, rng)
    for w, p in enumerate(PERIODS):
        for s in range(p):
            em.theta[w][s] = [0.0] * A26
            em.theta[w][s][wheels[w][s]] = 1.0
    em.update_emissions(1.0)
    em.forward_backward()
    hits = sum(em.gamma[t].index(max(em.gamma[t])) == letters[t] for t in range(em.n))
    mass = sum(em.gamma[t][letters[t]] for t in range(em.n)) / em.n
    print(f"pinned-true wheels: posterior argmax hits {hits}/{em.n}, mean true-mass {mass:.3f}")

    # -- 2. identifiability trace ---------------------------------------------
    em2 = EMDA(ct_idx, logp, logu, PERIODS, rng)
    for it in range(80):
        beta = min(1.0, 0.15 * (1.08 ** it))
        temp = max(0.05, 1.0 * (0.97 ** it))
        em2.update_emissions(beta)
        em2.forward_backward()
        em2.m_step(temp)
        if it % 10 == 9:
            tm = sum(em2.gamma[t][letters[t]] for t in range(em2.n)) / em2.n
            hw = em2.hard_wheels()
            pt = decrypt(ct, hw)
            acc = sum(a == b for a, b in zip(pt, plain)) / len(plain)
            print(f"iter {it + 1:3d} beta={beta:.2f} temp={temp:.2f} true-mass={tm:.3f} pt-acc={acc * 100:.0f}%")


if __name__ == "__main__":
    main()
