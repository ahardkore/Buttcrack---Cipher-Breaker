#!/usr/bin/env python3
"""KRYPTOS K4 — MORSE CODE OVER 26x26 TABLEAU TESTING ENGINE.

Models and tests the physical theory of Morse code copper plate superimposition:
1. Full Morse timing bitstreams (1-unit dot, 3-unit dash, inter-element/letter/word spaces)
2. Token Morse bitstreams (dot=1, dash=1, space=0 or dot=1, dash=2)
3. 2D 26x26 Morse Mask generation (raster, serpentine, vertical layouts)
4. Traversal readouts across 26x26 Tableau:
   - Row-major, Column-major, Diagonal, Spiral, Boustrophedon
5. Geometric variations:
   - 4 Rotations (0°, 90°, 180°, 270°), Horizontal & Vertical Flips
   - Placements across all (r0, c0) 2D offsets
6. Exact algebraic anchor verification (EASTNORTHEAST & BERLINCLOCK)
7. Statistical language scoring of surviving candidate plaintexts
"""

import sys
import math
from itertools import product
from collections import defaultdict
from buttcrack.lang import get_model

model = get_model("english")

K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"
ALPH_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

# 26x26 Kryptos Keyed Tableau:
TABLEAU_26x26 = [ALPH_K[r:] + ALPH_K[:r] for r in range(26)]

# 24 Anchor Ground Truth:
CRIBS = {}
for i, c in enumerate("EASTNORTHEAST"):
    CRIBS[21 + i] = c
for i, c in enumerate("BERLINCLOCK"):
    CRIBS[63 + i] = c

# Morse code dictionary:
MORSE_MAP = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..'
}

# The physical Morse inscriptions on Kryptos:
MORSE_PANELS = [
    "VIRTUALLY INVISIBLE",
    "DIGETAL INTERPRETATUON",
    "SHADOW FORCES",
    "LUCID MEMORY",
    "T IS YOUR POSITION",
    "SOS",
    "RQ"
]

print("=" * 78)
print(" KRYPTOS K4 — MORSE CODE OVER 26x26 TABLEAU TESTING ENGINE")
print("=" * 78)

# ---------------------------------------------------------------------------
# 1. BUILD MULTIPLE 2D 26x26 MORSE APERTURE MASKS
# ---------------------------------------------------------------------------
print("\n[1] GENERATING PHYSICAL MORSE 2D MASKS (676 CELLS)")

# Method A: Standard International Morse Timing Stream
# Dot=1, Dash=111, intra-char=0, inter-char=000, inter-word=0000000
def to_timing_stream(text):
    stream = []
    words = text.split()
    for w_idx, word in enumerate(words):
        for l_idx, letter in enumerate(word):
            code = MORSE_MAP.get(letter, "")
            for el_idx, el in enumerate(code):
                if el == '.':
                    stream.append(1)
                elif el == '-':
                    stream.extend([1, 1, 1])
                if el_idx < len(code) - 1:
                    stream.append(0) # 1 unit between elements
            if l_idx < len(word) - 1:
                stream.extend([0, 0, 0]) # 3 units between letters
        if w_idx < len(words) - 1:
            stream.extend([0, 0, 0, 0, 0, 0, 0]) # 7 units between words
    return stream

# Method B: Compact Token Stream (Dot=1, Dash=1, Space=0)
def to_token_stream(text):
    stream = []
    for ch in text:
        if ch in MORSE_MAP:
            for el in MORSE_MAP[ch]:
                stream.append(1) # hole
                stream.append(0) # space
            stream.append(0) # extra letter space
        elif ch == ' ':
            stream.extend([0, 0])
    return stream

all_text = " ".join(MORSE_PANELS)
timing_bits = to_timing_stream(all_text)
token_bits = to_token_stream(all_text)

print(f"  Concatenated Morse Panels: \"{all_text}\"")
print(f"  Timing Stream Bit Count  : {len(timing_bits)} bits")
print(f"  Token Stream Bit Count   : {len(token_bits)} bits")

