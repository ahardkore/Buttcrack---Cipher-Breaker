import json
from collections import Counter

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
C = cts['PK9']
N = len(C)

ALPH_K = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'

eng_freq = {
    'A': 0.08167, 'B': 0.01492, 'C': 0.02782, 'D': 0.04253, 'E': 0.12702,
    'F': 0.02228, 'G': 0.02015, 'H': 0.06094, 'I': 0.06966, 'J': 0.00153,
    'K': 0.00772, 'L': 0.04025, 'M': 0.02406, 'N': 0.06749, 'O': 0.07507,
    'P': 0.01929, 'Q': 0.00095, 'R': 0.05987, 'S': 0.06327, 'T': 0.09056,
    'U': 0.02758, 'V': 0.00978, 'W': 0.02360, 'X': 0.00150, 'Y': 0.01974,
    'Z': 0.00074
}

s13 = [0, 2, 9, 10, 10, 6, 7]

def ioc(text):
    counts = Counter(text)
    return sum(v * (v - 1) for v in counts.values()) / (N * (N - 1))

def chi2(text):
    counts = Counter(text)
    val = 0.0
    for ch, p in eng_freq.items():
        exp = N * p
        obs = counts.get(ch, 0)
        val += (obs - exp) ** 2 / exp
    return val

candidates = []
for mask in range(128):
    shifts = [(s13[i] + 13 * ((mask >> i) & 1)) % 26 for i in range(7)]
    key_str = ''.join(ALPH_K[s] for s in shifts)
    z = ''.join(ALPH_K[(ALPH_K.index(ch) - shifts[i % 7]) % 26] for i, ch in enumerate(C))
    ic = ioc(z)
    c2 = chi2(z)
    candidates.append((c2, ic, mask, key_str, z))

candidates.sort() # lowest chi2 first
print("Top 10 candidates by lowest Chi-Square (best fit to English unigrams):")
for c2, ic, mask, key, z in candidates[:10]:
    print(f"Mask {mask:07b} | Key: {key} | chi2: {c2:6.1f} | IoC: {ic:.5f}")
    print(f"  Z: {z[:75]}...\n")

# Also sort by highest IoC
candidates.sort(key=lambda x: -x[1])
print("\nTop 5 candidates by highest Index of Coincidence:")
for c2, ic, mask, key, z in candidates[:5]:
    print(f"Mask {mask:07b} | Key: {key} | chi2: {c2:6.1f} | IoC: {ic:.5f}")
    print(f"  Z: {z[:75]}...\n")
