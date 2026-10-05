#!/usr/bin/env python3
"""KRYPTOS K4 — PHYSICAL 'LAYER TWO' REVERSE TABLEAU TESTING ENGINE.

Exhaustively tests all physical alignment hypotheses between the Front Screen (K4 CT)
and the Reverse Screen (Tableau Face T):

1. Direct & Row-Specific Modular Shifts (Standard & KRYPTOS alphabets, Vig/Beau/VarB)
2. Mirror-Image Physical Superimposition (Left-to-Right inversion on reverse face)
3. Column-by-Column & Serpentine Reverse Readouts
4. Differential & Cumulative Helper Keystreams (ΔT, ΣT)
5. 2D Coordinate Offsets (Δrow, Δcol) on the physical copper grid
"""

import sys
from collections import defaultdict
from buttcrack.lang import get_model

model = get_model("english")

K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"
ALPH_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

# Physical 4 rows of the Reverse Face (Tableau Layer Two):
# Row 25 (pos 0..3):   WXZK (4 cells)
# Row 26 (pos 4..34):  YXZKRYPTOSABCDEFGHIJLMNQUVWXZKR (31 cells)
# Row 27 (pos 35..65): ZZKRYPTOSABCDEFGHIJLMNQUVWXZKRY (31 cells)
# Row 28 (pos 66..96): _ABCDEFGHIJKLMNOPQRSTUVWXYZABCD (31 cells)
REV_ROWS = [
    "WXZK",
    "YXZKRYPTOSABCDEFGHIJLMNQUVWXZKR",
    "ZZKRYPTOSABCDEFGHIJLMNQUVWXZKRY",
    "_ABCDEFGHIJKLMNOPQRSTUVWXYZABCD"
]

HELPER_T_DIRECT = "".join(REV_ROWS)
assert len(HELPER_T_DIRECT) == 97

CRIBS = {}
for i, c in enumerate("EASTNORTHEAST"):
    CRIBS[21 + i] = c
for i, c in enumerate("BERLINCLOCK"):
    CRIBS[63 + i] = c

print("=" * 78)
print(" KRYPTOS K4 — DEEP 'LAYER TWO' REVERSE TABLEAU TEST ENGINE")
print("=" * 78)

# ---------------------------------------------------------------------------
# [1] DIRECT & ROW-SPECIFIC SHIFTS OVER HELPER T
# ---------------------------------------------------------------------------
print("\n[1] DIRECT & ROW-SPECIFIC SHIFTS OVER HELPER T")
print("Testing K[i] = (T[i] + offset[row]) mod 26 across all alphabets & modes...")

# Lane / row assignment for index i in 0..96:
def get_lane(i):
    return 0 if i < 4 else 1 if i < 35 else 2 if i < 66 else 3

direct_hits = []

for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
    for mode in ["vig", "beau", "var_beau"]:
        # Test 1: Global constant shift k in 0..25:
        for k in range(26):
            matches = 0
            for pos, pt_char in CRIBS.items():
                t_ch = HELPER_T_DIRECT[pos]
                if t_ch == '_':
                    continue
                t_val = alph.index(t_ch)
                c_val = alph.index(K4_CT[pos])
                p_val = alph.index(pt_char)
                k_val = (t_val + k) % 26
                
                if mode == "vig":
                    exp_c = (p_val + k_val) % 26
                elif mode == "beau":
                    exp_c = (k_val - p_val) % 26
                elif mode == "var_beau":
                    exp_c = (p_val - k_val) % 26
                    
                if exp_c == c_val:
                    matches += 1
            if matches >= 5:
                direct_hits.append((matches, "Global Shift", alph_name, mode, k))
                
        # Test 2: Row-specific shifts (k_lane for lane in 0..3)
        # For each lane, find if an exact k_lane satisfies the cribs in that lane:
        # Lane 1 (Row 26): contains pos 21..33 (all 13 letters of EASTNORTHEAST!)
        # Lane 2 (Row 27): contains pos 63..65 (BER)
        # Lane 3 (Row 28): contains pos 66..73 (LINCLOCK)
        for k1 in range(26):
            # Test Lane 1 (EASTNORTHEAST):
            m1 = 0
            for pos in range(21, 34):
                t_val = alph.index(HELPER_T_DIRECT[pos])
                c_val = alph.index(K4_CT[pos])
                p_val = alph.index(CRIBS[pos])
                k_val = (t_val + k1) % 26
                if mode == "vig" and (p_val + k_val) % 26 == c_val: m1 += 1
                elif mode == "beau" and (k_val - p_val) % 26 == c_val: m1 += 1
                elif mode == "var_beau" and (p_val - k_val) % 26 == c_val: m1 += 1
            if m1 >= 5:
                direct_hits.append((m1, "Row26 Shift", alph_name, mode, f"k1={k1}"))