# Pad or repeat streams to fill 676 cells (26x26):
def make_grid(bits, fill_type="repeat"):
    grid = [[0]*26 for _ in range(26)]
    for idx in range(676):
        r, c = idx // 26, idx % 26
        if idx < len(bits):
            grid[r][c] = bits[idx]
        elif fill_type == "repeat":
            grid[r][c] = bits[idx % len(bits)]
        else:
            grid[r][c] = 0
    return grid

MASKS = {
    "Timing_Repeat": make_grid(timing_bits, "repeat"),
    "Timing_ZeroPad": make_grid(timing_bits, "zero"),
    "Token_Repeat": make_grid(token_bits, "repeat"),
    "Token_ZeroPad": make_grid(token_bits, "zero")
}

# Also add individual panel grids (e.g. "T IS YOUR POSITION" alone, "VIRTUALLY INVISIBLE" alone):
for p in MORSE_PANELS:
    if len(p) >= 3:
        p_bits = to_timing_stream(p)
        MASKS[f"Panel_{p[:12]}_Timing"] = make_grid(p_bits, "repeat")

print(f"  Total 2D Morse Masks constructed: {len(MASKS)}")

# ---------------------------------------------------------------------------
# 2. ROTATION & FLIP TRANSFORMATIONS
# ---------------------------------------------------------------------------
def rotate_grid_90(grid):
    return [[grid[25 - c][r] for c in range(26)] for r in range(26)]

def flip_h(grid):
    return [[grid[r][25 - c] for c in range(26)] for r in range(26)]

def flip_v(grid):
    return [[grid[25 - r][c] for c in range(26)] for r in range(26)]

def get_orientations(grid):
    orientations = []
    g = grid
    for rot in [0, 90, 180, 270]:
        orientations.append((f"rot_{rot}", g))
        orientations.append((f"rot_{rot}_flipH", flip_h(g)))
        orientations.append((f"rot_{rot}_flipV", flip_v(g)))
        g = rotate_grid_90(g)
    return orientations

# ---------------------------------------------------------------------------
# 3. TRAVERSAL EXTRACTION & ANCHOR VERIFICATION
# ---------------------------------------------------------------------------
print("\n[2] TESTING APERTURE TRAVERSAL & 24-ANCHOR ALGEBRAIC CONSISTENCY")
print("Scanning all 2D offsets (r0, c0), orientations, traversal paths, and encipherment modes...")

# Required anchor keystream letters:
# In Vigenere: K = (C - P) % 26
# In Beaufort: K = (C + P) % 26
# In VarBeau : K = (P - C) % 26
targets_std_vig = {pos: (ALPH_STD.index(K4_CT[pos]) - ALPH_STD.index(CRIBS[pos])) % 26 for pos in CRIBS}
targets_kr_vig  = {pos: (ALPH_K.index(K4_CT[pos]) - ALPH_K.index(CRIBS[pos])) % 26 for pos in CRIBS}
targets_std_beau = {pos: (ALPH_STD.index(K4_CT[pos]) + ALPH_STD.index(CRIBS[pos])) % 26 for pos in CRIBS}
targets_kr_beau  = {pos: (ALPH_K.index(K4_CT[pos]) + ALPH_K.index(CRIBS[pos])) % 26 for pos in CRIBS}

TARGET_SETS = [
    ("Standard Vig", targets_std_vig, ALPH_STD, "vig"),
    ("KRYPTOS Vig",  targets_kr_vig,  ALPH_K,   "vig"),
    ("Standard Beau", targets_std_beau, ALPH_STD, "beau"),
    ("KRYPTOS Beau",  targets_kr_beau,  ALPH_K,   "beau")
]

