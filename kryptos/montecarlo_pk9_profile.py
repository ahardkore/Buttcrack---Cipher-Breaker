#!/usr/bin/env python3
"""Monte Carlo architecture test for PK9's raw-ciphertext fingerprint.

PK9 (N=144) shows: IoC(7)=0.0568, z(lag7)=+3.88, z(lag28)=+3.64,
z(lag14)=-0.46, IoC(45)=0.0704.  Reference points: PK4 (T-first, Q-last,
period 45) shows IoC(45)=0.0756; PK5/PK8 (period > N) show no peaks.

Question: which construction family produces PK9's profile?
  A. qt : Q(5)+Q(6)+Q(7) sum-clock, then columnar T8          (notation order)
  B. tq : columnar T8, then Q sum-clock                       (T-first like PK4/5/6)
  C. pure Q sum-clock, no transposition (identity T8), qt
  D. pure Q sum-clock, no transposition, tq (same as C)
Trials: random wheels, random T8 permutations, plaintext = random windows of
the verified PK1-PK8 story.
"""
from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALPHA = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
KIDX = {c: i for i, c in enumerate(ALPHA)}
CTS = json.loads((ROOT / "pk_all_ciphertexts.json").read_text())
SOL = json.loads((ROOT / "pk_verified_solutions.json").read_text())
STORY = "".join(SOL[pk]["plaintext"] for pk in ("PK1", "PK2", "PK3", "PK4", "PK5", "PK6", "PK7", "PK8"))
PK9 = CTS["PK9"]
N, W, H = 144, 8, 18


def ioc_period(text: str, p: int) -> float:
    tot, n = 0.0, 0
    for i in range(p):
        s = text[i::p]
        if len(s) < 2:
            continue
        c = Counter(s)
        tot += sum(v * (v - 1) for v in c.values()) / (len(s) * (len(s) - 1))
        n += 1
    return tot / n if n else 0.0


def autocorr_z(text: str, lag: int) -> float:
    n = len(text) - lag
    obs = sum(a == b for a, b in zip(text, text[lag:]))
    exp = n / 26
    var = n * (1 / 26) * (25 / 26)
    return (obs - exp) / var**0.5


def profile(t: str) -> dict:
    return {
        "ioc7": ioc_period(t, 7),
        "ioc14": ioc_period(t, 14),
        "ioc28": ioc_period(t, 28),
        "ioc45": ioc_period(t, 45),
        "z7": autocorr_z(t, 7),
        "z14": autocorr_z(t, 14),
        "z21": autocorr_z(t, 21),
        "z28": autocorr_z(t, 28),
    }


def rand_wheels():
    return ([random.randrange(26) for _ in range(5)],
            [random.randrange(26) for _ in range(6)],
            [random.randrange(26) for _ in range(7)])


def encrypt(pt: str, q5, q6, q7, sigma, order: str) -> str:
    # substitution
    z = "".join(ALPHA[(KIDX[c] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26] for i, c in enumerate(pt))
    if order == "qt":  # substitute then transpose
        return "".join(z[sigma[k] + W * r] for k in range(W) for r in range(H))
    # transpose then substitute
    m = "".join(pt[sigma[k] + W * r] for k in range(W) for r in range(H))
    return "".join(ALPHA[(KIDX[c] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26] for i, c in enumerate(m))


def trial(order: str, use_t8: bool) -> dict:
    pos = random.randrange(len(STORY) - N)
    pt = STORY[pos:pos + N]
    q5, q6, q7 = rand_wheels()
    sigma = list(range(W))
    if use_t8:
        sigma = random.sample(range(W), W)
    return profile(encrypt(pt, q5, q6, q7, sigma, order))


def summarize(name: str, trials: list[dict]) -> None:
    import statistics as st
    keys = trials[0].keys()
    print(f"\n{name} ({len(trials)} trials)")
    print("  " + "  ".join(f"{k:>7}" for k in keys))
    means = [st.mean(t[k] for t in trials) for k in keys]
    maxs = [max(t[k] for t in trials) for k in keys]
    p95 = [sorted(t[k] for t in trials)[int(0.95 * len(trials)) - 1] for k in keys]
    print("  mean " + "  ".join(f"{m:7.2f}" for m in means))
    print("  p95  " + "  ".join(f"{m:7.2f}" for m in p95))
    print("  max  " + "  ".join(f"{m:7.2f}" for m in maxs))


def main() -> None:
    random.seed(20261002)
    T = 4000
    obs = profile(PK9)
    print("PK9 observed:")
    print("  " + "  ".join(f"{k:>7}" for k in obs))
    print("  " + "  ".join(f"{v:7.2f}" for v in obs.values()))

    summarize(f"A: qt (Q567 then T8), random", [trial("qt", True) for _ in range(T)])
    summarize(f"B: tq (T8 then Q567), random", [trial("tq", True) for _ in range(T)])
    summarize(f"C: pure Q567, no T8", [trial("qt", False) for _ in range(T)])

    # how often does each family reach PK9's observed z7 and z28 jointly?
    for name, tr in (("A qt", [trial("qt", True) for _ in range(T)]),
                     ("B tq", [trial("tq", True) for _ in range(T)]),
                     ("C pure", [trial("qt", False) for _ in range(T)])):
        z7, z28 = obs["z7"], obs["z28"]
        both = sum(t["z7"] >= z7 and t["z28"] >= z28 for t in tr)
        either = sum(t["z7"] >= z7 or t["z28"] >= z28 for t in tr)
        print(f"\n{name}: trials with z7>={z7:.2f} AND z28>={z28:.2f}: {both}/{T}; either: {either}/{T}")


if __name__ == "__main__":
    main()
