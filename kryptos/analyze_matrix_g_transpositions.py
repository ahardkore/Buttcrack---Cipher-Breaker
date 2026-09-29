import numpy as np, sys
sys.path.insert(0, 'buttcrack/src')
from buttcrack.scoring import NgramScorer
from buttcrack.wordlm import word_segment

scorer = NgramScorer()

G_rows = [
    "UIRERTAHIHIO",
    "TSMRLOCNSDHH",
    "NWOWEMOSALSO",
    "MDTUNRNAUENO",
    "SOIHFSNLIRSN",
    "ASSETIRNFNSW",
    "OCEHMAHADCAE",
    "FTGTDNIONOCE",
    "WFETREEEEPSD",
    "SALRNEEIFDIH",
    "UITAONLOFSSI",
    "EHAHSSDSOOFU"
]

G = np.array([[ord(c) - ord('A') for c in row] for row in G_rows], dtype=int)
H, W = G.shape

print(f"Matrix G shape: {H} x {W}")

# Test 1: Serpentine (boustrophedon) rows
serp_rows = []
for r in range(H):
    if r % 2 == 0:
        serp_rows.append(''.join(chr(ord('A') + c) for c in G[r, :]))
    else:
        serp_rows.append(''.join(chr(ord('A') + c) for c in G[r, ::-1]))
s1 = ''.join(serp_rows)
print(f"Serpentine rows score: {scorer.average(s1):.4f}")

# Test 2: Serpentine cols
serp_cols = []
for c in range(W):
    if c % 2 == 0:
        serp_cols.append(''.join(chr(ord('A') + G[r, c]) for r in range(H)))
    else:
        serp_cols.append(''.join(chr(ord('A') + G[r, c]) for r in range(H - 1, -1, -1)))
s2 = ''.join(serp_cols)
print(f"Serpentine cols score: {scorer.average(s2):.4f}")

# Test 3: Diagonal read-outs
diag_fwd = []
for d in range(H + W - 1):
    for r in range(max(0, d - W + 1), min(H, d + 1)):
        c = d - r
        diag_fwd.append(chr(ord('A') + G[r, c]))
s3 = ''.join(diag_fwd)
print(f"Diagonal fwd score: {scorer.average(s3):.4f}")

# Test 4: Spiral inward
spiral = []
top, bottom, left, right = 0, H - 1, 0, W - 1
while top <= bottom and left <= right:
    for c in range(left, right + 1): spiral.append(chr(ord('A') + G[top, c]))
    top += 1
    for r in range(top, bottom + 1): spiral.append(chr(ord('A') + G[r, right]))
    right -= 1
    if top <= bottom:
        for c in range(right, left - 1, -1): spiral.append(chr(ord('A') + G[bottom, c]))
        bottom -= 1
    if left <= right:
        for r in range(bottom, top - 1, -1): spiral.append(chr(ord('A') + G[r, left]))
        left += 1
s4 = ''.join(spiral)
print(f"Spiral inward score: {scorer.average(s4):.4f}")

# Test 5: Can we anagram each row individually to form valid English words?
from buttcrack.words import _words
dict_words = set(_words())

print("\n--- Testing Individual Row Anagrams against English Dictionary ---")
for r in range(H):
    row_chars = G_rows[r]
    from collections import Counter
    rc = Counter(row_chars)
    matching_words = []
    for w in dict_words:
        if 4 <= len(w) <= 12:
            wc = Counter(w)
            if all(rc[ch] >= wc[ch] for ch in wc):
                matching_words.append(w)
    matching_words.sort(key=lambda w: (-len(w), w))
    print(f"Row {r:2d} ({row_chars}): {len(matching_words)} candidate sub-words | Top: {matching_words[:8]}")