def extract_keystream(mask_grid, tableau, r0, c0, path_type="raster"):
    # Shift mask by (r0, c0) over 26x26 tableau:
    extracted = []
    if path_type == "raster":
        for r in range(26):
            for c in range(26):
                mr = (r - r0) % 26
                mc = (c - c0) % 26
                if mask_grid[mr][mc] == 1:
                    extracted.append(tableau[r][c])
    elif path_type == "vertical":
        for c in range(26):
            for r in range(26):
                mr = (r - r0) % 26
                mc = (c - c0) % 26
                if mask_grid[mr][mc] == 1:
                    extracted.append(tableau[r][c])
    elif path_type == "diagonal":
        for d in range(51):
            for r in range(max(0, d - 25), min(26, d + 1)):
                c = d - r
                mr = (r - r0) % 26
                mc = (c - c0) % 26
                if mask_grid[mr][mc] == 1:
                    extracted.append(tableau[r][c])
    elif path_type == "spiral":
        top, bottom, left, right = 0, 25, 0, 25
        while top <= bottom and left <= right:
            for c in range(left, right + 1):
                mr = (top - r0) % 26
                mc = (c - c0) % 26
                if mask_grid[mr][mc] == 1: extracted.append(tableau[top][c])
            top += 1
            for r in range(top, bottom + 1):
                mr = (r - r0) % 26
                mc = (right - c0) % 26
                if mask_grid[mr][mc] == 1: extracted.append(tableau[r][right])
            right -= 1
            if top <= bottom:
                for c in range(right, left - 1, -1):
                    mr = (bottom - r0) % 26
                    mc = (c - c0) % 26
                    if mask_grid[mr][mc] == 1: extracted.append(tableau[bottom][c])
                bottom -= 1
            if left <= right:
                for r in range(bottom, top - 1, -1):
                    mr = (r - r0) % 26
                    mc = (left - c0) % 26
                    if mask_grid[mr][mc] == 1: extracted.append(tableau[r][left])
                left += 1
    return extracted

best_morse_results = []
total_evaluations = 0

for m_name, base_grid in MASKS.items():
    orientations = get_orientations(base_grid)
    for o_name, o_grid in orientations:
        for path in ["raster", "vertical", "diagonal", "spiral"]:
            for r0 in range(26):
                for c0 in range(26):
                    total_evaluations += 1
                    ks = extract_keystream(o_grid, TABLEAU_26x26, r0, c0, path)
                    if len(ks) < 97:
                        continue
                    
                    # Test against all 4 target shift conventions:
                    for t_name, targets, alph, mode in TARGET_SETS:
                        matches = 0
                        for pos, req_val in targets.items():
                            k_char = ks[pos]
                            if alph.index(k_char) == req_val:
                                matches += 1
                        
                        if matches >= 6: # 6 out of 24 (chance expectation is ~0.92)
                            best_morse_results.append((matches, m_name, o_name, path, r0, c0, t_name, ks[:97]))

best_morse_results.sort(key=lambda x: x[0], reverse=True)

print(f"\nCompleted {total_evaluations} mask-aperture configurations.")
print(f"Configurations achieving >= 6 anchor matches: {len(best_morse_results)}")

if best_morse_results:
    print(f"\nTop 5 Highest Scoring Morse Mask Configurations:")
    for matches, m_name, o_name, path, r0, c0, t_name, ks in best_morse_results[:5]:
        print(f"  {matches}/24 Matches | Mask: {m_name} | {o_name} | Path: {path} | Offset: ({r0:2d}, {c0:2d}) | Mode: {t_name}")
        
        # Decode and score:
        # Decrypt K4 with keystream ks
        alph = ALPH_STD if "Standard" in t_name else ALPH_K
        pt = []
        for i in range(97):
            c_val = alph.index(K4_CT[i])
            k_val = alph.index(ks[i])
            if "Vig" in t_name:
                p_val = (c_val - k_val) % 26
            else:
                p_val = (k_val - c_val) % 26
            pt.append(alph[p_val])
        dec_text = "".join(pt)
        fitness = model.fitness(dec_text)
        print(f"    Plaintext Fitness: {fitness:.3f}")
        print(f"    Decrypted Sample : {dec_text[:50]}...")
        print(f"    Keystream Sample : {ks[:50]}...\n")
        
    print("=" * 78)
    if best_morse_results[0][0] == 24:
        print(" BREAKTHROUGH: Exact 24/24 Anchor Match Found!")
    else:
        print(f" VERDICT: Maximum match was {best_morse_results[0][0]}/24 (chance expectation: 0.92, 3-sigma bound: ~5-6).")
        print(" Direct static superimposition of Morse plate timing masks onto the 26x26 Tableau")
        print(" does not yield the 24 confirmed anchor letters.")
    print("=" * 78)
else:
    print("-> No configuration achieved >= 6 matches.")

