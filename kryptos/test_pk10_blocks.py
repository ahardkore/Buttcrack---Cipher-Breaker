import json
import numpy as np

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK10"]

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
ct_num = [KRYPTOS.index(c) for c in ct]

# Test block sizes: 2, 3, 4, 6, 7, 8, 9
for b in [2, 3, 4, 6, 7, 8, 9]:
    blocks = [ct_num[i:i+b] for i in range(0, len(ct_num), b)]
    # Compute covariance or correlation
    mat = np.array(blocks)
    # Check if any columns are identical or correlated
    col_var = np.var(mat, axis=0)
    print(f"Block size {b:2d}: {len(blocks):3d} blocks, col variances: {[round(v, 1) for v in col_var]}")