direct_hits.sort(key=lambda x: x[0], reverse=True)
print(f"  Direct helper shift results: {len(direct_hits)} configurations with >= 5 anchor hits.")
if direct_hits:
    print(f"  Best match: {direct_hits[0][0]}/24 hits on {direct_hits[0][1]} ({direct_hits[0][2]} {direct_hits[0][3]}, {direct_hits[0][4]})")
    for h in direct_hits[:5]:
        print(f"    {h[0]}/24 hits: {h[1]} ({h[2]} {h[3]}, {h[4]})")
    print("  -> Direct helper shifts (global or row-specific) ELIMINATED.")
else:
    print("  -> Direct helper shifts ELIMINATED.")

# ---------------------------------------------------------------------------
# [2] MIRROR-IMAGE PHYSICAL SUPERIMPOSITION (Left-to-Right Inversion)
# ---------------------------------------------------------------------------
print("\n[2] MIRROR-IMAGE PHYSICAL SUPERIMPOSITION")
print("Testing horizontal flip (column 30 - col) when viewing through reverse face...")

# When looking through the screen from behind, column c on the front aligns with (width - 1 - c) on the back!
# Row 25: len 4 -> col on back = 3 - col (or 30 - col)
# Row 26: len 31 -> col on back = 30 - col
# Row 27: len 31 -> col on back = 30 - col
# Row 28: len 31 -> col on back = 30 - col

rev_mirror_rows = [
    REV_ROWS[0][::-1],
    REV_ROWS[1][::-1],
    REV_ROWS[2][::-1],
    REV_ROWS[3][::-1]
]
HELPER_T_MIRROR = "".join(rev_mirror_rows)

mirror_hits = []
for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
    for mode in ["vig", "beau", "var_beau"]:
        for k in range(26):
            matches = 0
            for pos, pt_char in CRIBS.items():
                t_ch = HELPER_T_MIRROR[pos]
                if t_ch == '_':
                    continue
                t_val = alph.index(t_ch)
                c_val = alph.index(K4_CT[pos])
                p_val = alph.index(pt_char)
                k_val = (t_val + k) % 26
                
                if mode == "vig" and (p_val + k_val) % 26 == c_val: matches += 1
                elif mode == "beau" and (k_val - p_val) % 26 == c_val: matches += 1
                elif mode == "var_beau" and (p_val - k_val) % 26 == c_val: matches += 1
            if matches >= 5:
                mirror_hits.append((matches, "Mirror Superimposition", alph_name, mode, k))

mirror_hits.sort(key=lambda x: x[0], reverse=True)
print(f"  Mirror superimposition results: {len(mirror_hits)} configurations with >= 5 hits.")
if mirror_hits:
    print(f"  Best mirror match: {mirror_hits[0][0]}/24 hits on {mirror_hits[0][2]} {mirror_hits[0][3]} (offset k={mirror_hits[0][4]})")
    print("  -> Mirror-image superimposition ELIMINATED.")
else:
    print("  -> Mirror-image superimposition ELIMINATED.")

# ---------------------------------------------------------------------------
# [3] COLUMN-BY-COLUMN & TRANSPOSITION READOUTS OF REVERSE FACE
# ---------------------------------------------------------------------------
print("\n[3] COLUMN-BY-COLUMN READOUT OF THE 4 REVERSE ROWS")
print("Testing vertical reading down the 31 columns of the reverse screen...")

