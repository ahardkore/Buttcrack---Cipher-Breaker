from collections import Counter
import math

ALPH_K = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
ALPH_S = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# English single-letter frequencies
EFREQ = {
    'A': 0.08167, 'B': 0.01492, 'C': 0.02782, 'D': 0.04253, 'E': 0.12702,
    'F': 0.02228, 'G': 0.02015, 'H': 0.06094, 'I': 0.06966, 'J': 0.00153,
    'K': 0.00772, 'L': 0.04025, 'M': 0.02406, 'N': 0.06749, 'O': 0.07507,
    'P': 0.01929, 'Q': 0.00095, 'R': 0.05987, 'S': 0.06327, 'T': 0.09056,
    'U': 0.02758, 'V': 0.00978, 'W': 0.02360, 'X': 0.00150, 'Y': 0.01974,
    'Z': 0.00074
}

M = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF"

def evaluate_column(col, alph_c, alph_p, mode_name):
    print(f"\n=== Column (len {len(col)}): {mode_name} ===")
    results = []
    L = len(col)
    for s in range(26):
        # Decrypt col with shift s:
        # P = alph_p[(alph_c.index(c) - s) % 26]
        dec = [alph_p[(alph_c.index(c) - s) % 26] for c in col]
        counts = Counter(dec)
        # Dot product with EFREQ
        score = sum((counts[c] / L) * EFREQ[c] for c in EFREQ)
        # Chi-squared
        chi2 = sum(((counts[c] - L * EFREQ[c])**2) / (L * EFREQ[c]) for c in EFREQ)
        results.append((score, chi2, s, alph_p[s], ''.join(dec[:10])))
    
    # Sort by dot product descending
    results.sort(key=lambda x: x[0], reverse=True)
    for score, chi2, s, char_k, preview in results[:5]:
        print(f"  Shift {s:2d} (Key char '{char_k}'): dot={score:.5f}, chi2={chi2:6.1f} | preview: {preview}")

for r in range(7):
    col = M[r::7]
    evaluate_column(col, ALPH_K, ALPH_K, f"Col {r} (Quagmire III)")
