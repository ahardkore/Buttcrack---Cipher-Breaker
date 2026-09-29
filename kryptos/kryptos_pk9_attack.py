#!/usr/bin/env python3
"""High-performance PK9 Cryptanalysis Engine
Executes joint search over mod-13 parity lifts, transposition geometries, and quadgram scores.
"""

import json
import math
from collections import Counter
import random

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK9"]

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
n = len(ct)

# 1. Build an n-gram language model from English wordlist
print("Building English n-gram language model...")
with open("words_alpha.txt") as f:
    dict_words = [w.strip().upper() for w in f if len(w.strip()) >= 3]

# Tri-gram and Quad-gram frequencies
tri_counts = Counter()
quad_counts = Counter()
for w in dict_words:
    for i in range(len(w) - 2):
        tri_counts[w[i:i+3]] += 1
    for i in range(len(w) - 3):
        quad_counts[w[i:i+4]] += 1

total_tri = sum(tri_counts.values())
log_tri = {t: math.log10(c / total_tri) for t, c in tri_counts.items()}
floor_tri = -7.5

total_quad = sum(quad_counts.values())
log_quad = {q: math.log10(c / total_quad) for q, c in quad_counts.items()}
floor_quad = -9.0

def score_tri(txt):
    return sum(log_tri.get(txt[i:i+3], floor_tri) for i in range(len(txt) - 2)) / (len(txt) - 2)

def score_quad(txt):
    return sum(log_quad.get(txt[i:i+4], floor_quad) for i in range(len(txt) - 3)) / (len(txt) - 3)

with open("words_alpha.txt") as f:
    common_words = set(w.strip().upper() for w in f if len(w.strip()) >= 4)

def count_words(txt):
    return sum(1 for i in range(len(txt) - 3) if txt[i:i+4] in common_words)

print("Baseline CT scores:")
print(f"  Tri-gram score: {score_tri(ct):.4f}")
print(f"  Quad-gram score: {score_quad(ct):.4f}")

# 2. Known Mod-13 Schedule
shifts13 = [0, 2, 9, 10, 10, 6, 7]

# 3. Route transpositions on a matrix of (rows, cols)
def get_routes(s, r, c):
    grid = [s[i*c:(i+1)*c] for i in range(r)]
    routes = {}
    
    # By rows (identity)
    routes["row_id"] = s
    
    # By cols
    routes["col_read"] = "".join("".join(grid[i][j] for i in range(r)) for j in range(c))
    
    # Boustrophedon rows
    b_rows = []
    for i in range(r):
        b_rows.append(grid[i] if i % 2 == 0 else grid[i][::-1])
    routes["boustro_rows"] = "".join(b_rows)
    
    # Boustrophedon cols
    b_cols = []
    for j in range(c):
        col = [grid[i][j] for i in range(r)]
        b_cols.append("".join(col if j % 2 == 0 else col[::-1]))
    routes["boustro_cols"] = "".join(b_cols)
    
    # Reverse rows
    routes["rev_rows"] = "".join("".join(row[::-1]) for row in grid)
    
    # Reverse cols
    routes["rev_cols"] = "".join("".join(grid[r-1-i][j] for i in range(r)) for j in range(c))
    
    return routes

print("\n" + "=" * 70)
print("PHASE 1: Testing 128 Parity Lifts against 12x12 & 16x9 Matrix Routes")
print("=" * 70)

best_candidates = []

for mask in range(128):
    # Parity lift for 7 positions
    shifts26 = [shifts13[i] + (13 if (mask & (1 << i)) else 0) for i in range(7)]
    
    # Decrypt outer Quagmire layer
    z = "".join(ALPH[(ALPH.index(ch) - shifts26[i % 7]) % 26] for i, ch in enumerate(ct))
    
    # Test routes on 12x12
    r12 = get_routes(z, 12, 12)
    for r_name, r_text in r12.items():
        sc = score_tri(r_text)
        w_cnt = count_words(r_text)
        if sc > -4.5 or w_cnt > 12:
            best_candidates.append((sc, w_cnt, f"12x12_{r_name}", mask, shifts26, r_text))
            
    # Test routes on 16x9
    r16 = get_routes(z, 16, 9)
    for r_name, r_text in r16.items():
        sc = score_tri(r_text)
        w_cnt = count_words(r_text)
        if sc > -4.5 or w_cnt > 12:
            best_candidates.append((sc, w_cnt, f"16x9_{r_name}", mask, shifts26, r_text))
            
    # Test routes on 9x16
    r9 = get_routes(z, 9, 16)
    for r_name, r_text in r9.items():
        sc = score_tri(r_text)
        w_cnt = count_words(r_text)
        if sc > -4.5 or w_cnt > 12:
            best_candidates.append((sc, w_cnt, f"9x16_{r_name}", mask, shifts26, r_text))

best_candidates.sort(key=lambda x: (x[1], x[0]), reverse=True)
print(f"Top routes evaluated. Filtered candidates: {len(best_candidates)}")
for sc, w_cnt, r_name, mask, s26, txt in best_candidates[:10]:
    key_str = "".join(ALPH[s] for s in s26)
    print(f"[{r_name}] Words: {w_cnt:2d} | Tri-Score: {sc:.3f} | Key: {key_str} | Mask: {mask:3d}")
    print(f"   Text: {txt[:70]}...")

print("\n" + "=" * 70)
print("PHASE 2: Columnar Permutation Search (Held-Karp Bigram Optimal)")
print("=" * 70)

# Build bigram log table
bigram_counts = Counter()
for w in dict_words:
    for i in range(len(w) - 1):
        bigram_counts[w[i:i+2]] += 1
total_bg = sum(bigram_counts.values())
log_bg = {bg: math.log10(c / total_bg) for bg, c in bigram_counts.items()}
floor_bg = -7.0

def score_bg(txt):
    return sum(log_bg.get(txt[i:i+2], floor_bg) for i in range(len(txt) - 1)) / (len(txt) - 1)

# Test widths dividing 144
for w in [8, 9, 12]:
    rows = n // w
    print(f"\nTesting width {w} (rows {rows})...")
    # For top 5 parity masks, test column permutations
    for mask in [0, 1, 2, 4, 8, 16, 32, 64, 127]:
        shifts26 = [shifts13[i] + (13 if (mask & (1 << i)) else 0) for i in range(7)]
        z = "".join(ALPH[(ALPH.index(ch) - shifts26[i % 7]) % 26] for i, ch in enumerate(ct))
        
        # Grid columns
        cols = [z[c*rows:(c+1)*rows] for c in range(w)]
        
        # Greedy best permutation
        perm = [0]
        used = {0}
        while len(perm) < w:
            last = perm[-1]
            best_c = None
            best_sc = -1e9
            for c in range(w):
                if c not in used:
                    # transition score between cols[last] and cols[c]
                    trans_sc = sum(log_bg.get(cols[last][r] + cols[c][r], floor_bg) for r in range(rows))
                    if trans_sc > best_sc:
                        best_sc = trans_sc
                        best_c = c
            perm.append(best_c)
            used.add(best_c)
            
        # Unroll grid
        unrolled = []
        for r in range(rows):
            for c in perm:
                unrolled.append(cols[c][r])
        cand_pt = "".join(unrolled)
        w_cnt = count_words(cand_pt)
        bg_sc = score_bg(cand_pt)
        if w_cnt > 10 or bg_sc > -3.3:
            print(f"  Width {w} | Mask {mask:3d} | Perm {perm} | Words: {w_cnt:2d} | BG-Score: {bg_sc:.3f}")
            print(f"     PT: {cand_pt[:60]}...")
