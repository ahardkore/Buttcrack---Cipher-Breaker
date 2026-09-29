import json
from collections import Counter
import sys
sys.path.insert(0, 'buttcrack/src')
from buttcrack.transsub import _undo_columnar

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)

ct10 = cts['PK10']
N = len(ct10)

def slice_ioc(s, p):
    slices = [s[i::p] for i in range(p)]
    iocs = []
    for sl in slices:
        m = len(sl)
        if m <= 1: continue
        c = Counter(sl)
        iocs.append(sum(v * (v - 1) for v in c.values()) / (m * (m - 1)))
    return sum(iocs) / len(iocs) if iocs else 0.0

# Load thematic words
with open('all_words.txt') as f:
    words = [w.strip().upper() for w in f if w.strip().isalpha()]

w7 = [w for w in words if len(w) == 7][:500]
w8 = [w for w in words if len(w) == 8][:500]
w9 = [w for w in words if len(w) == 9][:500]

def word_to_order(w):
    idx = list(range(len(w)))
    idx.sort(key=lambda i: (w[i], i))
    return idx

print(f"Testing two-stage keyword transpositions on PK10...")
best_ioc = 0.0
best_pair = None

# Test stage 1: w8, stage 2: w7
# Test stage 1: w9, stage 2: w8
for word_list1, w_len1, word_list2, w_len2 in [(w7, 7, w8, 8), (w8, 8, w9, 9), (w7, 7, w9, 9)]:
    print(f"Testing pairs ({w_len1}, {w_len2})...")
    for w1 in word_list1[:100]:
        o1 = word_to_order(w1)
        s1 = _undo_columnar(ct10, o1, incomplete=False, unit=1)
        for w2 in word_list2[:100]:
            o2 = word_to_order(w2)
            s2 = _undo_columnar(s1, o2, incomplete=False, unit=1)
            for p in [7, 8, 9]:
                val = slice_ioc(s2, p)
                if val > best_ioc:
                    best_ioc = val
                    best_pair = (w1, w2, p, val)
                    if val > 0.050:
                        print(f"SPIKE! Pair ({w1}, {w2}): IoC({p}) = {val:.5f}")

print(f"\nBest Two-Stage Result: {best_pair}")
