import sympy as sp
import numpy as np

periods = [7, 8, 9]
n_vars = sum(periods) # 24
cols_to_keep = [c for c in range(24) if c not in [0, 7]] # 22 variables

# We will precompute M_inv mod 26 for start positions 0..482
# M_red is 22x22.
# In SymPy:
# M_inv = M_red.inv_mod(26)

inv_matrices = []
print("Computing inverse matrices for start positions 0..482...")

for start in range(504 - 22 + 1):
    M = []
    for i in range(start, start + 22):
        row = [0] * n_vars
        row[i % 7] = 1
        row[7 + (i % 8)] = 1
        row[7 + 8 + (i % 9)] = 1
        M.append(row)
    M_red = sp.Matrix(M)[:, cols_to_keep]
    # det is +/- 1, so M_red is always invertible mod 26!
    M_inv = M_red.inv_mod(26)
    inv_matrices.append(np.array(M_inv, dtype=np.int8))

# Save as binary or C header
# 483 * 22 * 22 bytes = 233,772 bytes (233 KB)
all_inv = np.stack(inv_matrices, axis=0) # shape (483, 22, 22)
all_inv.tofile("pk10_inv_matrices.bin")
print(f"Saved {all_inv.shape} inverse matrices to pk10_inv_matrices.bin ({all_inv.nbytes} bytes).")
