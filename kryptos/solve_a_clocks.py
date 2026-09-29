KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
perm = [3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10]

b = [5, 5, 8, 7, 16, 10, 22] # Q7 clock
# a0 = 0

# Row 5 pt candidate: "FARTWITCLNIA"
# Let us check what a1 is implied by each character of Row 5:
# ct_kr = KRYPTOS.index(ct)
# pt_kr = KRYPTOS.index(pt)
# shift = (ct_kr - pt_kr) % 26
# a1 = (shift - b[r7]) % 26

pt_row5 = "FARTWITCLNIA"
print("Implied a1 values from Row 5 characters:")
for c in range(12):
    i = perm[c] * 12 + 5
    ct_char = PK9_REAL[i]
    pt_char = pt_row5[c]
    r7 = (5 * perm[c] + 5) % 7
    ct_k = KRYPTOS.index(ct_char)
    pt_k = KRYPTOS.index(pt_char)
    shift = (ct_k - pt_k) % 26
    a1 = (shift - b[r7]) % 26
    print(f"c={c:2d}: pt={pt_char}, ct={ct_char}, r7={r7}, b[r7]={b[r7]:2d}, shift={shift:2d} => a1 = {a1:2d}")
