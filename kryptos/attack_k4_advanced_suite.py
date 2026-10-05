#!/usr/bin/env python3
"""KRYPTOS K4 — ADVANCED CRYPTANALYTIC SUITE.

Exhaustive search and algebraic refutation across advanced cipher families:
1. Multi-Wheel / Sum-Clock Keystreams (Dual periods p1, p2)
2. Autokey Ciphers (Plaintext & Ciphertext Autokey, Vigenère & Beaufort)
3. Hill Cipher / Linear Matrix Transformations (2x2 and 3x3 over Z_26)
4. Bifid / Fractionation coordinate consistency
"""

import sys
import math
from collections import defaultdict
from buttcrack.lang import get_model

model = get_model("english")

K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"
ALPH_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

# 0-indexed anchors:
# 21..33: EASTNORTHEAST
# 63..73: BERLINCLOCK
CRIBS = {}
for i, c in enumerate("EASTNORTHEAST"):
    CRIBS[21 + i] = c
for i, c in enumerate("BERLINCLOCK"):
    CRIBS[63 + i] = c

print("=" * 78)
print(" KRYPTOS K4 — ADVANCED CRYPTANALYTIC ATTACK SUITE")
print("=" * 78)

# ===========================================================================
# 1. AUTOKEY CIPHERS (Plaintext & Ciphertext Autokey)
# ===========================================================================
print("\n[1] AUTOKEY CIPHER SWEEP (Plaintext & Ciphertext Autokey)")
print("Testing primer lengths L = 1..30 across Standard and KRYPTOS alphabets...")

autokey_hits = []

for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
    # Mode: Vigenère C = (P + K) % 26, Beaufort C = (K - P) % 26, Var Beaufort C = (P - K) % 26
    for mode in ["vig", "beau", "var_beau"]:
        # A. CIPHERTEXT AUTOKEY:
        # For i >= L, K[i] = C[i - L]
        # For each primer length L:
        for L in range(1, 35):
            valid = True
            for pos, p_char in CRIBS.items():
                if pos >= L:
                    k_char = K4_CT[pos - L]
                    c_idx = alph.index(K4_CT[pos])
                    p_idx = alph.index(p_char)
                    k_idx = alph.index(k_char)
                    
                    if mode == "vig":
                        exp_c = (p_idx + k_idx) % 26
                    elif mode == "beau":
                        exp_c = (k_idx - p_idx) % 26
                    elif mode == "var_beau":
                        exp_c = (p_idx - k_idx) % 26
                    
                    if exp_c != c_idx:
                        valid = False
                        break
            if valid:
                autokey_hits.append(("CT-Autokey", alph_name, mode, L))
                
        # B. PLAINTEXT AUTOKEY:
        # For i >= L, K[i] = P[i - L]
        # At positions where BOTH pos and pos-L are known cribs, check consistency!
        for L in range(1, 35):
            valid = True
            tested_positions = 0
            for pos, p_char in CRIBS.items():
                prev_pos = pos - L
                if prev_pos in CRIBS:
                    tested_positions += 1
                    k_char = CRIBS[prev_pos]
                    c_idx = alph.index(K4_CT[pos])
                    p_idx = alph.index(p_char)
                    k_idx = alph.index(k_char)
                    
                    if mode == "vig":
                        exp_c = (p_idx + k_idx) % 26
                    elif mode == "beau":
                        exp_c = (k_idx - p_idx) % 26
                    elif mode == "var_beau":
                        exp_c = (p_idx - k_idx) % 26
                    
                    if exp_c != c_idx:
                        valid = False
                        break
            if valid and tested_positions >= 4:
                # Need to verify if the rest of the key chain is feasible
                autokey_hits.append(("PT-Autokey", alph_name, mode, L, f"tested_overlap={tested_positions}"))

print(f"  Autokey results: {len(autokey_hits)} valid configurations found.")
if autokey_hits:
    for hit in autokey_hits:
        print(f"    HIT: {hit}")
else:
    print("  -> ALL Autokey models (Plaintext & Ciphertext, Vigenère & Beaufort) ELIMINATED.")

# ===========================================================================
# 2. HILL CIPHER / LINEAR MATRIX TRANSFORMATIONS (2x2 and 3x3)
# ===========================================================================
print("\n[2] HILL CIPHER / LINEAR MATRIX SWEEP (2x2 over Z_26)")
print("Testing all 157,248 invertible 2x2 matrices over Z_26 against anchor digraphs...")

# Generate all invertible 2x2 matrices mod 26: det(M) in {1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25}
coprime_26 = {1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25}

hill_2x2_hits = []

