# Automated Dictionary Search on Q8 and Q9 Sequences
import math
from collections import Counter

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
STANDARD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

q8 = [0, 8, 16, 15, 16, 3, 6, 20]
q9 = [16, 0, 19, 9, 7, 23, 6, 16, 18]

q8_kr = "".join(KRYPTOS[x] for x in q8) # KBJIJPSQ
q9_kr = "".join(KRYPTOS[x] for x in q9) # JKNCAWSJM

q8_std = "".join(STANDARD[x] for x in q8) # AIQPQDGU
q9_std = "".join(STANDARD[x] for x in q9) # QATJHXGQS

print("======================================================================")
print("AUTOMATED DICTIONARY SEARCH ON Q8 AND Q9 SEQUENCES")
print("======================================================================")
print(f"Q8: {q8} -> Kryptos: {q8_kr} | Standard: {q8_std}")
print(f"Q9: {q9} -> Kryptos: {q9_kr} | Standard: {q9_std}\n")

# 1. Caesar Shift Sweeps on Q8 and Q9
print("--- 1. Evaluating all 26 Caesar Shifts on Q8 and Q9 ---")
for s in range(26):
    sh_q8_kr = "".join(KRYPTOS[(x - s + 26) % 26] for x in q8)
    sh_q9_kr = "".join(KRYPTOS[(x - s + 26) % 26] for x in q9)
    sh_q8_std = "".join(STANDARD[(x - s + 26) % 26] for x in q8)
    sh_q9_std = "".join(STANDARD[(x - s + 26) % 26] for x in q9)
    
    # Check if any common syllables or fragments appear
    for sub in ["ING", "THE", "AND", "ART", "FOR", "MEN", "MAN", "RED", "ICE", "HAM"]:
        if sub in sh_q8_kr or sub in sh_q8_std:
            print(f"  Q8 Shift {s:2d}: Kr={sh_q8_kr}, Std={sh_q8_std} (contains {sub})")
        if sub in sh_q9_kr or sub in sh_q9_std:
            print(f"  Q9 Shift {s:2d}: Kr={sh_q9_kr}, Std={sh_q9_std} (contains {sub})")

# 2. Dictionary Search: Words of length 8 and 9
print("\n--- 2. Dictionary Word Search (Hamming Distance & Vigenere Difference) ---")
words_8 = set()
words_9 = set()
with open("all_words.txt") as f:
    for line in f:
        w = line.strip().upper()
        if w.isalpha():
            if len(w) == 8: words_8.add(w)
            elif len(w) == 9: words_9.add(w)

print(f"Loaded {len(words_8)} 8-letter words and {len(words_9)} 9-letter words.")

# Check for constant shift difference: diff[i] = (q[i] - word[i]) % 26
print("\nScanning for exact monoalphabetic / Caesar offsets from real dictionary words:")
q8_matches = []
for w in words_8:
    diff_kr = [(q8[i] - KRYPTOS.index(w[i])) % 26 for i in range(8)]
    diff_std = [(q8[i] - (ord(w[i]) - ord("A"))) % 26 for i in range(8)]
    if len(set(diff_kr)) == 1:
        q8_matches.append((w, "Kr Caesar", diff_kr[0]))
    if len(set(diff_std)) == 1:
        q8_matches.append((w, "Std Caesar", diff_std[0]))

print(f"Exact Caesar dictionary word matches for Q8: {len(q8_matches)}")
if q8_matches:
    for m in q8_matches: print("  Match:", m)

q9_matches = []
for w in words_9:
    diff_kr = [(q9[i] - KRYPTOS.index(w[i])) % 26 for i in range(9)]
    diff_std = [(q9[i] - (ord(w[i]) - ord("A"))) % 26 for i in range(9)]
    if len(set(diff_kr)) == 1:
        q9_matches.append((w, "Kr Caesar", diff_kr[0]))
    if len(set(diff_std)) == 1:
        q9_matches.append((w, "Std Caesar", diff_std[0]))

print(f"Exact Caesar dictionary word matches for Q9: {len(q9_matches)}")
if q9_matches:
    for m in q9_matches: print("  Match:", m)

# 3. Anagram search on Q8 and Q9
print("\n--- 3. Anagram & Subword Analysis ---")
subwords_q8 = []
c_q8 = Counter(q8_kr)
for w in words_8:
    if len(w) >= 4 and len(w) <= 8:
        cw = Counter(w)
        if all(cw[ch] <= c_q8[ch] for ch in cw):
            subwords_q8.append(w)

subwords_q9 = []
c_q9 = Counter(q9_kr)
for w in words_9:
    if len(w) >= 4 and len(w) <= 9:
        cw = Counter(w)
        if all(cw[ch] <= c_q9[ch] for ch in cw):
            subwords_q9.append(w)

print(f"Formable subwords from Q8 (KBJIJPSQ): {len(subwords_q8)}")
if subwords_q8:
    print("  Subwords:", subwords_q8[:10])

print(f"Formable subwords from Q9 (JKNCAWSJM): {len(subwords_q9)}")
if subwords_q9:
    print("  Subwords:", subwords_q9[:10])
