import json
from collections import Counter

with open("pk_all_ciphertexts.json") as f:
    cts = json.load(f)

ct10 = cts["PK10"]
N = len(ct10)

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
kpos = {c: i for i, c in enumerate(ALPH)}
ct_num = [kpos[c] for c in ct10]

print("=== Phase-Stratified Difference IoC on RAW PK10 ===")

# Stride 72: partition by t % 7
print("\nStride 72 (Clock 7 survives, Clocks 8 & 9 cancel):")
for r in range(7):
    diffs = [(ct_num[t + 72] - ct_num[t]) % 26 for t in range(r, N - 72, 7)]
    counts = Counter(diffs)
    total_pairs = len(diffs)
    ioc = sum(c * (c - 1) for c in counts.values()) / (total_pairs * (total_pairs - 1)) if total_pairs > 1 else 0
    print(f"  Phase {r} (N={total_pairs:2d}): IoC = {ioc:.5f} | Top: {counts.most_common(2)}")

# Stride 63: partition by t % 8
print("\nStride 63 (Clock 8 survives, Clocks 7 & 9 cancel):")
for r in range(8):
    diffs = [(ct_num[t + 63] - ct_num[t]) % 26 for t in range(r, N - 63, 8)]
    counts = Counter(diffs)
    total_pairs = len(diffs)
    ioc = sum(c * (c - 1) for c in counts.values()) / (total_pairs * (total_pairs - 1)) if total_pairs > 1 else 0
    print(f"  Phase {r} (N={total_pairs:2d}): IoC = {ioc:.5f} | Top: {counts.most_common(2)}")

# Stride 56: partition by t % 9
print("\nStride 56 (Clock 9 survives, Clocks 7 & 8 cancel):")
for r in range(9):
    diffs = [(ct_num[t + 56] - ct_num[t]) % 26 for t in range(r, N - 56, 9)]
    counts = Counter(diffs)
    total_pairs = len(diffs)
    ioc = sum(c * (c - 1) for c in counts.values()) / (total_pairs * (total_pairs - 1)) if total_pairs > 1 else 0
    print(f"  Phase {r} (N={total_pairs:2d}): IoC = {ioc:.5f} | Top: {counts.most_common(2)}")
