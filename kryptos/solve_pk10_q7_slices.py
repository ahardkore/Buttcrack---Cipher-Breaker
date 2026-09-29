import json
import math

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK10"]

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
q7 = [5, 5, 8, 7, 16, 10, 22] # from PK9

freq = {
    'E': 12.0, 'T': 9.1, 'A': 8.1, 'O': 7.7, 'I': 7.3, 'N': 7.0, 'S': 6.3,
    'H': 5.9, 'R': 5.9, 'D': 4.3, 'L': 4.0, 'C': 2.7, 'U': 2.9, 'M': 2.6,
    'W': 2.1, 'F': 2.2, 'G': 2.0, 'Y': 2.1, 'P': 1.8, 'B': 1.5, 'V': 1.0,
    'K': 0.8, 'X': 0.2, 'J': 0.15, 'Q': 0.1, 'Z': 0.07
}

# 72 slices of period 72:
# For each slice s in 0..71:
# chars are ct[s + 72 * m] for m in 0..6.
# Key is C_s + q7[(s + 2*m) % 7] (mod 26).
# Let us find optimal C_s for each slice!

best_Cs = []
total_log_lik = 0.0

z = [""] * 504

for s in range(72):
    slice_indices = [s + 72 * m for m in range(7)]
    slice_chars = [ct[idx] for idx in slice_indices]
    
    best_val = -1
    best_sc = -999.0
    best_dec = []
    
    for Cs in range(26):
        cur_sc = 0.0
        cur_dec = []
        for m in range(7):
            c_kr = KRYPTOS.index(slice_chars[m])
            sh = (Cs + q7[(s + 2*m) % 7]) % 26
            p_kr = (c_kr - sh + 26) % 26
            ch = KRYPTOS[p_kr]
            cur_dec.append(ch)
            cur_sc += math.log(freq[ch])
        if cur_sc > best_sc:
            best_sc = cur_sc
            best_val = Cs
            best_dec = list(cur_dec)
            
    best_Cs.append(best_val)
    total_log_lik += best_sc
    for m in range(7):
        z[slice_indices[m]] = best_dec[m]

z_str = "".join(z)
print(f"Total log-likelihood across all 72 slices: {total_log_lik:.1f}")
print(f"Average monogram log-likelihood per char: {total_log_lik / 504.0:.3f}")

# Check IoC of z_str across periods!
from collections import Counter
def get_ioc(s, p):
    slices = [s[i::p] for i in range(p)]
    total_pairs = sum(len(sl)*(len(sl)-1) for sl in slices)
    total_coinc = sum(sum(v*(v-1) for v in Counter(sl).values()) for sl in slices)
    return total_coinc / total_pairs if total_pairs > 0 else 0

print("\nIoC of z_str across periods:")
for p in [1, 2, 3, 4, 6, 7, 8, 9, 12, 14, 18, 21, 24, 28, 36, 42, 56, 63, 72]:
    ioc_val = get_ioc(z_str, p)
    if ioc_val > 0.05:
        print(f"Period {p:2d}: IoC = {ioc_val:.4f}  *** ELEVATED ***")
    else:
        print(f"Period {p:2d}: IoC = {ioc_val:.4f}")
