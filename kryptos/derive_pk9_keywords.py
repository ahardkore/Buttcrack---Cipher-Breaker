# Derivation of PK9 Keystream Keywords (Q4, Q7)
import math
from collections import Counter

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
STANDARD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

s28 = [25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6]

print("======================================================================")
print("PK9 KEYSTREAM (Q4, Q7) KEYWORD DERIVATION SEARCH")
print("======================================================================")
print("28 Shifts:", s28)

# 1. 2D Matrix Representation (4 rows x 7 cols)
matrix = [s28[r*7 : (r+1)*7] for r in range(4)]
print("\n4x7 Matrix of Shifts:")
for r in range(4):
    print(f"  Row {r}: {matrix[r]}")

# 2. Optimal 2-Clock Decomposition: s[t] ~ (q4[t%4] + q7[t%7]) mod 26
# There are 26^4 x 26^7, but we can fix q4[0] = 0, leaving 26^3 x 26^7 = 26^10.
# Or optimize via least squares / integer programming over Z_26:
print("\n--- Solving for Optimal (q4, q7) Decomposition in Z_26 ---")

# Let q4[0] = 0. Then for each col c in 0..6:
# We want q7[c] to match s[r*7 + c] - q4[(r*7+c)%4].
# Notice (r*7 + c) % 4:
# r=0: c % 4
# r=1: (c + 7) % 4 = (c + 3) % 4
# r=2: (c + 14) % 4 = (c + 2) % 4
# r=3: (c + 21) % 4 = (c + 1) % 4
# For every c, the 4 rows sample ALL FOUR phases of q4!

best_error = 999
best_q4 = None
best_q7 = None

# Grid search all 26^3 = 17,576 states of (q4[1], q4[2], q4[3])
for q4_1 in range(26):
    for q4_2 in range(26):
        for q4_3 in range(26):
            q4 = [0, q4_1, q4_2, q4_3]
            tot_err = 0
            opt_q7 = []
            for c in range(7):
                # For this c, find best q7_c in 0..25
                best_c_err = 999
                best_c_val = 0
                for v in range(26):
                    c_err = 0
                    for r in range(4):
                        t = r * 7 + c
                        pred = (q4[t % 4] + v) % 26
                        diff = abs((s28[t] - pred + 13) % 26 - 13)
                        c_err += diff
                    if c_err < best_c_err:
                        best_c_err = c_err
                        best_c_val = v
                tot_err += best_c_err
                opt_q7.append(best_c_val)
            if tot_err < best_error:
                best_error = tot_err
                best_q4 = list(q4)
                best_q7 = list(opt_q7)

print(f"Optimal Additive Clock Fit: Error = {best_error} / (28 x 13 = 364)")
print(f"  Best Q4: {best_q4}")
print(f"  Best Q7: {best_q7}")

# Check letters in Kryptos and Standard:
q4_kr = "".join(KRYPTOS[x] for x in best_q4)
q7_kr = "".join(KRYPTOS[x] for x in best_q7)
q4_std = "".join(STANDARD[x] for x in best_q4)
q7_std = "".join(STANDARD[x] for x in best_q7)

print(f"  Q4 letters: Kryptos = \"{q4_kr}\", Standard = \"{q4_std}\"")
print(f"  Q7 letters: Kryptos = \"{q7_kr}\", Standard = \"{q7_std}\"")

# 3. Test 7-letter words matching Q7
print("\n--- Scanning 7-letter words matching Q7 under Caesar shifts ---")
words_7 = []
try:
    with open("words_7.txt") as f:
        for line in f:
            w = line.strip().upper()
            if len(w) == 7 and w.isalpha(): words_7.append(w)
except: pass

print(f"Loaded {len(words_7)} 7-letter words.")
q7_matches = []
for w in words_7:
    diff_kr = [(best_q7[i] - KRYPTOS.index(w[i])) % 26 for i in range(7)]
    diff_std = [(best_q7[i] - (ord(w[i]) - ord("A"))) % 26 for i in range(7)]
    if len(set(diff_kr)) == 1:
        q7_matches.append((w, "Kr Caesar", diff_kr[0]))
    if len(set(diff_std)) == 1:
        q7_matches.append((w, "Std Caesar", diff_std[0]))

print(f"Exact 7-letter keyword matches for Q7: {len(q7_matches)}")
if q7_matches:
    for m in q7_matches[:10]: print("  Match:", m)

# 4. Check specific Kryptos / Theophilus anchors:
anchors = ["DEFUNCT", "KRYPTOS", "SANBORN", "SCHEIDT", "ROGERUS", "HELMART", "SESTIER"]
print("\nEvaluating Specific Thematic Anchors against Q7:")
for a in anchors:
    diff_kr = [(best_q7[i] - KRYPTOS.index(a[i])) % 26 for i in range(7)]
    diff_std = [(best_q7[i] - (ord(a[i]) - ord("A"))) % 26 for i in range(7)]
    print(f"  Anchor \"{a:7s}\": Diff_Kr={diff_kr}, Diff_Std={diff_std}")
