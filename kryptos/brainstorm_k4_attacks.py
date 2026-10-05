#!/usr/bin/env python3
"""KRYPTOS K4 — NEW BRAINSTORMED ATTACK FRONTIER.

Testing:
1. Alternating Vigenère / Beaufort modulated by Morse / binary flip vectors
2. "ID BY ROWS" — Row-specific keying on Rows 25, 26, 27, 28
3. Tableau 2D Coordinate Transformations (Row/Col deltas on Kryptos Tableau)
4. Dictionary Keyword search with Vigenère/Beaufort mixed mode
5. K1/K2/K3 Tableau coordinate extraction
"""

import sys
from collections import Counter
from itertools import product
from buttcrack.lang import get_model

model = get_model("english")

K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"
ALPH_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

CRIBS = {}
for i, c in enumerate("EASTNORTHEAST"):
    CRIBS[21 + i] = c
for i, c in enumerate("BERLINCLOCK"):
    CRIBS[63 + i] = c

# Physical lines on sculpture:
# Row 25: pos 0..3 (4 chars)
# Row 26: pos 4..34 (31 chars) -> contains pos 21..33 (EASTNORTHEAST)
# Row 27: pos 35..65 (31 chars) -> contains pos 63..65 (BER)
# Row 28: pos 66..96 (31 chars) -> contains pos 66..73 (LINCLOCK)

print("=" * 78)
print(" KRYPTOS K4 — BRAINSTORMED ATTACK RUN")
print("=" * 78)

# ---------------------------------------------------------------------------
# [1] MIXED VIGENÈRE / BEAUFORT REPEATING KEYWORDS
# ---------------------------------------------------------------------------
print("\n[1] MIXED VIGENÈRE / BEAUFORT WITH DICTIONARY KEYWORDS")
print("Testing if a repeating keyword enciphers K4 with position-dependent Vig/Beau flips...")

# Common Kryptos keywords:
KEYWORDS = [
    "KRYPTOS", "PALIMPSEST", "ABSCISSA", "SANBORN", "SCHEIDT",
    "LANGLEY", "VIRGINIA", "BERLIN", "CLOCK", "COMPASS", "LODESTONE",
    "SHADOW", "LIGHT", "NORTHEAST", "EAST", "INVISIBLE", "MAGNETIC",
    "BURIED", "PASSAGE", "MEDIEVAL", "THEOPHILUS", "COLDWAR", "WALL",
    "WEBSTER", "WOMACKA", "COPPER", "NEEDLE", "ARCHIVE", "LAYER"
]

mixed_hits = []

for kw in KEYWORDS:
    L = len(kw)
    for off in range(L):
        for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
            # For each crib pos, check if key char matches Vigenère OR Beaufort:
            # Vig:  C = (P + K) % 26 => K_vig = (C - P) % 26
            # Beau: C = (K - P) % 26 => K_beau = (C + P) % 26
            # VarB: C = (P - K) % 26 => K_var = (P - C) % 26
            
            valid = True
            flip_pattern = []
            for pos, pt_char in CRIBS.items():
                k_char = kw[(pos + off) % L]
                k_val = alph.index(k_char)
                c_val = alph.index(K4_CT[pos])
                p_val = alph.index(pt_char)
                
                k_vig = (c_val - p_val) % 26
                k_beau = (c_val + p_val) % 26
                k_var = (p_val - c_val) % 26
                
                if k_val == k_vig:
                    flip_pattern.append("V")
                elif k_val == k_beau:
                    flip_pattern.append("B")
                elif k_val == k_var:
                    flip_pattern.append("U")
                else:
                    valid = False
                    break
            if valid:
                mixed_hits.append((kw, off, alph_name, "".join(flip_pattern)))

print(f"  Mixed Vig/Beau keyword results: {len(mixed_hits)} matches found.")
if mixed_hits:
    for h in mixed_hits:
        print(f"    HIT: Keyword={h[0]} (off={h[1]}, {h[2]}) Flip pattern: {h[3]}")
else:
    print("  -> No simple dictionary keyword satisfies mixed Vig/Beau mode.")

