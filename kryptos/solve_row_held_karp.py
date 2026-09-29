import json
import numpy as np

# Load quadgrams from buttcrack
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

W = 12
H = 12

p_col = [10, 3, 2, 9, 7, 8, 11, 5, 4, 0, 6, 1]

# Ordered rows L_r
lines = ["".join(G_rows[r][p_col[c]] for c in range(W)) for r in range(H)]
for r, line in enumerate(lines):
    print(f"L_{r:2d}: {line}")

# Compute transition cost between placing row A then row B
# Transition quadgrams across the boundary:
# quad 0: L_A[9], L_A[10], L_A[11], L_B[0]
# quad 1: L_A[10], L_A[11], L_B[0], L_B[1]
# quad 2: L_A[11], L_B[0], L_B[1], L_B[2]
cost = np.zeros((H, H))
for a in range(H):
    for b in range(H):
        if a == b:
            cost[a, b] = -1e9
            continue
        boundary = lines[a][9:] + lines[b][:3] # 6 chars
        sc = scorer.score(boundary)
        cost[a, b] = sc

# Held-Karp to find optimal row order
memo = {}
def solve(mask, last):
    if mask == (1 << H) - 1:
        return 0.0, []
    state = (mask, last)
    if state in memo:
        return memo[state]
    
    best_val = -1e9
    best_path = []
    for nxt in range(H):
        if not (mask & (1 << nxt)):
            val, path = solve(mask | (1 << nxt), nxt)
            total = val + cost[last, nxt]
            if total > best_val:
                best_val = total
                best_path = [nxt] + path
                
    memo[state] = (best_val, best_path)
    return memo[state]

global_best_val = -1e9
global_best_perm = []

for start in range(H):
    val, path = solve(1 << start, start)
    if val > global_best_val:
        global_best_val = val
        global_best_perm = [start] + path

print(f"\nOptimal row permutation: {global_best_perm}")

full_pt = "".join(lines[r] for r in global_best_perm)
full_sc = scorer.score(full_pt) / (len(full_pt) - 3)
print(f"Full text quadgram score: {full_sc:.4f}")
print("\nFull Plaintext:")
for r in global_best_perm:
    print(lines[r])

print("\nJoined Plaintext:")
print(full_pt)
