import math
from collections import Counter

# Load bigrams
bigrams = {}
total = 0
with open("english_quadgrams.txt") as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) == 2:
            q, cnt = parts[0], float(parts[1])
            for i in range(3):
                bi = q[i:i+2]
                bigrams[bi] = bigrams.get(bi, 0) + cnt
                total += cnt

log_bi = {k: math.log10(v / total) for k, v in bigrams.items()}
floor_bi = math.log10(0.01 / total)

def get_bi_score(c1, c2):
    return log_bi.get(c1 + c2, floor_bi)

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
undone = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF"

cols = [undone[i::7] for i in range(7)]

for name, alph in [("KRYPTOS", ALPH), ("STANDARD", STD)]:
    print(f"\n=== Alphabet: {name} ===")
    for c in range(7):
        col = cols[c]
        best_sc = -1e9
        best_shift = 0
        best_text = ""
        for s in range(26):
            pt = "".join(alph[(alph.index(ch) - s) % 26] for ch in col)
            sc = sum(get_bi_score(pt[i], pt[i+1]) for i in range(len(pt)-1)) / (len(pt)-1)
            if sc > best_sc:
                best_sc = sc
                best_shift = s
                best_text = pt
        print(f"Col {c} best shift={best_shift:2d} (score={best_sc:.3f}): {best_text}")

