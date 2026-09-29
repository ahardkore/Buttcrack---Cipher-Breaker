KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

# The 12 ciphertext letters of Row 6:
ct = ["Y", "E", "S", "Q", "M", "R", "Z", "L", "M", "G", "M", "U"]
# The shift indices for the 12 columns:
# Pair 0: col 0, 11 (s_idx=14)
# Pair 1: col 1, 9  (s_idx=6)
# Col 2:  col 2     (s_idx=22)
# Pair 3: col 3, 8  (s_idx=2)
# Pair 4: col 4, 6  (s_idx=26)
# Col 5:  col 5     (s_idx=10)
# Pair 6: col 7, 10 (s_idx=18)

# Load english quadgrams
import math
quad = {}
total = 0
with open("english_quadgrams.txt") as f:
    for line in f:
        p = line.strip().split()
        if len(p) == 2:
            quad[p[0]] = float(p[1])
            total += float(p[1])
for k in quad:
    quad[k] = math.log10(quad[k] / total)

# Our current shifts:
# s14 = 14
# s6  = 6
# s22 = 22
# s2  = 9
# s26 = 7
# s10 = 20
# s18 = 10

# Let us test all 26^7 combinations? 26^7 is 8 billion, too large for pure python.
# But s_idx are shared across the other rows!
# What shifts are already determined by Rows 4, 5, 7, 8, 9, 10, 11?
# In Row 4: s14 does not appear. s6 does not appear.
# Let us check how many other rows use each of these 7 shifts:
perm = [3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10]
shifts = [5, 4, 9, 15, 16, 5, 6, 10, 5, 25, 20, 21, 10, 6, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3]

def get_row(r, sh):
    row = []
    for c in range(12):
        i = perm[c] * 12 + r
        s = sh[i % 28]
        c_kr = KRYPTOS.index(PK9_REAL[i])
        p_kr = (c_kr - s + 26) % 26
        row.append(KRYPTOS[p_kr])
    return "".join(row)

# Let us check the quadgram score of Row 6 under small variations around the current shifts:
best_sc = -999.0
best_text = ""
best_vals = None

PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"

# Test delta in [-2, 2] for each of the 7 shifts
for d14 in range(-2, 3):
    for d6 in range(-2, 3):
        for d22 in range(-2, 3):
            for d2 in range(-2, 3):
                for d26 in range(-2, 3):
                    for d10 in range(-2, 3):
                        for d18 in range(-2, 3):
                            sh = list(shifts)
                            sh[14] = (sh[14] + d14) % 26
                            sh[6]  = (sh[6]  + d6) % 26
                            sh[22] = (sh[22] + d22) % 26
                            sh[2]  = (sh[2]  + d2) % 26
                            sh[26] = (sh[26] + d26) % 26
                            sh[10] = (sh[10] + d10) % 26
                            sh[18] = (sh[18] + d18) % 26
                            r6 = get_row(6, sh)
                            # Score Row 5 + Row 6 + Row 7 together!
                            r5 = get_row(5, sh)
                            r7 = get_row(7, sh)
                            t = r5 + r6 + r7
                            sc = sum(quad.get(t[i:i+4], -9.5) for i in range(len(t)-3)) / (len(t)-3)
                            if sc > best_sc:
                                best_sc = sc
                                best_text = r6
                                best_vals = (d14, d6, d22, d2, d26, d10, d18)

print(f"Best score: {best_sc:.4f}")
print(f"Best deltas: {best_vals}")
print(f"Row 6 text: {best_text}")
