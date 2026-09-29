# Exhaustive 12-Letter Keyword Sweep for Panels B & C
import os
from collections import Counter

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
STANDARD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Target rank permutations for Panel B and Panel C:
# Panel B: [23, 25, 26, 16, 20, 37, 39, 7, 31, 33, 32, 36]
pb_cols = [23, 25, 26, 16, 20, 37, 39, 7, 31, 33, 32, 36]
pb_sorted = sorted(pb_cols)
pi_B = [pb_sorted.index(c) for c in pb_cols]

# Panel C: [22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6]
pc_cols = [22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6]
pc_sorted = sorted(pc_cols)
pi_C = [pc_sorted.index(c) for c in pc_cols]

print("======================================================================")
print("12-LETTER KEYWORD & REFLECTION SWEEP FOR PANELS B & C")
print("======================================================================")
print(f"Panel B Permutation pi_B: {pi_B}")
print(f"Panel C Permutation pi_C: {pi_C}\n")

# 1. Symmetry Analysis on pi_B and pi_C (in Z_12, x + y = 11)
def analyze_symmetry(name, perm):
    print(f"--- Symmetry Analysis for {name} ---")
    center_sums = []
    for x in range(6):
        comp = 11 - x
        p1 = perm.index(x)
        p2 = perm.index(comp)
        center_sums.append(p1 + p2)
        print(f"  Pair ({x:2d}, {comp:2d}): pos {p1:2d} and pos {p2:2d} -> pos_sum = {p1+p2:2d}, dist = {abs(p1-p2):2d}")
    c_counts = Counter(center_sums)
    print(f"  Pos sums distribution: {dict(sorted(c_counts.items()))}\n")

analyze_symmetry("Panel B", pi_B)
analyze_symmetry("Panel C", pi_C)

# 2. Load 12-letter words
words_12 = set()
for fname in ["words_12.txt", "all_words.txt", "craft_words_12.txt"]:
    if os.path.exists(fname):
        with open(fname) as f:
            for line in f:
                w = line.strip().upper()
                if len(w) == 12 and w.isalpha():
                    words_12.add(w)

print(f"Loaded {len(words_12)} distinct 12-letter words.")

# Test Keyword to Permutation
def word_to_perm_std(w):
    return [i for i, c in sorted(enumerate(w), key=lambda x: x[1])]

def word_to_perm_kr(w):
    return [i for i, c in sorted(enumerate(w), key=lambda x: KRYPTOS.index(x[1]))]

matches_B = []
matches_C = []

pi_B_inv = [pi_B.index(i) for i in range(12)]
pi_C_inv = [pi_C.index(i) for i in range(12)]

for w in words_12:
    p_std = word_to_perm_std(w)
    p_kr  = word_to_perm_kr(w)
    
    if p_std == pi_B or p_std == pi_B_inv: matches_B.append((w, "Std", p_std == pi_B))
    if p_kr  == pi_B or p_kr  == pi_B_inv: matches_B.append((w, "Kr",  p_kr == pi_B))
    if p_std == pi_C or p_std == pi_C_inv: matches_C.append((w, "Std", p_std == pi_C))
    if p_kr  == pi_C or p_kr  == pi_C_inv: matches_C.append((w, "Kr",  p_kr == pi_C))

print(f"Exact 12-letter keyword matches for Panel B: {len(matches_B)}")
for m in matches_B[:10]: print("  Panel B Match:", m)

print(f"Exact 12-letter keyword matches for Panel C: {len(matches_C)}")
for m in matches_C[:10]: print("  Panel C Match:", m)

# 3. Check repeated sub-keywords:
# Length 3 (x4), Length 4 (x3), Length 6 (x2)
print("\n--- Scanning for Repeated Sub-Keywords (3x4, 4x3, 6x2) ---")
subwords = set()
with open("all_words.txt") as f:
    for line in f:
        w = line.strip().upper()
        if w.isalpha() and len(w) in [3, 4, 6]:
            subwords.add(w)

rep_matches_B = []
rep_matches_C = []
for sw in subwords:
    rep_w = sw * (12 // len(sw))
    p_std = word_to_perm_std(rep_w)
    p_kr  = word_to_perm_kr(rep_w)
    if p_std == pi_B or p_std == pi_B_inv: rep_matches_B.append((sw, "Std"))
    if p_kr  == pi_B or p_kr  == pi_B_inv: rep_matches_B.append((sw, "Kr"))
    if p_std == pi_C or p_std == pi_C_inv: rep_matches_C.append((sw, "Std"))
    if p_kr  == pi_C or p_kr  == pi_C_inv: rep_matches_C.append((sw, "Kr"))

print(f"Repeated sub-keyword matches for Panel B: {len(rep_matches_B)}")
print(f"Repeated sub-keyword matches for Panel C: {len(rep_matches_C)}")
