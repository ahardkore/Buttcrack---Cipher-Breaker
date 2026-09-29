import numpy as np

perm = [4, 6, 34, 19, 29, 13, 11, 8, 35, 21, 2, 40, 37, 18, 38, 0, 26, 30, 14, 16, 9, 10, 24, 3, 32, 41, 22, 39, 20, 1, 15, 7, 28, 5, 33, 31, 25, 17, 36, 12, 27, 23]
W = 42

# Positions in row 4:
# "ALFAFRRQAKPICKLAPEXULTESVXGYQPPPDONHAWZDMO"
# Index of 'PICK': 10..13 -> perm[10..13] = [2, 40, 37, 18]
# Index of 'EXULT': 17..21 -> perm[17..21] = [30, 14, 16, 9, 10]

# Positions in row 9:
# "FTOKOHEHNSIMSHYLSZBRJBLURRYQZSKVEWEONMYTXUJ"
# Index of 'BLURRY': 21..26 -> perm[21..26] = [10, 24, 3, 32, 41, 22]

# Positions in row 1:
# "ALICDUBPQHHNQQZNGCHOPLWEPMBXNEIFMRSBUTPADS"
# Index of 'CHOP': 17..20 -> perm[17..20] = [30, 14, 16, 9]

print("Columns forming PICK in row 4:", perm[10:14])
print("Columns forming CHOP/EXULT in rows 1/4:", perm[17:22])
print("Columns forming BLURRY in row 9:", perm[21:27])

pinned_cols = set(perm[10:14] + perm[17:22] + perm[21:27])
print(f"Total pinned columns: {len(pinned_cols)} -> {sorted(list(pinned_cols))}")
