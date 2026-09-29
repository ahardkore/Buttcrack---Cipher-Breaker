import json

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK10"]

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
q7 = [5, 5, 8, 7, 16, 10, 22]

import math
freq = {
    'E': 12.0, 'T': 9.1, 'A': 8.1, 'O': 7.7, 'I': 7.3, 'N': 7.0, 'S': 6.3,
    'H': 5.9, 'R': 5.9, 'D': 4.3, 'L': 4.0, 'C': 2.7, 'U': 2.9, 'M': 2.6,
    'W': 2.1, 'F': 2.2, 'G': 2.0, 'Y': 2.1, 'P': 1.8, 'B': 1.5, 'V': 1.0,
    'K': 0.8, 'X': 0.2, 'J': 0.15, 'Q': 0.1, 'Z': 0.07
}

best_Cs = []
for s in range(72):
    slice_indices = [s + 72 * m for m in range(7)]
    slice_chars = [ct[idx] for idx in slice_indices]
    best_val = -1
    best_sc = -999.0
    for Cs in range(26):
        cur_sc = 0.0
        for m in range(7):
            c_kr = KRYPTOS.index(slice_chars[m])
            sh = (Cs + q7[(s + 2*m) % 7]) % 26
            p_kr = (c_kr - sh + 26) % 26
            ch = KRYPTOS[p_kr]
            cur_sc += math.log(freq[ch])
        if cur_sc > best_sc:
            best_sc = cur_sc
            best_val = Cs
    best_Cs.append(best_val)

print("Recovered best_Cs (72 values):")
print(best_Cs)

# Now fit best_Cs[s] = (q8[s % 8] + q9[s % 9]) % 26:
# There are 8 variables for q8, 9 variables for q9.
# Fix q8[0] = 0 (gauge freedom).
# Search over 26^7 for q8? 26^7 is 8 billion.
# Or since 72 = 8 * 9, we have 72 equations: q8[s % 8] + q9[s % 9] = best_Cs[s]
# For any fixed q8, each q9[j] is determined by 8 values!
# Can we search over 26^7? In Python, 26^7 is too big. But simulated annealing takes 0.01s!

import random
# Simulated annealing to find q8 and q9
cur_q8 = [0] + [random.randint(0, 25) for _ in range(7)]
cur_q9 = [random.randint(0, 25) for _ in range(9)]

def score_clocks(q8, q9):
    matches = sum(1 for s in range(72) if (q8[s % 8] + q9[s % 9]) % 26 == best_Cs[s])
    return matches

best_matches = score_clocks(cur_q8, cur_q9)
for step in range(50000):
    var = random.randint(0, 15)
    delta = random.choice([-1, 1])
    n_q8 = list(cur_q8)
    n_q9 = list(cur_q9)
    if var < 7:
        n_q8[var + 1] = (n_q8[var + 1] + delta) % 26
    else:
        n_q9[var - 7] = (n_q9[var - 7] + delta) % 26
    m = score_clocks(n_q8, n_q9)
    if m >= best_matches:
        best_matches = m
        cur_q8 = n_q8
        cur_q9 = n_q9

print(f"\nBest matches of (q8, q9) with best_Cs: {best_matches}/72")
print(f"q8: {cur_q8}")
print(f"q9: {cur_q9}")
