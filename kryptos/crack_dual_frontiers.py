# Dual-Frontier Cracking Engine: PK9 Locus Analysis & PK10 Consonant Stitching
import math
from collections import Counter

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
STANDARD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# ======================================================================
# PART 1: PK9 THREE-LOCUS DEEP DIVE & DUAL-PHASE ANALYSIS
# ======================================================================
print("==========================================================================================")
print("             PART 1: PK9 THREE-LOCUS EXACT LETTER SUBSTITUTION & TRANSFORMATION            ")
print("==========================================================================================\n")

PK9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
p2 = [7, 0, 5, 2, 4, 3, 6, 1]
p1 = [15, 1, 3, 7, 6, 0, 17, 9, 13, 12, 5, 4, 2, 10, 11, 14, 16, 8]
p2_inv = {p2[i]: i for i in range(8)}
s28 = [25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6]

# Locus 1: What positions share Phase 17?
phase17_positions = [t for t in range(144) if t % 28 == 17]
print("Positions sharing Phase 17 (t % 28 == 17):", phase17_positions)

for t in phase17_positions:
    # Find which (r, c) this t corresponds to:
    # t = p2_inv[r] * 18 + col_mid
    row_grid = -1
    col_mid = t % 18
    p2_row = t // 18
    r = p2[p2_row]
    c = p1.index(col_mid)
    
    ct_char = PK9_RAW[t]
    ct_idx = KRYPTOS.index(ct_char)
    # Current PT with shift 23:
    pt_cur = KRYPTOS[(ct_idx - 23 + 26) % 26]
    # PT with shift 6 (to make 'Q' -> 'E'):
    pt_e = KRYPTOS[(ct_idx - 6 + 26) % 26]
    print(f"  t={t:3d} (Row {r}, Col {c:2d}, p1={col_mid:2d}): CT='{ct_char}' -> Current(s=23): '{pt_cur}', With s=6: '{pt_e}'")

# Locus 2 & 3: Positions sharing Phase 0:
phase0_positions = [t for t in range(144) if t % 28 == 0]
print("\nPositions sharing Phase 0 (t % 28 == 0):", phase0_positions)
for t in phase0_positions:
    p2_row = t // 18
    r = p2[p2_row]
    col_mid = t % 18
    c = p1.index(col_mid)
    ct_char = PK9_RAW[t]
    ct_idx = KRYPTOS.index(ct_char)
    pt_cur = KRYPTOS[(ct_idx - 25 + 26) % 26]
    print(f"  t={t:3d} (Row {r}, Col {c:2d}, p1={col_mid:2d}): CT='{ct_char}' -> Current(s=25): '{pt_cur}'")

# ======================================================================
# PART 2: PK10 CONSONANT STITCHING VIA BIGRAM TRANSITION MATCHING
# ======================================================================
print("\n==========================================================================================")
print("             PART 2: PK10 RESIDUAL CONSONANT STITCHING VIA BIGRAM TRANSITIONS             ")
print("==========================================================================================\n")

with open("pk10_record_6943.txt") as f:
    lines = [l.strip() for l in f if l.startswith("# Row")]

rows = [l.split(":")[1].split("(")[0].strip() for l in lines]
core_rows = [r[2:38] for r in rows]

# Inspect the 14 defect columns (Columns 18 to 31 in core):
# Col IDs: [39, 7, 31, 33, 32, 36, 22, 35, 27, 10, 9, 41, 8, 19]
defect_cols_core = [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]

print("Defect Zone in Core Grid (Cols 18..31, 14 columns):")
for r in range(12):
    zone_str = "".join(core_rows[r][c] for c in defect_cols_core)
    print(f"  Row {r:2d}: {zone_str}")

# Check which column swaps in the defect zone form common English words
# Across all rows simultaneously:
print("\nChecking pairwise column swaps in the defect zone for total English word gain:")
word_set = set()
with open("all_words.txt") as f:
    for line in f:
        w = line.strip().upper()
        if len(w) >= 3 and w.isalpha(): word_set.add(w)

def count_row_words(text):
    count = 0
    chars = set()
    for L in range(3, 9):
        for i in range(len(text) - L + 1):
            if text[i : i + L] in word_set:
                count += 1
                for k in range(i, i + L): chars.add(k)
    return count, len(chars)

base_total_words = 0
base_total_chars = 0
for r in range(12):
    cnt, nch = count_row_words(core_rows[r])
    base_total_words += cnt
    base_total_chars += nch

print(f"Baseline Word Occurrences in Core: {base_total_words} words, {base_total_chars} / 432 characters covered.")
