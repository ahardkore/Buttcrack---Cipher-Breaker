import json
import math
import numpy as np

# Load English bigrams
with open("english_bigrams.json") as f:
    bg_dict = json.load(f)["tbl"]

# 12 rows of G
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

# Bigram log probabilities
log_bg = np.full((26, 26), -10.0)
for bg, val in bg_dict.items():
    if len(bg) == 2:
        a = ord(bg[0]) - ord('A')
        b = ord(bg[1]) - ord('A')
        if 0 <= a < 26 and 0 <= b < 26:
            log_bg[a, b] = float(val)

# Transition cost: cost[A, B] = sum over all 12 rows of log_bg[G[r, A], G[r, B]]
cost = np.zeros((W, W))
for a in range(W):
    for b in range(W):
        if a == b:
            cost[a, b] = -1e9
            continue
        s = 0.0
        for r in range(H):
            ca = ord(G_rows[r][a]) - ord('A')
            cb = ord(G_rows[r][b]) - ord('A')
            s += log_bg[ca, cb]
        cost[a, b] = s

print("Cost matrix calculated. Running Held-Karp on 12 columns...")

# Held-Karp DP
# dp[mask, last] = (best_score, best_path)
memo = {}

def solve(mask, last):
    if mask == (1 << W) - 1:
        return 0.0, []
    state = (mask, last)
    if state in memo:
        return memo[state]
    
    best_val = -1e9
    best_path = []
    for nxt in range(W):
        if not (mask & (1 << nxt)):
            val, path = solve(mask | (1 << nxt), nxt)
            total = val + cost[last, nxt]
            if total > best_val:
                best_val = total
                best_path = [nxt] + path
                
    memo[state] = (best_val, best_path)
    return memo[state]

# Find best starting column
global_best_val = -1e9
global_best_perm = []

for start in range(W):
    val, path = solve(1 << start, start)
    if val > global_best_val:
        global_best_val = val
        global_best_perm = [start] + path

print(f"Optimal column permutation: {global_best_perm}")
print(f"Total bigram score across all 12 rows: {global_best_val:.2f} (avg {global_best_val / (11 * 12):.3f} per bigram)")

print("\nResulting rows with optimal Held-Karp permutation:")
for r in range(H):
    row_str = "".join(G_rows[r][global_best_perm[c]] for c in range(W))
    print(f"Row {r:2d}: {row_str}")

