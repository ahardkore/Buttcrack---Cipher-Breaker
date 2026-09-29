import numpy as np
from sympy import Matrix

periods = (7, 8, 9)
total_offsets = 504 - 22

matrices = np.zeros((total_offsets, 22, 22), dtype=np.uint8)

print(f"Precomputing {total_offsets} inverse matrices...")
for pos in range(total_offsets):
    A = np.zeros((22, 22), dtype=int)
    for row in range(22):
        i = pos + row
        A[row, i % 7] = 1
        if i % 8 < 7:
            A[row, 7 + (i % 8)] = 1
        if i % 9 < 8:
            A[row, 14 + (i % 9)] = 1
    M = Matrix(A.tolist())
    M_inv = M.inv_mod(26)
    for r in range(22):
        for c in range(22):
            matrices[pos, r, c] = int(M_inv[r, c]) % 26

matrices.tofile("a_inv_all.bin")
print("Saved a_inv_all.bin successfully!")
