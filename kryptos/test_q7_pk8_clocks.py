import json

with open("pk_all_ciphertexts.json") as f:
    ct8 = json.load(f)["PK8"]

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
N = len(ct8)

s13 = [0, 2, 9, 10, 10, 6, 7]

lags_4_5_6 = [4, 5, 6, 8, 10, 12, 15, 16, 20, 24, 25, 30]

best_score = -1.0
best_mask = None

for mask in range(128):
    q7 = [(s13[j] + 13 * ((mask >> j) & 1)) % 26 for j in range(7)]
    
    c_res = [(ALPH.index(c) - q7[i % 7]) % 26 for i, c in enumerate(ct8)]
    
    total_coinc = 0
    total_pairs = 0
    for lag in lags_4_5_6:
        matches = sum(1 for i in range(N - lag) if c_res[i] == c_res[i + lag])
        total_coinc += matches
        total_pairs += (N - lag)
        
    rate = total_coinc / total_pairs
    if rate > best_score:
        best_score = rate
        best_mask = mask

print(f"Tested all 128 masks of Q7 against PK8.")
print(f"Best mask: {best_mask} with coincidence rate at 4/5/6 multiples = {best_score:.5f}")
null_rate = 1.0 / 26
z = (best_score - null_rate) / ((null_rate * (1 - null_rate) / (N * len(lags_4_5_6)))**0.5)
print(f"Null rate: {null_rate:.5f} | z-score: {z:+.2f}")
