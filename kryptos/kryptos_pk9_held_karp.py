#!/usr/bin/env python3
"""EXACT HELD-KARP COLUMNAR SOLVER FOR PK9
Coupled with the mod-13 Quagmire III schedule.
"""

import json
import math
import time
from collections import Counter

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK9"]

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
n = len(ct)

# 1. Build an English bigram transition matrix from words_alpha.txt
print("Building English bigram table from dictionary...")
with open("words_alpha.txt") as f:
    dict_words = [w.strip().upper() for w in f if len(w.strip()) >= 3]

bg_counts = Counter()
for w in dict_words:
    for i in range(len(w) - 1):
        bg_counts[w[i:i+2]] += 1

total_bg = sum(bg_counts.values())
TBL = {bg: math.log10(c / total_bg) for bg, c in bg_counts.items()}
FLOOR = -7.5

def lp(x, y):
    return TBL.get(x + y, FLOOR)

# 2. Exact Held-Karp Solver
def held_karp(T, W, w):
    full = (1 << w) - 1
    best_score, best_seq = None, None
    for start in range(w):
        NEG = float("-inf")
        dp = [[NEG] * w for _ in range(1 << w)]
        par = [[-1] * w for _ in range(1 << w)]
        dp[1 << start][start] = 0.0
        for S in range(1 << w):
            if not (S >> start) & 1:
                continue
            row = dp[S]
            for last in range(w):
                cur = row[last]
                if cur == NEG:
                    continue
                for nxt in range(w):
                    if (S >> nxt) & 1:
                        continue
                    S2 = S | (1 << nxt)
                    val = cur + T[last][nxt]
                    if val > dp[S2][nxt]:
                        dp[S2][nxt] = val
                        par[S2][nxt] = last
        for end in range(w):
            if dp[full][end] == NEG:
                continue
            total = dp[full][end] + W[end][start]
            if best_score is None or total > best_score:
                seq, S, cur = [], full, end
                while cur != -1:
                    seq.append(cur)
                    prev = par[S][cur]
                    S ^= (1 << cur)
                    cur = prev
                best_score, best_seq = total, seq[::-1]
    return best_score, best_seq

def solve_columnar(text, w):
    h = len(text) // w
    B = [text[k * h:(k + 1) * h] for k in range(w)]
    T = [[sum(lp(B[i][r], B[j][r]) for r in range(h)) if i != j else float("-inf")
          for j in range(w)] for i in range(w)]
    Wm = [[sum(lp(B[i][r], B[j][r + 1]) for r in range(h - 1))
           for j in range(w)] for i in range(w)]
    score, seq = held_karp(T, Wm, w)
    plain = "".join(B[seq[c]][r] for r in range(h) for c in range(w))
    order = [0] * w
    for c, blk in enumerate(seq):
        order[blk] = c
    return score, order, plain

# 3. English word checker
with open("words_alpha.txt") as f:
    word_set = set(w.strip().upper() for w in f if len(w.strip()) >= 4)

def count_words(txt):
    return sum(1 for i in range(len(txt) - 3) if txt[i:i+4] in word_set)

# 4. Mod-13 Schedule
s13 = [0, 2, 9, 10, 10, 6, 7]

print(f"\nSearching all 128 parity lifts across candidate widths [6, 8, 9, 12]...")

results = []
t0 = time.time()

for w in [8, 9, 12, 6]:
    print(f"\n--- Testing Width {w:2d} ({n // w} rows x {w} cols) ---")
    for mask in range(128):
        shifts26 = [s13[i] + (13 if (mask & (1 << i)) else 0) for i in range(7)]
        # Decrypt outer Quagmire
        z = "".join(ALPH[(ALPH.index(ch) - shifts26[i % 7]) % 26] for i, ch in enumerate(ct))
        score, order, plain = solve_columnar(z, w)
        w_cnt = count_words(plain)
        results.append((w_cnt, score, w, mask, shifts26, order, plain))

print(f"\nExhaustive sweep completed in {time.time() - t0:.2f} seconds!")
results.sort(key=lambda x: (x[0], x[1]), reverse=True)

print("\n" + "=" * 70)
print("TOP 10 CANDIDATE DECRYPTIONS (Ranked by Valid English 4+ Letter Words)")
print("=" * 70)

for w_cnt, score, w, mask, shifts, order, plain in results[:10]:
    key_str = "".join(ALPH[s] for s in shifts)
    print(f"Words: {w_cnt:2d} | Width: {w:2d} | Mask: {mask:3d} | Key: {key_str} | Order: {order}")
    print(f"Text: {plain[:70]}...")
    print("-" * 70)