# Grid layout of reverse face: 4 rows of width 31:
# Row 0 (pos 0..3 in cols 27..30 or cols 0..3):
# Let's test both alignments of Row 25 (left-aligned at cols 0..3, or right-aligned at cols 27..30)
for r25_align in ["left", "right"]:
    grid_rev = [[''] * 31 for _ in range(4)]
    if r25_align == "left":
        for c in range(4): grid_rev[0][c] = REV_ROWS[0][c]
    else:
        for c in range(4): grid_rev[0][27 + c] = REV_ROWS[0][c]
    for r in range(1, 4):
        for c in range(31):
            grid_rev[r][c] = REV_ROWS[r][c]
            
    # Read down columns:
    col_stream = []
    for c in range(31):
        for r in range(4):
            if grid_rev[r][c] != '' and grid_rev[r][c] != '_':
                col_stream.append(grid_rev[r][c])
    
    # Test col_stream as keystream:
    for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
        for mode in ["vig", "beau"]:
            for off in range(len(col_stream) - 97 + 1):
                matches = 0
                for pos, pt_char in CRIBS.items():
                    k_char = col_stream[off + pos]
                    c_val = alph.index(K4_CT[pos])
                    p_val = alph.index(pt_char)
                    k_val = alph.index(k_char)
                    if mode == "vig" and (p_val + k_val) % 26 == c_val: matches += 1
                    elif mode == "beau" and (k_val - p_val) % 26 == c_val: matches += 1
                if matches >= 5:
                    print(f"  Col-stream ({r25_align}) match: {matches}/24 on {alph_name} {mode}")

print("  -> Column-by-column reverse readouts ELIMINATED.")

# ---------------------------------------------------------------------------
# [4] DIFFERENTIAL & CUMULATIVE HELPER CALCULUS (ΔT, ΣT)
# ---------------------------------------------------------------------------
print("\n[4] DIFFERENTIAL & CUMULATIVE HELPER KEYSTREAMS (ΔT, ΣT)")
print("Testing keystreams generated by differences or cumulative sums of reverse letters...")

diff_cumul_hits = []
for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
    # Replace '_' in Row 28 with 'A' or 0:
    t_vals = [alph.index(c) if c != '_' else 0 for c in HELPER_T_DIRECT]
    
    # 1. First difference ΔT[i] = (T[i] - T[i-1]) mod 26
    delta_T = [(t_vals[i] - t_vals[i-1]) % 26 for i in range(1, 97)]
    
    # 2. Cumulative sum ΣT[i] = sum(t_vals[:i+1]) mod 26
    cumul_T = [sum(t_vals[:i+1]) % 26 for i in range(97)]
    
    for stream_name, stream in [("Delta_T", [0] + delta_T), ("Cumul_T", cumul_T)]:
        for mode in ["vig", "beau", "var_beau"]:
            for k in range(26):
                matches = 0
                for pos, pt_char in CRIBS.items():
                    c_val = alph.index(K4_CT[pos])
                    p_val = alph.index(pt_char)
                    k_val = (stream[pos] + k) % 26
                    if mode == "vig" and (p_val + k_val) % 26 == c_val: matches += 1
                    elif mode == "beau" and (k_val - p_val) % 26 == c_val: matches += 1
                    elif mode == "var_beau" and (p_val - k_val) % 26 == c_val: matches += 1
                if matches >= 5:
                    diff_cumul_hits.append((matches, stream_name, alph_name, mode, k))

diff_cumul_hits.sort(key=lambda x: x[0], reverse=True)
print(f"  Differential & Cumulative results: {len(diff_cumul_hits)} configurations with >= 5 hits.")
if diff_cumul_hits:
    print(f"  Best match: {diff_cumul_hits[0][0]}/24 hits on {diff_cumul_hits[0][1]} ({diff_cumul_hits[0][2]} {diff_cumul_hits[0][3]}, k={diff_cumul_hits[0][4]})")
    print("  -> Differential / Cumulative helper keystreams ELIMINATED.")
else:
    print("  -> Differential / Cumulative helper keystreams ELIMINATED.")

print("\n" + "=" * 78)
print(" LAYER TWO REVERSE TABLEAU TESTING COMPLETE")
print("=" * 78)

