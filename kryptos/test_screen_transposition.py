import sys
from itertools import permutations
from buttcrack.lang import get_model

model = get_model("english")
K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"
# Screen layout: 
# Row 25: 4 chars
# Row 26: 31 chars
# Row 27: 31 chars
# Row 28: 31 chars
# Total 97 chars.

# What if K4 was placed in a 31-column grid (with 4 rows: row 0 has 4, rows 1..3 have 31, total 97)?
# Or written into columns of height 4 (some height 3)?
# Let's test Column-transposition on the 31 columns!

CRIBS = {}
for i, c in enumerate("EASTNORTHEAST"):
    CRIBS[21 + i] = c
for i, c in enumerate("BERLINCLOCK"):
    CRIBS[63 + i] = c

# Width 31:
# Cols 0..3 have 4 cells (indices: c, c+4, c+35, c+66) or (indices: c, 4+c, 35+c, 66+c)?
# Row 0: pos 0..3 (length 4)
# Row 1: pos 4..34 (length 31)
# Row 2: pos 35..65 (length 31)
# Row 3: pos 66..96 (length 31)

# Notice row 1 has 31 chars (pos 4..34). Pos 21..33 are ALL in row 1!
# Row 2 has 31 chars (pos 35..65). Pos 63..65 are in row 2!
# Row 3 has 31 chars (pos 66..96). Pos 66..73 are in row 3!

print("Row 0 (4): ", K4_CT[0:4])
print("Row 1 (31):", K4_CT[4:35])
print("Row 2 (31):", K4_CT[35:66])
print("Row 3 (31):", K4_CT[66:97])

print("\nPositions of EASTNORTHEAST (21..33):")
print("  All in Row 1: col indices", [p - 4 for p in range(21, 34)])
print("\nPositions of BERLINCLOCK (63..73):")
print("  BER in Row 2: col indices", [p - 35 for p in range(63, 66)])
print("  LINCLOCK in Row 3: col indices", [p - 66 for p in range(66, 74)])

