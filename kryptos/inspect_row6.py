KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
perm = [3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10]

print("Row 6 ciphertext letters and shift indices:")
for c in range(12):
    i = perm[c] * 12 + 6
    s_idx = i % 28
    ct_char = PK9_REAL[i]
    print(f"Col {c:2d}: s_idx={s_idx:2d}, ct={ct_char}")
