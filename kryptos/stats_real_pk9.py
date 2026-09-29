import json
from collections import Counter

with open("pk_all_ciphertexts.json") as f:
    ct9 = json.load(f)["PK9"]

def ioc(s):
    n = len(s)
    if n <= 1: return 0.0
    cnt = Counter(s)
    return sum(v * (v - 1) for v in cnt.values()) / (n * (n - 1))

print(f"REAL PK9 Length: {len(ct9)}")
print(f"Whole text unigram IoC: {ioc(ct9):.5f}")

print("\n--- Slice IoC by period (1..36) ---")
for p in range(1, 37):
    slices = [ct9[i::p] for i in range(p)]
    mean_ioc = sum(ioc(sl) for sl in slices) / p
    if mean_ioc > 0.045 or p in [4, 6, 7, 8, 9, 12, 14, 16, 18, 24, 28]:
        print(f"Period {p:2d}: IoC = {mean_ioc:.5f}")

print("\n--- Coincidences by lag (1..36) ---")
for lag in range(1, 37):
    matches = sum(1 for i in range(len(ct9) - lag) if ct9[i] == ct9[i+lag])
    prob = matches / (len(ct9) - lag)
    if matches >= 7 or prob > 0.055:
        print(f"Lag {lag:2d}: {matches:2d} matches / {len(ct9)-lag:3d} (Pr = {prob:.5f})")
