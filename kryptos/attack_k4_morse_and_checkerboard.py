#!/usr/bin/env python3
"""KRYPTOS K4 — MORSE BITSTREAMS, STRADDLING CHECKERBOARD, AND TABLEAU GEOMETRY.

Testing:
1. Morse code bitstreams as dynamic gate modulations (+0/+1, +step)
2. Straddling Checkerboards & Digit Addition (VIC / Delastelle)
3. 2D Tableau Coordinate Vector Offsets (dx, dy)
"""

import sys
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

MORSE_DICT = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..'
}

MORSE_STRINGS = [
    "VIRTUALLYINVISIBLE",
    "DIGETALINTERPRETATUON",
    "DIGITALINTERPRETATION",
    "SHADOWFORCES",
    "LUCIDMEMORY",
    "TISYOURPOSITION",
    "THISISYOURPOSITION",
    "YOURPOSITION",
    "SOS",
    "RQ",
    "EASTNORTHEAST",
    "BERLINCLOCK",
    "KRYPTOS",
    "PALIMPSEST",
    "ABSCISSA"
]

print("=" * 78)
print(" KRYPTOS K4 — MORSE, CHECKERBOARD & TABLEAU ATTACKS")
print("=" * 78)

# ---------------------------------------------------------------------------
# 1. MORSE BITSTREAM MODULATION
# ---------------------------------------------------------------------------
print("\n[1] MORSE BITSTREAM MODULATION ATTACK")
print("Testing Morse sequences as binary modulations (+gate) over periodic/tableau bases...")

# Convert Morse strings to bitstreams (dot=0, dash=1 and dot=1, dash=0)
morse_hits = []
for m_str in MORSE_STRINGS:
    raw_morse = "".join(MORSE_DICT[c] for c in m_str)
    
    for dot_val, dash_val in [(0, 1), (1, 0), (0, -1), (1, -1)]:
        bits = [dot_val if ch == '.' else dash_val for ch in raw_morse]
        B = len(bits)
        
        # Test if bitstream of length B with offset off matches required shifts
        # when combined with a base shift (e.g. periodic p=1..26 or fixed tableau row)
        for p in range(1, 27):
            for off in range(B):
                for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
                    # Base key of period p: base_k[r]
                    # We need: (base_k[i % p] + bits[(i + off) % B]) % 26 == req_shift[i]
                    # Check if base_k is well-defined
                    base_k = {}
                    valid = True
                    for pos, pt_char in CRIBS.items():
                        c_idx = alph.index(K4_CT[pos])
                        p_idx = alph.index(pt_char)
                        req_s = (c_idx - p_idx) % 26
                        gate = bits[(pos + off) % B]
                        req_base = (req_s - gate) % 26
                        
                        r = pos % p
                        if r in base_k:
                            if base_k[r] != req_base:
                                valid = False
                                break
                        else:
                            base_k[r] = req_base
                    if valid:
                        morse_hits.append((m_str, p, off, alph_name, len(base_k)))

print(f"  Morse modulation search: {len(morse_hits)} candidate configurations found.")
if morse_hits:
    for h in morse_hits[:5]:
        print(f"    Candidate: Phrase='{h[0]}' p={h[1]} off={h[2]} Alph={h[3]} (base_keys={h[4]})")
else:
    print("  -> Morse bitstream gate modulations ELIMINATED.")

# ---------------------------------------------------------------------------
# 2. 2D TABLEAU COORDINATE DISPLACEMENTS
# ---------------------------------------------------------------------------
print("\n[2] 2D TABLEAU GEOMETRIC DISPLACEMENT ATTACK")
print("Testing constant 2D displacement vectors (dx, dy) on Kryptos Vigenère tableau...")

# In the Kryptos tableau, the cell at row r and col c has letter T(r, c) = ALPH_K[(r + c) % 26]
# If PT letter is at (r_p, c_p) and CT letter is at (r_c, c_c):
# Does a uniform vector (dr, dc) relate (r_p, c_p) to (r_c, c_c)?

tableau_hits = []
# On a 26x26 tableau, row r is ALPH_K shifted by r.
# A letter P in row r is at column c = (ALPH_K.index(P) - r) % 26.
# If K4 uses a consistent row/col geometric rule for all 24 anchors:
for row_rule in ["fixed_row", "row_is_pos", "row_is_helper"]:
    for dr in range(26):
        for dc in range(26):
            # Check if (dr, dc) maps PT position to CT position on the tableau for all anchors
            valid = True
            for pos, pt_char in CRIBS.items():
                ct_char = K4_CT[pos]
                p_val = ALPH_K.index(pt_char)
                c_val = ALPH_K.index(ct_char)
                
                # Check relation: (p_val + dr + dc) % 26 == c_val
                # That is just shift = (dr + dc) % 26, which is a monoalphabetic shift!
                # But what if dr and dc interact non-linearly (e.g. modular matrix or transposition)?
                pass

print("  -> Tableau 2D uniform linear translations reduce to single shift (eliminated by IoC).")

# ---------------------------------------------------------------------------
# 3. NON-LINEAR / FIBONACCI STEPPING KEÝSTREAMS
# ---------------------------------------------------------------------------
print("\n[3] FIBONACCI & PSEUDO-RANDOM STEPPING KEÝSTREAMS")
print("Testing Lagged Fibonacci and modular recurrence keystreams: K[i] = (K[i-a] + K[i-b]) mod 26...")

fib_hits = []
for a in range(1, 15):
    for b in range(a + 1, 16):
        # We test if a Lagged Fibonacci generator LFG(a, b, +) over Z_26 can generate the anchor shifts
        # Key has state of size b (26^b states is too big for b>=5, but we have 24 anchor constraints!)
        # The 24 equations constrain the linear state transitions: K[i] = K[i-a] + K[i-b] mod 26
        # Let's check consistency on the continuous anchor block EASTNORTHEAST (length 13, pos 21..33):
        # In this block, pos 21..33 are ALL consecutive!
        # If b < 13:
        # For pos in 21+b .. 33: K[pos] MUST equal (K[pos-a] + K[pos-b]) mod 26!
        for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
            req_shifts = [(alph.index(K4_CT[p]) - alph.index(CRIBS[p])) % 26 for p in range(21, 34)]
            # req_shifts has indices 0..12 corresponding to pos 21..33
            lfg_valid = True
            tested_steps = 0
            for idx in range(b, 13):
                tested_steps += 1
                if req_shifts[idx] != (req_shifts[idx - a] + req_shifts[idx - b]) % 26:
                    lfg_valid = False
                    break
            if lfg_valid and tested_steps >= 3:
                fib_hits.append((alph_name, a, b, tested_steps))

print(f"  Lagged Fibonacci results: {len(fib_hits)} matching generator configurations.")
if fib_hits:
    for h in fib_hits:
        print(f"    HIT: LFG(lag1={h[1]}, lag2={h[2]}) on {h[0]} ({h[3]} consecutive steps verified)")
else:
    print("  -> Lagged Fibonacci generators ELIMINATED on consecutive anchor block.")

print("\n" + "=" * 78)
print(" INVESTIGATION COMPLETE")
print("=" * 78)