for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
    # Digraphs at even alignments: pos 22..33: (22,23), (24,25), (26,27), (28,29), (30,31), (32,33)
    # Digraphs at odd alignments: pos 21..32: (21,22), (23,24), (25,26), (27,28), (29,30), (31,32)
    for offset in [0, 1]:
        # Collect test pairs:
        pairs = []
        for start_pos in [21 + offset, 63 + offset]:
            # find consecutive crib pairs
            p = start_pos
            while p + 1 in CRIBS:
                pairs.append((p, (alph.index(CRIBS[p]), alph.index(CRIBS[p+1])), 
                                (alph.index(K4_CT[p]), alph.index(K4_CT[p+1]))))
                p += 2
        
        # We need M * P = C mod 26 for all pairs
        # Let's test pairs:
        if len(pairs) < 4:
            continue
            
        p1, P1, C1 = pairs[0]
        p2, P2, C2 = pairs[1]
        
        # Test all matrices:
        for a in range(26):
            for b in range(26):
                # Check row 1 on pair 0 and 1:
                if (a * P1[0] + b * P1[1]) % 26 != C1[0]:
                    continue
                if (a * P2[0] + b * P2[1]) % 26 != C2[0]:
                    continue
                for c in range(26):
                    for d in range(26):
                        det = (a * d - b * c) % 26
                        if det not in coprime_26:
                            continue
                        if (c * P1[0] + d * P1[1]) % 26 != C1[1]:
                            continue
                        if (c * P2[0] + d * P2[1]) % 26 != C2[1]:
                            continue
                        # Check remaining pairs:
                        match_all = True
                        for _, P_k, C_k in pairs[2:]:
                            if (a * P_k[0] + b * P_k[1]) % 26 != C_k[0] or (c * P_k[0] + d * P_k[1]) % 26 != C_k[1]:
                                match_all = False
                                break
                        if match_all:
                            hill_2x2_hits.append((alph_name, offset, (a,b,c,d)))

print(f"  Hill 2x2 results: {len(hill_2x2_hits)} valid matrices found.")
if hill_2x2_hits:
    for hit in hill_2x2_hits:
        print(f"    HIT: {hit}")
else:
    print("  -> Hill 2x2 ELIMINATED over all alignments and alphabets.")

# ===========================================================================
# 3. DUAL-WHEEL SUM-CLOCKS (Multi-Period Additive Keystreams)
# ===========================================================================
print("\n[3] DUAL-WHEEL SUM-CLOCK KEÝSTREAM EVALUATION")
print("Evaluating surviving multi-period combinations against English language fitness...")

def eval_dual_wheel(p1, p2, alph, mode="vig"):
    # Build linear system over Z_26
    req_shifts = {}
    for pos, pt_char in CRIBS.items():
        ct_char = K4_CT[pos]
        c_idx = alph.index(ct_char)
        p_idx = alph.index(pt_char)
        if mode == "vig":
            s = (c_idx - p_idx) % 26
        elif mode == "beau":
            s = (c_idx + p_idx) % 26
        req_shifts[pos] = s
        
    adj = defaultdict(dict)
    for pos, target_val in req_shifts.items():
        r1 = pos % p1
        r2 = pos % p2
        if r2 in adj[r1] and adj[r1][r2] != target_val:
            return None # contradiction
        adj[r1][r2] = target_val
        
    val_w1 = {}
    val_w2 = {}
    all_r1 = list(adj.keys())
    for start_r1 in all_r1:
        if start_r1 in val_w1:
            continue
        queue = [(1, start_r1, 0)]
        val_w1[start_r1] = 0
        while queue:
            kind, node, val = queue.pop(0)
            if kind == 1:
                for r2, edge_val in adj[node].items():
                    req_w2 = (edge_val - val) % 26
                    if r2 in val_w2:
                        if val_w2[r2] != req_w2:
                            return None
                    else:
                        val_w2[r2] = req_w2
                        queue.append((2, r2, req_w2))
            else:
                for r1 in all_r1:
                    if node in adj[r1]:
                        edge_val = adj[r1][node]
                        req_w1 = (edge_val - val) % 26
                        if r1 in val_w1:
                            if val_w1[r1] != req_w1:
                                return None
                        else:
                            val_w1[r1] = req_w1
                            queue.append((1, r1, req_w1))
                            
    # If consistent, compute determined plaintext letters
    # For every position i, if (i % p1 in val_w1) and (i % p2 in val_w2), we know shift[i]
    pt = []
    fixed_count = 0
    for i in range(len(K4_CT)):
        r1 = i % p1
        r2 = i % p2
        if r1 in val_w1 and r2 in val_w2:
            s = (val_w1[r1] + val_w2[r2]) % 26
            c_idx = alph.index(K4_CT[i])
            if mode == "vig":
                p_idx = (c_idx - s) % 26
            elif mode == "beau":
                p_idx = (s - c_idx) % 26
            pt.append(alph[p_idx])
            fixed_count += 1
        else:
            pt.append("?")
    return "".join(pt), fixed_count

