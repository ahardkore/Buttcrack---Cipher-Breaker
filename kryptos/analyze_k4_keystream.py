ALPH_K = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
shifts_k = [1, 20, 15, 18, 16, 13, 21, 24, 7, 8, 20, 12, 2, 21, 16, 11, 1, 1, 7, 23, 25, 1, 10, 21, 18, 1, 15, 2, 23, 5, 2, 19, 0, 2, 1, 16, 8, 24, 5, 0, 14, 15, 11, 5, 8, 21, 19, 10, 19, 18, 25, 23, 2, 8, 16, 18, 23, 18, 17, 9, 4, 7, 15, 11, 17, 2, 5, 15, 11, 9, 8, 7, 20, 0, 0, 25, 21, 17, 11, 9, 24, 23, 4, 9, 11, 25, 15, 14, 8, 17, 2, 9, 23, 15, 8, 22, 3]

# Check differences between successive shifts:
diffs = [(shifts_k[i] - shifts_k[i-1]) % 26 for i in range(1, len(shifts_k))]
print("Successive differences mod 26 (first 30):", diffs[:30])

# Check second differences:
diffs2 = [(diffs[i] - diffs[i-1]) % 26 for i in range(1, len(diffs))]
print("Second differences mod 26 (first 30):", diffs2[:30])

# Check if shifts_k comes from a linear recurrence / LFSR over GF(2) or Z_26:
# Berlekamp-Massey on Z_26 or Z_2:
def berlekamp_massey_mod_p(s, p):
    n = len(s)
    b = [1]
    c = [1]
    l = 0
    m = 1
    for i in range(n):
        d = s[i]
        for j in range(1, l + 1):
            d = (d + c[j] * s[i - j]) % p
        if d == 0:
            m += 1
        else:
            t = list(c)
            # c = c - d/d_prev * b shifted by m
            # need inverse of d_prev
            # for p=2:
            pass
    return l

# Check for repeating patterns or sub-blocks:
for step in range(1, 35):
    matches = 0
    for i in range(len(shifts_k) - step):
        if shifts_k[i] == shifts_k[i + step]:
            matches += 1
    if matches >= 10:
        print(f"Lag {step:2d}: {matches} matches out of {len(shifts_k) - step} pairs ({matches/(len(shifts_k)-step):.1%})")

