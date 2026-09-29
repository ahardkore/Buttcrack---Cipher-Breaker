import json

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK10"]

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
b = [5, 5, 8, 7, 16, 10, 22]

from collections import Counter
def get_ioc(s, p):
    slices = [s[i::p] for i in range(p)]
    total_pairs = sum(len(sl)*(len(sl)-1) for sl in slices)
    total_coinc = sum(sum(v*(v-1) for v in Counter(sl).values()) for sl in slices)
    return total_coinc / total_pairs if total_pairs > 0 else 0

dims = [(21, 24), (24, 21), (18, 28), (28, 18), (14, 36), (36, 14), (12, 42), (42, 12)]

for W, H in dims:
    # 1. Untransposed row-by-row
    untrans1 = [""] * 504
    for r in range(H):
        for c in range(W):
            untrans1[r * W + c] = ct[c * H + r]
    s1 = "".join(untrans1)
    
    # 2. Untransposed col-by-col
    untrans2 = [""] * 504
    for c in range(W):
        for r in range(H):
            untrans2[c * H + r] = ct[r * W + c]
    s2 = "".join(untrans2)
    
    for label, s in [("row", s1), ("col", s2)]:
        # Check raw IoC across periods 7, 8, 9, 72
        i7 = get_ioc(s, 7)
        i8 = get_ioc(s, 8)
        i9 = get_ioc(s, 9)
        i72 = get_ioc(s, 72)
        if max(i7, i8, i9, i72) > 0.046:
            print(f"Matrix {W}x{H} ({label}): IoC(7)={i7:.4f}, IoC(8)={i8:.4f}, IoC(9)={i9:.4f}, IoC(72)={i72:.4f}")
