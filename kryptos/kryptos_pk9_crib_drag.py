#!/usr/bin/env python3
"""Targeted crib-dragging engine for PK9 based on the Pellegrin needle narrative.
"""

import json
from collections import Counter

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK9"]

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

with open("words_alpha.txt") as f:
    words = set(w.strip().upper() for w in f if len(w.strip()) >= 4)

# Candidate cribs based on the storyline
cribs = [
    "TENYEARS", "TENYEARSPASSED", "EVERYDAY", "NEEDLE", "NEEDLES",
    "GUTTER", "WHITESMITH", "WORKSHOP", "PRACTICE", "MAKING",
    "THEKNOT", "UNRAVEL", "PELLEGRIN", "ARCHIVE", "RECORD",
    "THREAD", "LETTERS", "SURGICAL", "INSTRUMENT", "SPLITAHAIR",
    "ATLAST", "FINALLY", "YEARS", "MONTHS", "STUDIED", "LEARNED",
    "FORGED", "CRAFT", "ANVIL", "HAMMER", "STEEL", "IRON",
    "INSCRIBED", "ACCESS", "ROUTE", "FAILED", "SUCCEEDED"
]

print(f"Testing {len(cribs)} narrative cribs across all positions of PK9...")

hits = []
for crib in cribs:
    L = len(crib)
    for pos in range(len(ct) - L + 1):
        ct_sub = ct[pos:pos+L]
        
        # Test KRYPTOS Quagmire III
        key_kry = [ALPH[(ALPH.index(c) - ALPH.index(p)) % 26] for c, p in zip(ct_sub, crib)]
        
        # Check if key repeats at period 7 (i.e. key_kry[i] == key_kry[i+7])
        repeats = sum(1 for i in range(L - 7) if key_kry[i] == key_kry[i+7])
        if repeats >= 2 or (L >= 10 and repeats >= 1):
            hits.append((repeats, crib, pos, "".join(key_kry), "KRYPTOS"))
            
        # Test STD Vigenere
        key_std = [chr((ord(c) - ord(p)) % 26 + 65) for c, p in zip(ct_sub, crib)]
        repeats_std = sum(1 for i in range(L - 7) if key_std[i] == key_std[i+7])
        if repeats_std >= 2 or (L >= 10 and repeats_std >= 1):
            hits.append((repeats_std, crib, pos, "".join(key_std), "STD"))

hits.sort(reverse=True)
print(f"Found {len(hits)} periodic key matches:")
for rep, crib, pos, k, mode in hits[:15]:
    print(f"[{mode}] Crib '{crib}' at pos {pos:3d}: {rep} periodic matches! Key snippet: {k}")
