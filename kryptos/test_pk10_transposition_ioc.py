import json

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK10"]

from collections import Counter

def get_ioc(s, p):
    slices = [s[i::p] for i in range(p)]
    total_pairs = sum(len(sl)*(len(sl)-1) for sl in slices)
    total_coinc = sum(sum(v*(v-1) for v in Counter(sl).values()) for sl in slices)
    return total_coinc / total_pairs if total_pairs > 0 else 0

widths = [7, 8, 9, 12, 14, 18, 21, 24, 28, 36, 42]

# If CT was formed by writing PT into a grid of width W, and reading out by columns:
# Then to untranspose (identity permutation):
# write into columns of height H = 504 // W, read row by row!
for W in widths:
    H = 504 // W
    # Identity columnar untranspose
    untrans = [""] * 504
    for r in range(H):
        for c in range(W):
            untrans[r * W + c] = ct[c * H + r]
    untrans_str = "".join(untrans)
    
    # Check IoCs
    ioc7 = get_ioc(untrans_str, 7)
    ioc8 = get_ioc(untrans_str, 8)
    ioc9 = get_ioc(untrans_str, 9)
    ioc72 = get_ioc(untrans_str, 72)
    max_ioc = max(ioc7, ioc8, ioc9, ioc72)
    if max_ioc > 0.042:
        print(f"Width {W:2d} (H={H:2d}): IoC(7)={ioc7:.4f}, IoC(8)={ioc8:.4f}, IoC(9)={ioc9:.4f}, IoC(72)={ioc72:.4f}")
