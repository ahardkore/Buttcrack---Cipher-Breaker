import itertools
from buttcrack.scoring import NgramScorer

scorer = NgramScorer()

G_rows = [
    "UIRERTAHIHIO",
    "TSMRLOCNSDHH",
    "NWOWEMOSALSO",
    "MDTUNRNAUENO",
    "SOIHFSNLIRSN",
    "ASSETIRNFNSW",
    "OCEHMAHADCAE",
    "FTGTDNIONOCE",
    "WFETREEEEPSD",
    "SALRNEEIFDIH",
    "UITAONLOFSSI",
    "EHAHSSDSOOFU"
]

# In G_rows[11]: EHAHSSDSOOFU
# Indices:
# E: 0
# H: 1, 3
# A: 2
# S: 4, 5, 7
# D: 6
# O: 8, 9
# F: 10
# U: 11

# Let's test two candidate phrases for Row 11:
# Candidate 1: S H A D E S O F H O U S
# Candidate 2: H O U S E O F S H A D E (missing one S, has extra E? No, multiset has 1 E, 3 S's)
# So it MUST be SHADES OF HOUS (or SHADOWS...)

s_idxs = [4, 5, 7]
h_idxs = [1, 3]
o_idxs = [8, 9]

best_global = -1e9
best_pt = ""
best_order = None

# For each of the 24 column permutations that spell SHADESOFHOUS:
for s_perm in itertools.permutations(s_idxs):
    for h_perm in itertools.permutations(h_idxs):
        for o_perm in itertools.permutations(o_idxs):
            p_col = [
                s_perm[0], h_perm[0], 2, 6, 0, s_perm[1],
                o_perm[0], 10, h_perm[1], o_perm[1], 11, s_perm[2]
            ]
            
            # Now unscramble the 12 rows with this p_col:
            rows = []
            for r in range(12):
                rows.append(''.join(G_rows[r][p_col[c]] for c in range(12)))
            
            # Let's check the score of all 12 rows individually:
            row_scores = [scorer.average(r) for r in rows]
            avg_row_sc = sum(row_scores) / 12
            
            if avg_row_sc > best_global:
                best_global = avg_row_sc
                best_order = (p_col, rows)

print(f"Best average row score: {best_global:.4f}")
print("Best p_col:", best_order[0])
print("\n12 Rows:")
for r, row in enumerate(best_order[1]):
    print(f"Row {r:2d} (score {scorer.average(row):.2f}): {row}")