# ---------------------------------------------------------------------------
# [2] "ID BY ROWS" — INDEPENDENT ROW KEYS
# ---------------------------------------------------------------------------
print("\n[2] 'ID BY ROWS' — INDEPENDENT ROW KEYING")
print("Testing if each physical screen row (Rows 25, 26, 27, 28) has its own repeating key...")

# Row 26 contains all 13 letters of EASTNORTHEAST (indices 17..29 within Row 26).
# Can Row 26 be decrypted by a repeating keyword of period p = 1..15?
row26_ct = K4_CT[4:35] # 31 chars
# Crib in row 26 is at relative indices 17..29:
row26_crib = "EASTNORTHEAST"

row26_survivors = []
for p in range(1, 16):
    for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
        for mode in ["vig", "beau", "var_beau"]:
            # Check if key of period p is consistent with crib at 17..29:
            key_chars = {}
            valid = True
            for j, pt_ch in enumerate(row26_crib):
                rel_pos = 17 + j
                c_val = alph.index(row26_ct[rel_pos])
                p_val = alph.index(pt_ch)
                if mode == "vig":
                    req_k = (c_val - p_val) % 26
                elif mode == "beau":
                    req_k = (c_val + p_val) % 26
                elif mode == "var_beau":
                    req_k = (p_val - c_val) % 26
                    
                rem_idx = rel_pos % p
                if rem_idx in key_chars:
                    if key_chars[rem_idx] != req_k:
                        valid = False
                        break
                else:
                    key_chars[rem_idx] = req_k
            if valid:
                # Reconstruct full row 26 if p <= 13:
                # For periods p <= 13, are all residues determined?
                # residues touched by 17..29:
                touched = { (17 + j) % p for j in range(13) }
                if len(touched) == p: # fully determined!
                    pt_row26 = []
                    for i in range(31):
                        k_val = key_chars[i % p]
                        c_val = alph.index(row26_ct[i])
                        if mode == "vig":
                            p_val = (c_val - k_val) % 26
                        elif mode == "beau":
                            p_val = (k_val - c_val) % 26
                        elif mode == "var_beau":
                            p_val = (c_val + k_val) % 26
                        pt_row26.append(alph[p_val])
                    row_text = "".join(pt_row26)
                    score = model.fitness(row_text)
                    row26_survivors.append((score, p, alph_name, mode, "".join(alph[key_chars[i]] for i in range(p)), row_text))

row26_survivors.sort(key=lambda x: x[0], reverse=True)
print(f"  Row 26 independent key results: {len(row26_survivors)} consistent periodic keys.")
if row26_survivors:
    print("  Top 5 scoring Row 26 plaintexts:")
    for sc, p, aname, mode, k_str, r_pt in row26_survivors[:5]:
        print(f"    Score {sc:.3f} | p={p:2d} ({aname} {mode}) Key='{k_str}':")
        print(f"      PT: {r_pt}")

# ---------------------------------------------------------------------------
# [3] TABLEAU 2D COORDINATE PAIRINGS
# ---------------------------------------------------------------------------
print("\n[3] TABLEAU 2D COORDINATE INTERSECTION ANALYSIS")
print("Mapping (Row, Col) of Ciphertext and Plaintext onto the Kryptos Tableau...")

# On the Kryptos tableau:
# Row r begins with ALPH_K shifted by r.
# Where is character P? In row r, it is at column C = (ALPH_K.index(P) - r) % 26.
# Let's inspect the coordinate properties of EASTNORTHEAST:
print("  Pos | CT PT | Kryptos indices: C_idx, P_idx | (C_idx + P_idx) mod 26 | (C_idx - P_idx) mod 26")
print("  ----+-------+-------------------------------+------------------------+------------------------")
for pos in range(21, 34):
    c = K4_CT[pos]
    p = CRIBS[pos]
    c_idx = ALPH_K.index(c)
    p_idx = ALPH_K.index(p)
    print(f"   {pos+1:2d} |  {c}  {p} | C={c_idx:2d}, P={p_idx:2d}             | sum = {(c_idx+p_idx)%26:2d}             | diff = {(c_idx-p_idx)%26:2d}")

print("\n" + "=" * 78)
print(" BRAINSTORM RUN COMPLETE")
print("=" * 78)
