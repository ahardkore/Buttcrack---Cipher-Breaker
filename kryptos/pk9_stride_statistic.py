#!/usr/bin/env python3
"""The manuscript's one untested proposal, tested: stride-k bigrams.

Context.  PK9's believed structure is plaintext -> double columnar -> Z ->
period-28 additive -> C.  The transposition wall (manuscript ch. 9): any
statistic on Z that ignores positions (letter histogram) survives the
transposition but cannot identify the outer substitution; n-grams identify
but need the transposition first.  Chapter 11's candidate escape: *the inner
text is a columnar permutation of English, so letters adjacent in the
plaintext sit a fixed stride apart in Z -- a statistic on stride-k bigrams
might survive and discriminate.*

This experiment measures, on synthetic instances with known keys:

1. For each stride d, the bigram log-likelihood of the stride-d pair stream
   of Z at the TRUE key vs English bigrams -- does any d carry real signal,
   and how much (bits)?
2. A discrimination A/B: rank the TRUE key among single-coordinate
   substitutions of it by (a) max-over-d stride-bigram likelihood vs
   (b) the plain monogram histogram likelihood.  If (a) ranks the true key
   first more often than (b), the statistic discriminates where the
   histogram does not, and the wall has a door in it.
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kryptos.pk8_calibrated_recovery import encrypt, english_pool  # noqa: E402

W1, H1, W2, H2 = 18, 8, 8, 18
N = 144
P28 = 28


def forward(plain: list[int], p1, p2):
    mid = [plain[r * W1 + p1[c]] for c in range(W1) for r in range(H1)]
    z = [mid[r * W2 + p2[c]] for c in range(W2) for r in range(H2)]
    return z


def bigram_model(path: Path):
    counts = [[1.0] * 26 for _ in range(26)]
    import gzip

    with gzip.open(path, "rt", encoding="ascii") as fh:
        for line in fh:
            g, _, n = line[:-1].partition(" ")
            if len(g) == 2 and g.isalpha():
                counts[ord(g[0]) - 65][ord(g[1]) - 65] += float(n)
    totals = [sum(row) for row in counts]
    return [[math.log(c / t) for c in row] for row, t in zip(counts, totals)]


def stride_loglik(z: list[int], d: int, logb) -> float:
    total = 0.0
    n = 0
    for i in range(len(z) - d):
        total += logb[z[i]][z[i + d]]
        n += 1
    return total / max(n, 1)


def mono_loglik(z: list[int], logu) -> float:
    cnt = Counter(z)
    return sum(c * logu[ch] for ch, c in cnt.items()) / len(z)


def main() -> None:
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    rng = random.Random(9090)
    pool = english_pool()
    big = pool[0]
    ref = Counter("".join(pool))
    tot = sum(ref.values())
    logu = [math.log(max(ref.get(chr(65 + i), 1), 1) / tot) for i in range(26)]
    logb = bigram_model(ROOT / "buttcrack/data/english_bigrams.txt.gz")

    wins_stride, wins_mono = 0, 0
    for trial in range(trials):
        plain = [ord(c) - 65 for c in pool[rng.randrange(len(pool))][:N]]
        p1 = list(range(W1)); rng.shuffle(p1)
        p2 = list(range(W2)); rng.shuffle(p2)
        z = forward(plain, p1, p2)
        s = [rng.randrange(26) for _ in range(P28)]
        c = [(z[t] + s[t % P28]) % 26 for t in range(N)]

        # 1. stride scan at the TRUE key: which strides carry signal?
        z_true = [(c[t] - s[t % P28]) % 26 for t in range(N)]
        best_d = max(range(1, N), key=lambda d: stride_loglik(z_true, d, logb))
        best_ll = stride_loglik(z_true, best_d, logb)
        sig = sum(
            1 for d in range(1, N) if stride_loglik(z_true, d, logb) > -5.2
        )
        if trial == 0:
            print(f"[instance 0] best stride {best_d} ll {best_ll:.3f}; "
                  f"strides above noise: {sig}")

        # 2. discrimination: true key vs 28x25 single-coordinate corruptions + 25 globals
        candidates = []
        wrongs = 0
        for pos in range(P28):
            for dv in (1, 2, -1, -2, 13):
                s2 = list(s)
                s2[pos] = (s2[pos] + dv) % 26
                candidates.append(s2)
                wrongs += 1
        rng.shuffle(candidates)

        def stride_score(sc):
            zc = [(c[t] - sc[t % P28]) % 26 for t in range(N)]
            return max(stride_loglik(zc, d, logb) for d in range(1, 73))

        def mono_score(sc):
            zc = [(c[t] - sc[t % P28]) % 26 for t in range(N)]
            return mono_loglik(zc, logu)

        s_true_stride = stride_score(s)
        s_true_mono = mono_score(s)
        ws = sum(stride_score(sc) > s_true_stride + 1e-12 for sc in candidates)
        wm = sum(mono_score(sc) > s_true_mono + 1e-12 for sc in candidates)
        wins_stride += ws == 0
        wins_mono += wm == 0
        print(f"trial {trial}: wrong keys beating true -> stride-bigram {ws}/{len(candidates)}, "
              f"monogram {wm}/{len(candidates)}", flush=True)

    print(f"true key wins: stride-bigram {wins_stride}/{trials}, monogram {wins_mono}/{trials}")


if __name__ == "__main__":
    main()
