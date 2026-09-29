import math, json
from collections import Counter

with open("pk_all_ciphertexts.json") as f:
    cts = json.load(f)

ct10 = cts["PK10"]
N = len(ct10)
print(f"PK10 Length: {N}")

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
kpos = {c: i for i, c in enumerate(ALPH)}
ct_num = [kpos[c] for c in ct10]

# Check autocorrelation and coincidence at strides 56, 63, 72 on RAW PK10
for stride in [56, 63, 72, 28, 42]:
    diffs = [(ct_num[i + stride] - ct_num[i]) % 26 for i in range(N - stride)]
    # Group diffs by phase modulo gcd
    # For stride 72: depends on phase modulo 7
    # For stride 63: depends on phase modulo 8
    # For stride 56: depends on phase modulo 9
    counts = Counter(diffs)
    total_pairs = len(diffs)
    ioc = sum(c * (c - 1) for c in counts.values()) / (total_pairs * (total_pairs - 1))
    print(f"Stride {stride:2d}: N={total_pairs} | Diff IoC = {ioc:.5f} | Top diffs: {counts.most_common(3)}")
