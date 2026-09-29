# Letter multisets of each of the 12 rows from PK9 grid under optimal shifts
KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
perm = [3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10]
shifts = [5, 4, 9, 15, 16, 5, 6, 10, 5, 25, 20, 21, 10, 6, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3]

z = []
for i in range(144):
    c_idx = KRYPTOS.index(PK9_REAL[i])
    p_kr = (c_idx - shifts[i % 28] + 26) % 26
    z.append(KRYPTOS[p_kr])
z = "".join(z)

W, H = 12, 12
cols = [z[c*H : (c+1)*H] for c in range(W)]

for r in range(H):
    row_chars = "".join(cols[perm[c]][r] for c in range(W))
    sorted_chars = "".join(sorted(row_chars))
    print(f"Row {r:2d}: {row_chars}  | available: {sorted_chars}")
