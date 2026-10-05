#!/usr/bin/env python3
"""PATH B: DEEP MATHEMATICAL AUTOCORRELATION & DELTA ANALYSIS ON 24 ANCHOR SHIFTS.

Detailed analysis of:
1. Exact shift values S_i under Standard and Kryptos alphabets
2. First differences ΔS_i = (S_{i+1} - S_i) mod 26
3. Second differences Δ²S_i = (ΔS_{i+1} - ΔS_i) mod 26
4. Autocorrelation & spectral properties
5. Modular congruences & Linear Complexity
6. Fixed points & 2D Tableau coordinate mapping
"""

import math
from collections import Counter

K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"
ALPH_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

CRIBS = {}
for i, c in enumerate("EASTNORTHEAST"):
    CRIBS[21 + i] = c
for i, c in enumerate("BERLINCLOCK"):
    CRIBS[63 + i] = c

print("=" * 78)
print(" PATH B: MATHEMATICAL ANALYSIS OF 24 ANCHOR SHIFTS")
print("=" * 78)

# Group anchors into Block 1 (pos 21..33) and Block 2 (pos 63..73)
block1_pos = list(range(21, 34))
block2_pos = list(range(63, 74))

def analyze_block(name, positions, alph_name, alph):
    pt_chars = [CRIBS[p] for p in positions]
    ct_chars = [K4_CT[p] for p in positions]
    
    # Shifts (Vigenere: S = (C - P) mod 26)
    shifts = [(alph.index(c) - alph.index(p)) % 26 for c, p in zip(ct_chars, pt_chars)]
    
    # First differences
    diffs1 = [(shifts[i+1] - shifts[i]) % 26 for i in range(len(shifts) - 1)]
    
    # Second differences
    diffs2 = [(diffs1[i+1] - diffs1[i]) % 26 for i in range(len(diffs1) - 1)]
    
    print(f"\n--- {name} ({alph_name} Alphabet) ---")
    print(f"  Pos:       {[p+1 for p in positions]}")
    print(f"  Plaintext: {'  '.join(pt_chars)}")
    print(f"  Cipher:    {'  '.join(ct_chars)}")
    print(f"  Shifts S:  {shifts}")
    print(f"  ΔS (1st):  {diffs1}")
    print(f"  Δ²S (2nd): {diffs2}")
    
    # Check for constant progression:
    if len(set(diffs1)) == 1:
        print(f"  -> CONSTANT 1st difference found: {diffs1[0]}")
    if len(set(diffs2)) == 1:
        print(f"  -> CONSTANT 2nd difference (quadratic progression): {diffs2[0]}")
        
    return shifts, diffs1, diffs2

# Analyze Standard Alphabet
s1_std, d1_1_std, d2_1_std = analyze_block("BLOCK 1: EASTNORTHEAST (22..34)", block1_pos, "Standard", ALPH_STD)
s2_std, d1_2_std, d2_2_std = analyze_block("BLOCK 2: BERLINCLOCK (64..74)", block2_pos, "Standard", ALPH_STD)

# Analyze Kryptos Alphabet
s1_kr, d1_1_kr, d2_1_kr = analyze_block("BLOCK 1: EASTNORTHEAST (22..34)", block1_pos, "KRYPTOS", ALPH_K)
s2_kr, d1_2_kr, d2_2_kr = analyze_block("BLOCK 2: BERLINCLOCK (64..74)", block2_pos, "KRYPTOS", ALPH_K)

# Combined properties
print("\n" + "=" * 78)
print(" CROSS-BLOCK MATHEMATICAL PROPERTIES")
print("=" * 78)

# Fixed points:
print("\n1. Fixed Points (Self-Encryption S = 0):")
print("   - Pos 33 (1-based): Plaintext 'S' -> Ciphertext 'S' (Shift = 0)")
print("   - Pos 74 (1-based): Plaintext 'K' -> Ciphertext 'K' (Shift = 0)")
print("   Both blocks terminate with a zero-shift fixed point near their boundary!")

# Autocorrelation of Block 1 shifts:
print("\n2. Block 1 Shift Autocorrelation R(τ):")
for tau in range(1, 7):
    sum_prod_std = sum(s1_std[i] * s1_std[i + tau] for i in range(len(s1_std) - tau))
    sum_prod_kr = sum(s1_kr[i] * s1_kr[i + tau] for i in range(len(s1_kr) - tau))
    print(f"   Lag τ = {tau}: R_std = {sum_prod_std:4d} | R_kr = {sum_prod_kr:4d}")

# 2D Tableau Coordinate Mapping:
print("\n3. 2D Coordinates on the 26x26 KRYPTOS Tableau:")
print(f"   {'Pos':>3} | {'PT':>2} {'CT':>2} | {'(r_p, c_p)':>10} | {'(r_c, c_c)':>10} | {'Vector (Δr, Δc)':>16}")
print("   ----+-------+------------+------------+------------------")
for p in block1_pos:
    pt = CRIBS[p]
    ct = K4_CT[p]
    # On tableau, letter L is in row r at column c = (ALPH_K.index(L) - r) % 26
    # If r is the line index (Row 26 = row 25 on 0-based), let's compute:
    idx_p = ALPH_K.index(pt)
    idx_c = ALPH_K.index(ct)
    print(f"   {p+1:3d} | {pt:>2} {ct:>2} | index_p={idx_p:2d} | index_c={idx_c:2d} | Δ = {(idx_c - idx_p)%26:2d}")

