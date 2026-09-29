#!/usr/bin/env python3
"""Tests classical cipher families on PK9:
Autokey, Beaufort, Variant Beaufort, Porta, Bifid, Playfair.
"""

import json
from collections import Counter

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK9"]

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

with open("words_alpha.txt") as f:
    words = set(w.strip().upper() for w in f if len(w.strip()) >= 4)

def count_words(txt):
    return sum(1 for i in range(len(txt)-3) if txt[i:i+4] in words)

print("Testing Autokey on PK9...")
# Autokey: key starts with keyword, then continues with plaintext!
# P[i] = (C[i] - K[i]) mod 26
# for i >= len(key), K[i] = P[i - len(key)]
with open("words_alpha.txt") as f:
    dict_words = [w.strip().upper() for w in f if 3 <= len(w.strip()) <= 10]

best_autokey = []
for kw in dict_words[:5000]:
    # test on STD
    pt = []
    for i, c in enumerate(ct):
        if i < len(kw):
            k = ord(kw[i]) - 65
        else:
            k = ord(pt[i - len(kw)]) - 65
        p = chr((ord(c) - 65 - k) % 26 + 65)
        pt.append(p)
    pt_str = "".join(pt)
    w_cnt = count_words(pt_str)
    if w_cnt > 10:
        best_autokey.append((w_cnt, kw, "STD", pt_str))
        
    # test on KRYPTOS
    pt_k = []
    for i, c in enumerate(ct):
        if i < len(kw):
            k = ALPH.index(kw[i])
        else:
            k = ALPH.index(pt_k[i - len(kw)])
        p = ALPH[(ALPH.index(c) - k) % 26]
        pt_k.append(p)
    pt_k_str = "".join(pt_k)
    w_cnt_k = count_words(pt_k_str)
    if w_cnt_k > 10:
        best_autokey.append((w_cnt_k, kw, "KRYPTOS", pt_k_str))

best_autokey.sort(reverse=True)
print(f"Top Autokey hits: {len(best_autokey)}")
for sc, kw, mode, pt in best_autokey[:5]:
    print(f"[{mode}] Word: {kw} (score {sc}) -> {pt[:60]}...")
