import json

with open("pk_all_ciphertexts.json") as f:
    ct10 = json.load(f)["PK10"]

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
N = len(ct10)

s13 = [0, 2, 9, 10, 10, 6, 7]

# Multiples of 8 and 9 up to 72
lags_8_9 = [8, 9, 16, 18, 24, 27, 32, 36, 40, 45, 48, 54, 56, 63, 64, 72]

best_score = -1.0
best_mask = None
best_c89 = None

for mask in range(128):
    q7 = [(s13[j] + 13 * ((mask >> j) & 1)) % 26 for j in range(7)]
    
    # Strip Q7 from PK10
    c_res = [(ALPH.index(c) - q7[i % 7]) % 26 for i, c in enumerate(ct10)]
    
    # Measure average coincidence at multiples of 8 and 9
    total_coinc = 0
    total_pairs = 0
    for lag in lags_8_9:
        matches = sum(1 for i in range(N - lag) if c_res[i] == c_res[i + lag])
        total_coinc += matches
        total_pairs += (N - lag)
        
    rate = total_coinc / total_pairs
    if rate > best_score:
        best_score = rate
        best_mask = mask

print(f"Tested all 128 masks of Q7 against PK10.")
print(f"Best mask: {best_mask} with coincidence rate at 8/9 multiples = {best_score:.5f}")
null_rate = 1.0 / 26
z = (best_score - null_rate) / ((null_rate * (1 - null_rate) / (N * len(lags_8_9)))**0.5)
print(f"Null rate: {null_rate:.5f} | z-score: {z:+.2f}")
