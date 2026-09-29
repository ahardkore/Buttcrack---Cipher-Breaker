import json
import numpy as np

with open("pk_all_ciphertexts.json") as f:
    ct9 = json.load(f)["PK9"]

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
k_to_std = np.array([ord(c) - ord('A') for c in KRYPTOS])
std_to_k = np.zeros(26, dtype=int)
for i, c in enumerate(KRYPTOS):
    std_to_k[ord(c) - ord('A')] = i

ct_kr = np.array([std_to_k[ord(c) - ord('A')] for c in ct9])

eng_freq = np.array([82, 15, 28, 43, 127, 22, 20, 61, 70, 2, 8, 40, 24, 67, 75, 19, 1, 60, 63, 91, 28, 10, 24, 2, 20, 1], dtype=float)
eng_freq /= np.sum(eng_freq)

# Find optimal 28 shifts
p = 28
shifts = []
for col in range(p):
    slice_kr = ct_kr[col::p]
    n_col = len(slice_kr)
    
    best_chi2 = 1e9
    best_s = 0
    for s in range(26):
        p_kr = (slice_kr - s + 26) % 26
        p_std = k_to_std[p_kr]
        counts = np.bincount(p_std, minlength=26)
        expected = n_col * eng_freq
        chi2 = np.sum((counts - expected)**2 / (expected + 0.001))
        if chi2 < best_chi2:
            best_chi2 = chi2
            best_s = s
    shifts.append(best_s)

print("Optimal Period-28 QIII Shifts:")
print(shifts)

# Decrypt
pt = []
for i in range(len(ct9)):
    p_kr = (ct_kr[i] - shifts[i % p] + 26) % 26
    pt.append(KRYPTOS[p_kr])

pt_str = "".join(pt)
print("\nDecrypted with Period-28 QIII Shifts:")
print(pt_str)

from collections import Counter
cnt = Counter(pt_str)
print("\nTop letters:", cnt.most_common(8))
print("Rare letters:", cnt.most_common()[-5:])
