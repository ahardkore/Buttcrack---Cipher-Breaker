import itertools
from buttcrack.scoring import NgramScorer
scorer = NgramScorer()

G_rows = [
    "UIRERTAHIHIO", # Row 0
    "TSMRLOCNSDHH", # Row 1
    "NWOWEMOSALSO", # Row 2
    "MDTUNRNAUENO", # Row 3
    "SOIHFSNLIRSN", # Row 4
    "ASSETIRNFNSW", # Row 5
    "OCEHMAHADCAE", # Row 6
    "FTGTDNIONOCE", # Row 7
    "WFETREEEEPSD", # Row 8
    "SALRNEEIFDIH", # Row 9
    "UITAONLOFSSI", # Row 10
    "EHAHSSDSOOFU"  # Row 11
]

# We want Row 11 to be "SHADESOFHOUS"
# Available cols for each character:
# S: [4, 5, 7] -> pos 0, 5, 11
# H: [1, 3]    -> pos 1, 8
# A: [2]       -> pos 2
# D: [6]       -> pos 3
# E: [0]       -> pos 4
# O: [8, 9]    -> pos 6, 9
# F: [10]      -> pos 7
# U: [11]      -> pos 10

candidates = []

for s_perm in itertools.permutations([4, 5, 7]):
    for h_perm in itertools.permutations([1, 3]):
        for o_perm in itertools.permutations([8, 9]):
            p_col = [
                s_perm[0], # pos 0: S
                h_perm[0], # pos 1: H
                2,         # pos 2: A
                6,         # pos 3: D
                0,         # pos 4: E
                s_perm[1], # pos 5: S
                o_perm[0], # pos 6: O
                10,        # pos 7: F
                h_perm[1], # pos 8: H
                o_perm[1], # pos 9: O
                11,        # pos 10: U
                s_perm[2]  # pos 11: S
            ]
            
            # Decrypt all 12 rows
            rows = ["".join(G_rows[r][p_col[c]] for c in range(12)) for r in range(12)]
            
            # Compute total quadgram score across all 12 rows
            sc = sum(scorer.score(row) for row in rows) / (12 * 9)
            candidates.append((sc, p_col, rows))

candidates.sort(reverse=True)

print(f"Evaluated all 24 permutations fixing Row 11 to SHADESOFHOUS.\n")
print(f"Top 5 candidates by total within-row quadgram score:")
for rank, (sc, p_col, rows) in enumerate(candidates[:5]):
    print(f"\n--- Rank {rank+1} (Score: {sc:.4f}) | p_col = {p_col} ---")
    for r, row in enumerate(rows):
        print(f"  Row {r:2d}: {row}")

