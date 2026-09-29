import numpy as np

# z_str under optimal shifts
KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
k_to_std = {KRYPTOS[i]: chr(65 + i) for i in range(26)}
std_to_k = {chr(65 + i): KRYPTOS[i] for i in range(26)}

shifts = [5, 4, 9, 15, 16, 5, 6, 14, 5, 25, 20, 21, 10, 6, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3]

z = []
for i in range(144):
    c_idx = KRYPTOS.index(PK9_REAL[i])
    p_kr = (c_idx - shifts[i % 28] + 26) % 26
    z.append(k_to_std[KRYPTOS[p_kr]])
z = "".join(z)

W = 12
H = 144 // W
cols = [z[c*H : (c+1)*H] for c in range(W)]

print("The 12 raw columns of Z (each 12 chars):")
for c in range(W):
    print(f"Col {c:2d}: {cols[c]}")

# Print row multi-sets
print("\nRow letter multisets (what letters are available in each row):")
for r in range(H):
    row_chars = sorted(cols[c][r] for c in range(W))
    print(f"Row {r:2d}: {''.join(row_chars)}")
