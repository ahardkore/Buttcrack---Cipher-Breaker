from buttcrack.layered import column_alternatives, _fast_quad_table
from buttcrack.scoring import NgramScorer
import itertools

PK9_CT = 'KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD'
order = [1, 11, 4, 3, 7, 6, 0, 2, 8, 10, 9, 5]
shifts = [13, 6, 9, 18, 16, 5, 6, 16, 1, 25, 14, 21, 10, 8, 16, 11, 7, 2, 8, 24, 25, 23, 18, 1, 7, 10, 11, 3]

scorer = NgramScorer()
table = _fast_quad_table(scorer)
alts = column_alternatives(PK9_CT, 'KRYPTOSABCDEFGHIJLMNQUVWXZ', 28, order, shifts, table)

# Let's inspect the effect of changing shifts in columns 1, 3, 7:
# Col 7: try shift 12 (TUTOR)
# Col 3: try shift 15 (HOUSE)
# Col 1: try shift 10 or 2

ALPH = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
k2i = {c: i for i, c in enumerate(ALPH)}

def decode(order, s_list):
    W = 12
    H = 12
    Z = []
    for i, c in enumerate(PK9_CT):
        val = (k2i[c] - s_list[i % 28] + 26) % 26
        Z.append(ord(ALPH[val]) - ord('A'))
    # col_dec
    cols = [[] for _ in range(W)]
    idx = 0
    for c in range(W):
        phys_col = order[c]
        cols[phys_col] = Z[idx : idx + H]
        idx += H
    out = []
    for r in range(H):
        for c in range(W):
            out.append(chr(ord('A') + cols[c][r]))
    return "".join(out)

# Baseline
pt0 = decode(order, shifts)
print("Baseline PT:")
print(pt0)

# Try with tutor / house:
shifts_mod = list(shifts)
shifts_mod[7] = 12 # TUTOR
shifts_mod[3] = 15 # HOUSE
pt1 = decode(order, shifts_mod)
print("\nModified PT (tutor/house):")
print(pt1)

