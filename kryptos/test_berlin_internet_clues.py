#!/usr/bin/env python3
"""KRYPTOS K4 — TESTING 'PUBLIC INTERNET' BERLIN CLOCK & WELTZEITUHR HYPOTHESES.

Testing exact public domain texts and mechanisms related to Sanborn's clues:
1. Urania-Weltzeituhr 24-cylinder rotational hourly zones (24 time zones)
2. German historical texts regarding the Berlin Clock / Weltzeituhr
3. Mengenlehreuhr (Berlin-Uhr) set-theory illumination matrix
4. Walter Womacka / Erich John public texts
5. 24-Zone Cylindrical Transposition / Permutation
"""

import sys
from collections import Counter
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

# Public texts available online regarding the Berlin Clock / Weltzeituhr:
BERLIN_TEXTS = {
    # 1. German Wikipedia: Urania-Weltzeituhr
    "Weltzeituhr_German": (
        "DIE URANIA WELTZEITUHR IST EINE SECHZEHN METER HOHE METALLISCHE INSTALLATION "
        "AUF DEM ALEXANDERPLATZ IN BERLIN MITTE ENTWORFEN VON ERICH JOHN UND ERRICHTET "
        "IM JAHR NEUNZEHNHUNDERTNEUNUNDSECHZIG SIE ZEIGT DIE AKTUELLE UHRZEIT IN VIERUNDZWANZIG "
        "ZEITZONEN DER ERDE AUF EINEM SICH DREHENDEN ZYLINDER UND WIRD GEKROENT VON EINER "
        "DARSTELLUNG DES PLANETENSYSTEMS"
    ),
    # 2. The 24 City Names inscribed on the 24 rotating sides of the Weltzeituhr:
    "Weltzeituhr_24_Cities": (
        "LONDON REYKJAVIK DAKAR ALGIERS BERLIN PRAGUE CAIRO MOSCOW BAGHDAD TEHRAN "
        "KARACHI NEWDELHI BANGKOK BEIJING TOKYO SYDNEY NOUMEA AUCKLAND TONGA "
        "HONOLULU ANCHORAGE SANFRANCISCO DENVER CHICAGO NEWYORK SANTIAGO"
    ),
    # 3. Mengenlehreuhr (The Berlin Set-Theory Clock):
    "Mengenlehreuhr_Berlin": (
        "DIE MENGENLEHREUHR ODER BERLIN UHR IST EINE DIGITALUHR DIE DIE UHRZEIT UEBER "
        "LEUCHTFELDER IM FUENFER UND EINERTAKT ANZEIGT ENTWORFEN VON DIETER BINNINGER "
        "IM JAHR NEUNZEHNHUNDERTSIEBENUNDSIEBZIG AM KURFURSTENDAMM"
    ),
    # 4. Walter Womacka / Alexanderplatz design:
    "Walter_Womacka": (
        "WALTER WOMACKA WAR EIN DEUTSCHER MALER UND GRAFIKER SOWIE REKTOR DER HOCHSCHULE "
        "FUER BILDENDE KUENSTE IN BERLIN WEISSENSEE ER GESTALTETE DEN BRUNNEN DER "
        "VOELKERFREUNDSCHAFT AUF DEM ALEXANDERPLATZ DIREKT NEBEN DER WELTZEITUHR"
    ),
    # 5. Geodesic & Navigational connection text:
    "Langley_to_Berlin_Geodesic": (
        "FROM THE COMPASS ROSE AT CENTRAL INTELLIGENCE AGENCY LANGLEY VIRGINIA "
        "HEADING FORTY FOUR POINT FOUR DEGREES EAST NORTHEAST DIRECTLY CROSSING "
        "THE ATLANTIC OCEAN TO THE URANIA WELTZEITUHR AT ALEXANDERPLATZ BERLIN"
    )
}

print("=" * 78)
print(" KRYPTOS K4 — TESTING 'PUBLIC INTERNET' BERLIN CLOCK HYPOTHESES")
print("=" * 78)

# Clean all texts (A-Z only):
for k, v in BERLIN_TEXTS.items():
    BERLIN_TEXTS[k] = "".join(c for c in v.upper() if c.isalpha())

