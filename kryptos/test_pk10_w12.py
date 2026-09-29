import json

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK10"]

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

W = 12
H = 504 // W # 42

print(f"Testing Width 12 (H={H}) on PK10...")

# Write row-by-row, read col-by-col -> to untranspose: write into columns of height H, read row-by-row
untrans = [""] * 504
for r in range(H):
    for c in range(W):
        untrans[r * W + c] = ct[c * H + r]
untrans_str = "".join(untrans)

from collections import Counter
def get_ioc(s, p):
    slices = [s[i::p] for i in range(p)]
    total_pairs = sum(len(sl)*(len(sl)-1) for sl in slices)
    total_coinc = sum(sum(v*(v-1) for v in Counter(sl).values()) for sl in slices)
    return total_coinc / total_pairs if total_pairs > 0 else 0

print("IoC across periods on untransposed Width 12:")
for p in [7, 8, 9, 12, 14, 21, 24, 28, 42, 56, 63, 72]:
    print(f"Period {p:2d}: IoC = {get_ioc(untrans_str, p):.4f}")
