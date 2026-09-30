#!/usr/bin/env python3
"""Calibration: can the sum-clock annealer recover synthetic PK8 instances?

The manuscript records 0/6 synthetic recoveries for greedy+kicks and says the
four-wheel hypothesis {4,5,6,7} has never been confirmed.  Before believing
any negative result on the real PK8 we need a search that provably recovers
synthetic instances of exactly PK8's shape (153 letters, four wheels
{4,5,6,7} over the Kryptos alphabet).  If a calibrated search recovers
synthetics reliably and then fails on the real PK8, the model is wrong, not
the search.

Usage: python3 kryptos/pk8_calibrated_recovery.py [instances] [restarts] [sweeps]
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from buttcrack.ciphers.base import CrackContext  # noqa: E402
from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET, SumClock  # noqa: E402
from buttcrack.lang import get_model  # noqa: E402

PERIODS = [4, 5, 6, 7]
N = 153
IDX = {c: i for i, c in enumerate(KRYPTOS_ALPHABET)}


def english_pool() -> list[str]:
    # Continuous windows of real prose, offsets chosen at random so window
    # boundaries land mid-sentence (like the true PK8 cut presumably does).
    sources = [
        ROOT / "examples/english_samples.txt",
        ROOT / "README.md",
        ROOT / "docs/how-it-works.md",
    ]
    text = "".join(
        "".join(c for c in s.read_text().upper() if "A" <= c <= "Z") for s in sources
    )
    rng = random.Random(7)
    return [text[o : o + N] for o in sorted(rng.sample(range(len(text) - N), 64))]


def encrypt(plain: str, wheels: list[list[int]]) -> str:
    return "".join(
        KRYPTOS_ALPHABET[(IDX[ch] + sum(w[t % len(w)] for w in wheels)) % 26]
        for t, ch in enumerate(plain)
    )


def decrypt(ct: str, wheels: list[list[int]]) -> str:
    return "".join(
        KRYPTOS_ALPHABET[(IDX[ch] - sum(w[t % len(w)] for w in wheels)) % 26]
        for t, ch in enumerate(ct)
    )


def main() -> None:
    rng = random.Random(20260930)
    model = get_model()
    sc = SumClock()
    pool = english_pool()
    print(f"english pool: {len(pool)} windows of {N}")

    n_instances = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    restarts = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    sweeps = int(sys.argv[3]) if len(sys.argv) > 3 else 260

    solved = 0
    for inst in range(n_instances):
        plain = pool[rng.randrange(len(pool))]
        wheels = [[rng.randrange(26) for _ in range(p)] for p in PERIODS]
        ct = encrypt(plain, wheels)
        ctx = CrackContext.create(model=model, budget=3600.0)

        best_fit, best_pt = -1e9, ""
        t0 = time.time()
        for r in range(restarts):
            rw, fit = sc._anneal(
                ct, KRYPTOS_ALPHABET, PERIODS, ctx,
                random.Random(rng.randrange(2**31)), sweeps=sweeps,
            )
            if fit > best_fit:
                best_fit, best_pt = fit, decrypt(ct, rw)
        acc = sum(a == b for a, b in zip(best_pt, plain)) / N
        ok = acc >= 0.99
        solved += ok
        print(f"instance {inst}: fit={best_fit:.4f} acc={acc * 100:.1f}% solved={ok} "
              f"({time.time() - t0:.1f}s)")
        if inst == 0:
            print(f"  truth: {plain[:70]}")
            print(f"  found: {best_pt[:70]}")
    print(f"RECOVERY: {solved}/{n_instances}")


if __name__ == "__main__":
    main()
