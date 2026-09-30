#!/usr/bin/env python3
"""Mean-field EM with deterministic annealing for sum-clock ciphers.

Greedy ascent and plain simulated annealing cannot recover a four-wheel
{4,5,6,7} key from 153 letters: the basin probe (pk8_basin_probe.py) shows
the true key only attracts within ~3 of 22 coordinates, and blind search
lands nothing close.  The same probe explains why: a wheel's value is
invisible until the other three are nearly right, so the landscape is flat
until it is not.

The way out is to keep the key *soft*.  Each wheel slot is a distribution
over Z/26.  The plaintext is then a distribution too, so we can ask a
bigram language model for per-position letter posteriors (forward-backward),
then set each wheel slot to the distribution that best explains those
posteriors (mean-field M step), and iterate while slowly sharpening the
emissions (deterministic annealing).  Flat landscapes become smooth at high
temperature; the algorithm follows the optimum as the landscape hardens.

Calibration protocol: ``--synthetic K`` measures the recovery rate on
instances with known answers.  Only a budget that works on synthetics says
anything about the real PK8.

Pure Python (the sandbox has no numpy); one EM iteration is ~0.5 s.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from buttcrack.ciphers.base import CrackContext  # noqa: E402
from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET, SumClock  # noqa: E402
from buttcrack.lang import get_model  # noqa: E402
from kryptos.pk8_calibrated_recovery import N, PERIODS, decrypt, encrypt, english_pool  # noqa: E402

A26 = 26
# letter index (A=0..Z=25) of the kryptos symbol with cipher-index k
LETTER_OF = [ord(c) - 65 for c in KRYPTOS_ALPHABET]


def load_bigrams(path: Path) -> tuple[list[list[float]], list[float]]:
    counts = [[1.0] * A26 for _ in range(A26)]  # add-one smoothing
    with gzip.open(path, "rt", encoding="ascii") as fh:
        for line in fh:
            gram, _, n = line[:-1].partition(" ")
            if len(gram) == 2 and gram.isalpha():
                counts[ord(gram[0]) - 65][ord(gram[1]) - 65] += float(n)
    logp = []
    for row in counts:
        total = sum(row)
        logp.append([math.log(c / total) for c in row])
    uni = [sum(counts[a][b] for a in range(A26)) for b in range(A26)]
    tot = sum(uni)
    logu = [math.log(u / tot) for u in uni]
    return logp, logu


class EMDA:
    def __init__(self, ct_idx: list[int], logp, logu, periods, rng):
        self.n = len(ct_idx)
        self.ct = ct_idx  # cipher indices over the kryptos alphabet
        self.logp, self.logu = logp, logu
        self.periods = periods
        self.rng = rng
        # theta[w][slot][v] distribution over Z26
        self.theta = [
            [[1.0 / A26] * A26 for _ in range(p)] for p in periods
        ]
        self.emiss = [[1.0 / A26] * A26 for _ in range(self.n)]
        self.gamma = [[1.0 / A26] * A26 for _ in range(self.n)]
        self.loggamma = [[-math.log(A26)] * A26 for _ in range(self.n)]

    # -- E step ---------------------------------------------------------- #
    def update_emissions(self, beta: float) -> None:
        for t in range(self.n):
            dist = None
            for wheel, p in zip(self.theta, self.periods):
                slot = wheel[t % p]
                if dist is None:
                    dist = slot
                    continue
                conv = [0.0] * A26
                for a in range(A26):
                    da = dist[a]
                    if da == 0.0:
                        continue
                    for b in range(A26):
                        conv[(a + b) % A26] += da * slot[b]
                dist = conv
            row = self.emiss[t]
            c = self.ct[t]
            # P(plaintext letter = x at t) = sum_v dist[v] where decrypting with
            # key v gives kryptos index (c - v), whose letter is LETTER_OF[(c-v)%26].
            e = [0.0] * A26
            for v in range(A26):
                e[LETTER_OF[(c - v) % A26]] += dist[v]
            if beta != 1.0:
                e = [max(v, 1e-300) ** beta for v in e]
            s = sum(e)
            self.emiss[t] = [v / s for v in e]

    def forward_backward(self) -> None:
        n = self.n
        alpha = [[0.0] * A26 for _ in range(n)]
        row0 = alpha[0]
        e0 = self.emiss[0]
        for x in range(A26):
            row0[x] = math.exp(self.logu[x]) * e0[x]
        s = sum(row0)
        for x in range(A26):
            row0[x] /= s
        for t in range(1, n):
            prev, cur = alpha[t - 1], alpha[t]
            et = self.emiss[t]
            logp = self.logp
            acc = [0.0] * A26
            for x in range(A26):
                ax = prev[x]
                if ax == 0.0:
                    continue
                lx = logp[x]
                ex = math.exp  # local
                for y in range(A26):
                    acc[y] += ax * ex(lx[y])
            tsum = 0.0
            for y in range(A26):
                v = acc[y] * et[y]
                cur[y] = v
                tsum += v
            inv = 1.0 / tsum
            for y in range(A26):
                cur[y] *= inv
        beta = [[0.0] * A26 for _ in range(n)]
        rown = beta[n - 1]
        for x in range(A26):
            rown[x] = 1.0
        for t in range(n - 2, -1, -1):
            cur, nxt = beta[t], beta[t + 1]
            en = self.emiss[t + 1]
            logp = self.logp
            for x in range(A26):
                s = 0.0
                lx = logp[x]
                for y in range(A26):
                    s += nxt[y] * en[y] * math.exp(lx[y])
                cur[x] = s
            tsum = sum(cur)
            inv = 1.0 / tsum
            for x in range(A26):
                cur[x] *= inv
        for t in range(n):
            a, b, g = alpha[t], beta[t], self.gamma[t]
            tsum = 0.0
            for x in range(A26):
                v = a[x] * b[x]
                g[x] = v
                tsum += v
            inv = 1.0 / tsum
            lg = self.loggamma[t]
            for x in range(A26):
                g[x] *= inv
                lg[x] = math.log(g[x] + 1e-300)

    # -- M step ---------------------------------------------------------- #
    def m_step(self, temperature: float) -> None:
        rng = self.rng
        order = [(w, s) for w, p in enumerate(self.periods) for s in range(p)]
        rng.shuffle(order)
        for w, s in order:
            p = self.periods[w]
            others = [i for i in range(len(self.periods)) if i != w]
            A = [0.0] * A26
            for t in range(s, self.n, p):
                # distribution of the sum of the other wheels at position t
                dist = None
                for w2 in others:
                    slot = self.theta[w2][t % self.periods[w2]]
                    if dist is None:
                        dist = slot
                        continue
                    conv = [0.0] * A26
                    for a in range(A26):
                        da = dist[a]
                        if da == 0.0:
                            continue
                        for b in range(A26):
                            conv[(a + b) % A26] += da * slot[b]
                    dist = conv
                c = self.ct[t]
                lg = self.loggamma[t]
                for v in range(A26):
                    acc = 0.0
                    for k in range(A26):
                        dk = dist[k]
                        if dk == 0.0:
                            continue
                        acc += dk * lg[LETTER_OF[(c - v - k) % A26]]
                    A[v] += acc
            amax = max(A)
            ex = [math.exp((a - amax) / temperature) for a in A]
            tot = sum(ex)
            self.theta[w][s] = [e / tot for e in ex]

    def run(self, iters: int = 60, beta0: float = 0.15) -> None:
        for it in range(iters):
            beta = min(1.0, beta0 * (1.08 ** it))
            temp = max(0.05, 1.0 * (0.95 ** it))
            self.update_emissions(beta)
            self.forward_backward()
            self.m_step(temp)

    def hard_wheels(self) -> list[list[int]]:
        return [
            [max(range(A26), key=lambda v: slot[v]) for slot in wheel]
            for wheel in self.theta
        ]


def attack(ct_text: str, *, restarts: int, iters: int, budget: float, seed: int,
           verbose: bool = False) -> tuple[float, str, list[list[int]]]:
    logp, logu = load_bigrams(ROOT / "buttcrack/data/english_bigrams.txt.gz")
    idx = {c: i for i, c in enumerate(KRYPTOS_ALPHABET)}
    ct_idx = [idx[c] for c in ct_text]
    model = get_model()
    sc = SumClock()
    ctx = CrackContext.create(model=model, budget=budget)
    rng = random.Random(seed)
    best_fit, best_pt, best_wheels = -1e9, "", None
    t_end = time.time() + budget
    for r in range(restarts):
        if time.time() > t_end:
            break
        em = EMDA(ct_idx, logp, logu, PERIODS, rng)
        em.run(iters=iters)
        wheels = em.hard_wheels()
        wheels, fit = sc._ascend(ct_text, KRYPTOS_ALPHABET, PERIODS, ctx, rng, wheels=wheels)
        pt = decrypt(ct_text, wheels)
        if verbose:
            print(f"  restart {r}: fit {fit:.4f}  {pt[:48]}", flush=True)
        if fit > best_fit:
            best_fit, best_pt, best_wheels = fit, pt, wheels
    return best_fit, best_pt, best_wheels


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--synthetic", type=int, default=0)
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--restarts", type=int, default=10)
    ap.add_argument("--iters", type=int, default=60)
    ap.add_argument("--budget", type=float, default=1800.0)
    args = ap.parse_args()

    if args.synthetic:
        rng = random.Random(31337)
        pool = english_pool()
        solved = 0
        for k in range(args.synthetic):
            plain = pool[rng.randrange(len(pool))]
            wheels = [[rng.randrange(26) for _ in range(p)] for p in PERIODS]
            ct = encrypt(plain, wheels)
            t0 = time.time()
            fit, pt, _ = attack(ct, restarts=args.restarts, iters=args.iters,
                                budget=args.budget, seed=rng.randrange(2**31), verbose=True)
            acc = sum(a == b for a, b in zip(pt, plain)) / len(plain)
            ok = acc >= 0.99
            solved += ok
            print(f"synthetic {k}: fit={fit:.4f} acc={acc * 100:.1f}% solved={ok} "
                  f"({time.time() - t0:.0f}s)", flush=True)
            if ok or k == 0:
                print(f"  truth: {plain[:66]}\n  found: {pt[:66]}", flush=True)
        print(f"EM-DA CALIBRATION RECOVERY: {solved}/{args.synthetic}")

    if args.real:
        ct = json.loads((ROOT / "kryptos/pk_all_ciphertexts.json").read_text())["PK8"]
        fit, pt, wheels = attack(ct, restarts=args.restarts, iters=args.iters,
                                 budget=args.budget, seed=8, verbose=True)
        print(f"REAL PK8: fit={fit:.4f}")
        print(pt)
        print(f"wheels: {wheels}")


if __name__ == "__main__":
    main()
