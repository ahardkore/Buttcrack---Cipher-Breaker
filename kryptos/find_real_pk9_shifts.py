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
ct_std = np.array([ord(c) - ord('A') for c in ct9])

eng_freq = np.array([82, 15, 28, 43, 127, 22, 20, 61, 70, 2, 8, 40, 24, 67, 75, 19, 1, 60, 63, 91, 28, 10, 24, 2, 20, 1], dtype=float)
eng_freq /= np.sum(eng_freq)

# For each period p in [7, 14, 28]:
for p in [7, 14]:
    print(f"\n=== Period {p} Optimal Shifts on REAL PK9 ===")
    shifts_kr = []
    shifts_std = []
    
    for col in range(p):
        slice_kr = ct_kr[col::p]
        slice_std = ct_std[col::p]
        n_col = len(slice_kr)
        
        # Quagmire III
        best_chi2_kr = 1e9
        best_s_kr = 0
        for s in range(26):
            p_kr = (slice_kr - s + 26) % 26
            p_std = k_to_std[p_kr]
            counts = np.bincount(p_std, minlength=26)
            expected = n_col * eng_freq
            chi2 = np.sum((counts - expected)**2 / (expected + 0.001))
            if chi2 < best_chi2_kr:
                best_chi2_kr = chi2
                best_s_kr = s
        shifts_kr.append(best_s_kr)
        
        # Standard Vig
        best_chi2_std = 1e9
        best_s_std = 0
        for s in range(26):
            p_std = (slice_std - s + 26) % 26
            counts = np.bincount(p_std, minlength=26)
            expected = n_col * eng_freq
            chi2 = np.sum((counts - expected)**2 / (expected + 0.001))
            if chi2 < best_chi2_std:
                best_chi2_std = chi2
                best_s_std = s
        shifts_std.append(best_s_std)
        
    print(f"Period {p} QIII Shifts:     {shifts_kr}")
    print(f"Period {p} QIII Shifts mod 13: {[s % 13 for s in shifts_kr]}")
    print(f"Period {p} Std Vig Shifts:  {shifts_std}")
    print(f"Period {p} Std Vig Shifts mod 13: {[s % 13 for s in shifts_std]}")
