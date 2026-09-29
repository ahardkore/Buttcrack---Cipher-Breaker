import json

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK10"]

print(f"PK10 Length: {len(ct)}")
print(f"PK10 Ciphertext:\n{ct}")

# Letter frequencies
from collections import Counter
c = Counter(ct)
print("\nLetter counts:")
print(sorted(c.items()))

# Monogram IoC
n = len(ct)
ioc = sum(v*(v-1) for v in c.values()) / (n*(n-1))
print(f"\nMonogram IoC: {ioc:.5f}")

# Factorization of 504
factors = [(w, 504 // w) for w in range(2, 504) if 504 % w == 0]
print(f"\nGrid factor pairs (width x height): {factors}")

# Autocorrelation of PK10 for lags 1 to 100
autocorr = []
for lag in range(1, 101):
    matches = sum(1 for i in range(len(ct) - lag) if ct[i] == ct[i+lag])
    expected = (len(ct) - lag) / 26.0
    ratio = matches / expected if expected > 0 else 0
    autocorr.append((ratio, matches, lag))

autocorr.sort(reverse=True)
print("\nTop 15 Autocorrelation Lags in PK10:")
for ratio, matches, lag in autocorr[:15]:
    print(f"Lag {lag:2d}: matches={matches:2d}, ratio={ratio:.2f}x expected")
