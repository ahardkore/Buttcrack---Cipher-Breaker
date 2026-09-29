import numpy as np, sys
sys.path.insert(0, 'buttcrack/src')
from buttcrack.additive_crib import _periods, _row, _alphabet

pk8 = 'COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY'
ps = [4, 5, 6, 7]
alpha = _alphabet('KRYPTOS')
index = {c: i for i, c in enumerate(alpha)}
ct_kr = np.array([index[c] for c in pk8], dtype=int)

N = 153
WIN = 18
num_windows = N - WIN + 1

M = np.array([_row(t, ps) for t in range(N)], dtype=int)

W_all = np.zeros((num_windows, N, WIN), dtype=np.int32)
D_all = np.zeros((num_windows, N), dtype=np.int32)
valid_win = np.zeros(num_windows, dtype=np.int32)

print(f"Precomputing unimodular weights for all {num_windows} windows...")

for w in range(num_windows):
    Aw = M[w : w + WIN]
    if np.linalg.matrix_rank(Aw) == WIN:
        valid_win[w] = 1
        W = np.linalg.lstsq(Aw.T, M.T, rcond=None)[0].T
        W_int = np.round(W).astype(np.int32)
        W_all[w] = W_int
        # D = (C - W @ C[w:w+18]) mod 26
        D = (ct_kr - (W_int @ ct_kr[w : w + WIN])) % 26
        D_all[w] = D

print(f"Precomputation complete. Valid windows: {np.sum(valid_win)} / {num_windows}")

with open("pk8_weights_all.bin", "wb") as f:
    W_all.tofile(f)
    D_all.tofile(f)
    valid_win.tofile(f)

print("Saved to pk8_weights_all.bin!")