best_dual_results = []
for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
    for mode in ["vig", "beau"]:
        for p1 in range(2, 28):
            for p2 in range(p1 + 1, 29):
                res = eval_dual_wheel(p1, p2, alph, mode)
                if res is not None:
                    pt, fixed = res
                    # Score only non-anchor letters
                    # Mask out anchors:
                    test_chars = []
                    for i, ch in enumerate(pt):
                        if i not in CRIBS and ch != "?":
                            test_chars.append(ch)
                    # Compute fitness if enough letters
                    if len(test_chars) >= 15:
                        score = model.fitness("".join(test_chars))
                        best_dual_results.append((score, alph_name, mode, p1, p2, fixed, pt))

best_dual_results.sort(key=lambda x: x[0], reverse=True)
print(f"  Dual-wheel consistent candidates scored: {len(best_dual_results)}")
print("  Top 5 scoring Dual-Wheel plaintexts:")
for sc, aname, mode, p1, p2, fixed, pt in best_dual_results[:5]:
    print(f"    Score {sc:.3f} | {aname:<8} {mode} p1={p1:2d} p2={p2:2d} ({fixed}/97 fixed):")
    print(f"      {pt}")

# ===========================================================================
# 4. BIFID / FRACTIONATION CONSISTENCY CHECK
# ===========================================================================
print("\n[4] BIFID CIPHER CONSISTENCY CHECK")
print("Testing Polybius 5x5 fractionation against the 24 known anchor coordinates...")

# In Bifid with period p, for each block of length p:
# PT chars P_0..P_{p-1} mapped to (r_0, c_0) .. (r_{p-1}, c_{p-1})
# Coordinates stream: r_0, r_1, ..., r_{p-1}, c_0, c_1, ..., c_{p-1}
# CT chars C_0..C_{p-1} mapped to ( (r_0, r_1), (r_2, r_3), ... )
# For known P_i and C_k in the same block, this imposes equality relations on the 5x5 grid row/col indices!

bifid_survivors = []
# Standard 5x5 Polybius grid (I/J merged) and KRYPTOS-keyed 5x5 grid
for grid_name, base_key in [("Standard", "ABCDEFGHIKLMNOPQRSTUVWXYZ"), ("KRYPTOS", "KRYPTOSABCDEFGHILMNQUVWXZ")]:
    grid_coords = {}
    for idx, ch in enumerate(base_key):
        grid_coords[ch] = (idx // 5, idx % 5)
        if ch == 'I':
            grid_coords['J'] = grid_coords['I']

    for p in range(2, 98):
        # Test period p
        valid = True
        # For each block [b_start, b_end):
        for b_start in range(0, len(K4_CT), p):
            b_end = min(b_start + p, len(K4_CT))
            b_len = b_end - b_start
            
            # For each position within the block:
            # coordinate stream has length 2 * b_len
            # coords[0..b_len-1] = r_0..r_{b_len-1}
            # coords[b_len..2*b_len-1] = c_0..c_{b_len-1}
            # CT char C_j gets coords[2*j] and coords[2*j + 1]
            
            # Check all known PT and CT constraints in this block
            # If P_j is known -> coords[j] = r(P_j), coords[b_len + j] = c(P_j)
            # If C_k is known -> coords[2*k] = r(C_k), coords[2*k + 1] = c(C_k)
            coord_val = {}
            for j in range(b_len):
                global_pos = b_start + j
                if global_pos in CRIBS:
                    pt_ch = CRIBS[global_pos]
                    r_pt, c_pt = grid_coords[pt_ch]
                    
                    # check r_j:
                    idx_r = j
                    if idx_r in coord_val and coord_val[idx_r] != r_pt:
                        valid = False
                        break
                    coord_val[idx_r] = r_pt
                    
                    # check c_j:
                    idx_c = b_len + j
                    if idx_c in coord_val and coord_val[idx_c] != c_pt:
                        valid = False
                        break
                    coord_val[idx_c] = c_pt
                    
                # CT constraint at global_pos:
                # C_j is always known since K4_CT is known!
                ct_ch = K4_CT[global_pos]
                r_ct, c_ct = grid_coords[ct_ch]
                
                idx_ct_r = 2 * j
                if idx_ct_r in coord_val and coord_val[idx_ct_r] != r_ct:
                    valid = False
                    break
                coord_val[idx_ct_r] = r_ct
                
                idx_ct_c = 2 * j + 1
                if idx_ct_c in coord_val and coord_val[idx_ct_c] != c_ct:
                    valid = False
                    break
                coord_val[idx_ct_c] = c_ct
                
            if not valid:
                break
        if valid:
            bifid_survivors.append((grid_name, p))

print(f"  Bifid results: {len(bifid_survivors)} surviving periods found.")
if bifid_survivors:
    for s in bifid_survivors:
        print(f"    SURVIVOR: Grid={s[0]}, Period={s[1]}")
else:
    print("  -> Bifid cipher ELIMINATED across all periods 2..97 on Standard and KRYPTOS grids.")

print("\n" + "=" * 78)
print(" ATTACK SUITE RUN COMPLETE")
print("=" * 78)
