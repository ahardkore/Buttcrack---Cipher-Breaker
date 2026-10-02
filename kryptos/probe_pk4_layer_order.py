#!/usr/bin/env python3
"""Pin down PK4's layer order and Q-wheel conventions empirically.

PK4 = T(8) Q(5) Q(9) per the public notation; verified PT/CT pair exists
(corrections of 2026-10-02).  Hypotheses for encryption order:
  H1:  P --T8--> M --Q(q5+q9)--> C   (transposition first)
  H2:  P --Q(q5+q9)--> M --T8--> C   (substitution first)
For each hypothesis and each of the 8! column orders, derive the implied
keystream d and test whether d[i] = q5[i%5] + q9[i%9] (mod 26) in KRYPTOS
index space for some wheels q5, q9 (gauge q5[0] = q9[0] = 0).

Answer (see verify_pk_constructions.py): H1 with key order UNDERLAY,
q5 = OCHRE, q9 = VERDIGRIS.  This probe re-derives it blind.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALPHA = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
KIDX = {c: i for i, c in enumerate(ALPHA)}

REC = json.loads((ROOT / "pk_verified_solutions.json").read_text())["PK4"]
PT, CT = REC["plaintext"], REC["ciphertext"]
N, W = len(PT), 8
H = N // W


def solve_sumclock(d: list[int]) -> list[int] | None:
    """Return wheels q5[0..4]+q9[0..8] (gauge q5[0]=0, the only free gauge
    dimension since shifts must cancel in the sum), or None."""
    # period-45 necessity
    if any((d[i] - d[i - 45]) % 26 != 0 for i in range(45, N)):
        return None
    q5, q9 = [0] * 5, [0] * 9
    q9[0] = d[0] % 26
    # CRT alignment: for each a in 1..4 find i in 0..44 with i%5==a and i%9==0
    for a in range(1, 5):
        for i in range(45):
            if i % 5 == a and i % 9 == 0:
                q5[a] = (d[i] - d[0]) % 26
                break
    for b in range(1, 9):
        for i in range(45):
            if i % 5 == 0 and i % 9 == b:
                q9[b] = d[i] % 26
                break
    for i in range(N):
        if (q5[i % 5] + q9[i % 9]) % 26 != d[i] % 26:
            return None
    return q5 + q9


def gauge_words(q5: list[int], q9: list[int]) -> list[tuple[str, str]]:
    """Lift the gauge: find shifts making both wheels dictionary words."""
    EN = set()
    for wl in ("words_5.txt", "words_9.txt"):
        p = ROOT / wl
        if p.exists():
            EN.update(w.strip().upper() for w in p.read_text().split())
    out = []
    for a in range(26):
        w5 = "".join(ALPHA[(x + a) % 26] for x in q5)
        for b in range(26):
            w9 = "".join(ALPHA[(x + b) % 26] for x in q9)
            if w5 in EN or w9 in EN:
                out.append((w5, w9))
    return out


found: list[tuple[tuple[int, ...], list[int]]] = []
for sigma in itertools.permutations(range(W)):
    # H1: M block k = PT grid column sigma[k]; s[i] = Kidx(C[i]) - Kidx(M[i])
    d = []
    for i in range(N):
        k, r = divmod(i, H)
        d.append((KIDX[CT[i]] - KIDX[PT[sigma[k] + W * r]]) % 26)
    w = solve_sumclock(d)
    if w is not None:
        found.append((sigma, w))
        print(f"H1 T-FIRST consistent: order={sigma} q5={w[:5]} q9={w[5:]}")
        print("   gauge words:", gauge_words(w[:5], w[5:])[:6])
print("H1 (T first) consistent orders:", len(found))

found2 = []
for sigma in itertools.permutations(range(W)):
    d = [0] * N
    for i in range(N):
        c, r = i % W, i // W
        k = sigma.index(c)
        d[i] = (KIDX[CT[k * H + r]] - KIDX[PT[i]]) % 26
    w = solve_sumclock(d)
    if w is not None:
        found2.append((sigma, w))
        print(f"H2 Q-FIRST consistent: order={sigma} wheels={w[:5]}")
print("H2 (Q first) consistent orders:", len(found2))