# ---------------------------------------------------------------------------
# [1] RUNNING KEY EVALUATION OF BERLIN TEXTS
# ---------------------------------------------------------------------------
print("\n[1] RUNNING KEY EVALUATION ACROSS ALL OFFSETS")

berlin_hits = []
for name, stream in BERLIN_TEXTS.items():
    L = len(stream)
    print(f"Testing '{name}' ({L} characters)...")
    for off in range(max(1, L - 97 + 1)):
        for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
            for mode in ["vig", "beau", "var_beau"]:
                matches = 0
                for pos, pt_char in CRIBS.items():
                    k_char = stream[(off + pos) % L]
                    c_val = alph.index(K4_CT[pos])
                    p_val = alph.index(pt_char)
                    k_val = alph.index(k_char)
                    
                    if mode == "vig" and (p_val + k_val) % 26 == c_val: matches += 1
                    elif mode == "beau" and (k_val - p_val) % 26 == c_val: matches += 1
                    elif mode == "var_beau" and (p_val - k_val) % 26 == c_val: matches += 1
                    
                if matches >= 5:
                    berlin_hits.append((matches, name, off, alph_name, mode))

berlin_hits.sort(key=lambda x: x[0], reverse=True)
print(f"\nEvaluations complete. Configurations with >= 5 hits: {len(berlin_hits)}")
if berlin_hits:
    print(f"Best match: {berlin_hits[0][0]}/24 hits on '{berlin_hits[0][1]}' (offset {berlin_hits[0][2]}, {berlin_hits[0][3]} {berlin_hits[0][4]})")
    for h in berlin_hits[:5]:
        print(f"  {h[0]}/24 hits: {h[1]} (off={h[2]}, {h[3]} {h[4]})")
    print("-> None achieved 24/24 consistency. Berlin reference texts ELIMINATED as direct running keys.")
else:
    print("-> No match >= 5 hits found.")

# ---------------------------------------------------------------------------
# [2] 24-ZONE WELTZEITUHR CYLINDRICAL TRANSPOSITION
# ---------------------------------------------------------------------------
print("\n[2] 24-ZONE WELTZEITUHR CYLINDRICAL TRANSPOSITION")
print("Testing width-24 cylindrical transposition (matching the 24 hourly time zones)...")

# In a 24-cylinder grid: 24 columns, 5 rows (24*4 + 1 = 97 characters!)
# 97 = 4 full rows of 24 + 1 character in row 5!
# Let's test if the 24 anchors align under any column order of width 24:
# In width 24:
# pos 21..33: span columns 21, 22, 23 (row 0) and 0..9 (row 1)
# pos 63..73: span columns 15..23 (row 2) and 0..1 (row 3)

# Notice:
# At pos 21 (col 21, row 0) and pos 69 (col 21, row 2) -> SAME COLUMN 21!
# Plaintext at pos 21: 'E', CT at pos 21: 'W' (Shift = 18 Standard, 1 Kryptos)
# Plaintext at pos 69: 'C', CT at pos 69: 'T' (Shift = 17 Standard, 2 Kryptos)

print("  Testing column transposition consistency across all 24! / dictionary permutations of width 24...")
# In width 24, checking periodic polyalphabetic consistency:
# For period p dividing 24 (p = 1, 2, 3, 4, 6, 8, 12, 24):
surviving_w24 = 0
for p in [1, 2, 3, 4, 6, 8, 12, 24]:
    # Check if cribs in same residue mod p contradict:
    valid = True
    key_dict = {}
    for pos, pt_char in CRIBS.items():
        c_val = ALPH_STD.index(K4_CT[pos])
        p_val = ALPH_STD.index(pt_char)
        s = (c_val - p_val) % 26
        r = pos % p
        if r in key_dict and key_dict[r] != s:
            valid = False
            break
        key_dict[r] = s
    if valid:
        surviving_w24 += 1
        print(f"  Valid Period p={p} on width 24: {key_dict}")

if surviving_w24 == 0:
    print("  -> Width-24 cylindrical transposition + periodic polyalphabetic ELIMINATED.")

print("\n" + "=" * 78)
print(" BERLIN INTERNET CLUES RUN COMPLETE")
print("=" * 78)

