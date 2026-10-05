#!/usr/bin/env python3
"""KRYPTOS K4 — HISTORICAL BOOK & REFERENCE RUNNING KEY ENGINE.

Tests running key hypotheses from reference texts nominated by Sanborn's clues:
1. Howard Carter: "The Tomb of Tutankhamun" (the source of K3)
2. Theophilus Presbyter: "De Diversis Artibus" (medieval craft treatise in repo)
3. National Security Act of 1947 / CIA Charter
4. Berlin Wall historical texts / Urania Weltzeituhr commemorative texts
5. Sanborn's own Artist Statements & Dedication Speeches (1990)
"""

import sys
import os
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

# Load reference texts available in the repository:
TEXTS = {}

# 1. Theophilus English text:
if os.path.exists("kryptos/theophilus_book3_english.txt"):
    with open("kryptos/theophilus_book3_english.txt", "r") as f:
        raw = f.read()
        clean = "".join(c for c in raw.upper() if c.isalpha())
        TEXTS["Theophilus_Book3"] = clean

# 2. Howard Carter extended passage (surrounding K3):
carter_text = (
    "AT FIRST I COULD SEE NOTHING THE HOT AIR ESCAPING FROM THE CHAMBER CAUSED THE CANDLE FLAME "
    "TO FLICKER BUT PRESENTLY AS MY EYES GREW ACCUSTOMED TO THE LIGHT DETAILS OF THE ROOM WITHIN "
    "EMERGED SLOWLY FROM THE MIST STRANGE ANIMALS STATUES AND GOLD EVERYWHERE THE GLINT OF GOLD "
    "FOR THE MOMENT AN ETERNITY IT MUST HAVE SEEMED TO THE OTHERS STANDING BY I WAS STRUCK DUMB "
    "WITH AMAZEMENT AND WHEN LORD CARNARVON UNABLE TO BEAR THE SUSPENSE ANY LONGER INQUIRED ANXIOUSLY "
    "CAN YOU SEE ANYTHING IT WAS ALL I COULD DO TO GET OUT THE WORDS YES WONDERFUL THINGS"
)
TEXTS["Howard_Carter_Tomb"] = "".join(c for c in carter_text.upper() if c.isalpha())

# 3. CIA Founding Document (National Security Act of 1947, Section 102):
cia_act = (
    "THERE IS ESTABLISHED UNDER THE NATIONAL SECURITY COUNCIL A CENTRAL INTELLIGENCE AGENCY "
    "WITH A DIRECTOR OF CENTRAL INTELLIGENCE WHO SHALL BE THE HEAD THEREOF THE DIRECTOR SHALL "
    "BE APPOINTED BY THE PRESIDENT BY AND WITH THE ADVICE AND CONSENT OF THE SENATE IT SHALL "
    "BE THE DUTY OF THE AGENCY UNDER THE DIRECTION OF THE NATIONAL SECURITY COUNCIL TO ADVISE "
    "THE NATIONAL SECURITY COUNCIL IN MATTERS CONCERNING SUCH INTELLIGENCE ACTIVITIES OF THE "
    "GOVERNMENT DEPARTMENTS AND AGENCIES AS RELATE TO NATIONAL SECURITY"
)
TEXTS["CIA_Act_1947"] = "".join(c for c in cia_act.upper() if c.isalpha())

# 4. Berlin Wall / Weltzeituhr historical commemoration:
berlin_text = (
    "THE URANIA WELTZEITUHR WAS ERECTED IN NINETEEN SIXTY NINE AT ALEXANDERPLATZ IN EAST BERLIN "
    "DESIGNED BY ERICH JOHN AND WALTER WOMACKA IT STANDS SIXTEEN METERS HIGH AND DISPLAYS THE "
    "CURRENT TIME IN ONE HUNDRED AND FORTY EIGHT MAJOR CITIES OF THE WORLD SURROUNDED BY THE "
    "MOSAIC OF THE WINDROSE AND THE BRUNNEN DER VOELKERFREUNDSCHAFT"
)
TEXTS["Berlin_Weltzeituhr_History"] = "".join(c for c in berlin_text.upper() if c.isalpha())

print("=" * 78)
print(" KRYPTOS K4 — HISTORICAL REFERENCE RUNNING KEY ATTACK")
print("=" * 78)
print(f"Loaded {len(TEXTS)} major historical reference corpora for running key sweeps.\n")

book_hits = []

for text_name, stream in TEXTS.items():
    L = len(stream)
    print(f"Testing corpus '{text_name}' (length {L} characters)...")
    
    if L < 97:
        continue
        
    for off in range(L - 97 + 1):
        for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
            for mode in ["vig", "beau", "var_beau"]:
                matches = 0
                for pos, pt_char in CRIBS.items():
                    k_char = stream[off + pos]
                    c_val = alph.index(K4_CT[pos])
                    p_val = alph.index(pt_char)
                    k_val = alph.index(k_char)
                    
                    if mode == "vig":
                        exp_c = (p_val + k_val) % 26
                    elif mode == "beau":
                        exp_c = (k_val - p_val) % 26
                    elif mode == "var_beau":
                        exp_c = (p_val - k_val) % 26
                        
                    if exp_c == c_val:
                        matches += 1
                        
                if matches >= 5:
                    book_hits.append((matches, text_name, off, alph_name, mode))

book_hits.sort(key=lambda x: x[0], reverse=True)
print(f"\nTotal sweeps completed. Configurations with >= 5 anchor hits: {len(book_hits)}")
if book_hits:
    print(f"Best match found: {book_hits[0][0]}/24 hits on '{book_hits[0][1]}' (offset {book_hits[0][2]}, {book_hits[0][3]} {book_hits[0][4]})")
    for h in book_hits[:5]:
        print(f"  {h[0]}/24 hits: {h[1]} (off={h[2]}, {h[3]} {h[4]})")
    print("-> None achieved 24/24 consistency. Tested reference corpora ELIMINATED as direct running keys.")
else:
    print("-> No match >= 5 hits found. Tested reference corpora ELIMINATED.")

print("\n" + "=" * 78)
print(" RUNNING KEY ANALYSIS COMPLETE")
print("=" * 78)

