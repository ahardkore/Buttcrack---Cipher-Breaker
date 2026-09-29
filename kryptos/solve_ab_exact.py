KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
perm = [3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10]

# Grid indices:
# For row r, col c:
# i = perm[c] * 12 + r
# r_mod_4 = r % 4
# r_mod_7 = (5 * perm[c] + r) % 7
# shift_i = (a[r_mod_4] + b[r_mod_7]) % 26
# p_kr = (ct_kr[i] - shift_i) % 26
# pt_char = KRYPTOS[p_kr]
# Therefore: shift_i = (ct_kr[i] - p_kr) % 26

# Let us inspect the ciphertext letter at each (r, c)
print("Row 4 ciphertext letters on KRYPTOS:")
for c in range(12):
    i = perm[c] * 12 + 4
    ct_char = PK9_REAL[i]
    print(f"c={c:2d}: ct={ct_char} (r4={4%4}, r7={(5*perm[c]+4)%7})")

print("\nRow 5 ciphertext letters on KRYPTOS:")
for c in range(12):
    i = perm[c] * 12 + 5
    ct_char = PK9_REAL[i]
    print(f"c={c:2d}: ct={ct_char} (r4={5%4}, r7={(5*perm[c]+5)%7})")
