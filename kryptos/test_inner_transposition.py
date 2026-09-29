import json
from collections import Counter

ALPH = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
k2std = [ord(c) - ord('A') for c in ALPH]
hpos = {c: i for i, c in enumerate(ALPH)}

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)

ct9_raw = cts['PK9']
N = len(ct9_raw)

EFREQ = {
    'A': 0.08167, 'B': 0.01492, 'C': 0.02782, 'D': 0.04253, 'E': 0.12702,
    'F': 0.02228, 'G': 0.02015, 'H': 0.06094, 'I': 0.06966, 'J': 0.00153,
    'K': 0.00772, 'L': 0.04025, 'M': 0.02406, 'N': 0.06749, 'O': 0.07507,
    'P': 0.01929, 'Q': 0.00095, 'R': 0.05987, 'S': 0.06327, 'T': 0.09056,
    'U': 0.02758, 'V': 0.00978, 'W': 0.02360, 'X': 0.00150, 'Y': 0.01974,
    'Z': 0.00074
}

shifts28 = []
key28 = []
for r in range(28):
    sl = [ct9_raw[i] for i in range(r, N, 28)]
    L = len(sl)
    scores = []
    for s in range(26):
        dec = [chr(ord('A') + k2std[(hpos[c] - s) % 26]) for c in sl]
        counts = Counter(dec)
        dot = sum((counts[c] / L) * EFREQ[c] for c in EFREQ)
        scores.append((dot, s, ALPH[s], ''.join(dec)))
    scores.sort(key=lambda x: x[0], reverse=True)
    best_dot, best_s, best_k, preview = scores[0]
    shifts28.append(best_s)
    key28.append(best_k)

pt = []
for i, ch in enumerate(ct9_raw):
    s = shifts28[i % 28]
    p_kr = (hpos[ch] - s) % 26
    pt.append(chr(ord('A') + k2std[p_kr]))
Z = ''.join(pt)

print(f"Intermediate stream Z (len {len(Z)}):")
print(Z)

# Format into 12 x 12 grid:
print("\n12 x 12 Grid of Z:")
for r in range(12):
    print(f"Row {r:2d}: {Z[r*12:(r+1)*12]}")
