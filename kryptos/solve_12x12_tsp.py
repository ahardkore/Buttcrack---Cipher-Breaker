import json
import itertools
import numpy as np

# Load bigrams
print("Loading bigrams...")
bigram_logp = np.full((26, 26), -10.0)
with open("candidate_running_keys.txt") as f:
    text = f.read().upper()

from collections import Counter
bg_counts = Counter()
for i in range(len(text) - 1):
    c1, c2 = text[i], text[i+1]
    if 'A' <= c1 <= 'Z' and 'A' <= c2 <= 'Z':
        bg_counts[(ord(c1) - ord('A'), ord(c2) - ord('A'))] += 1

total_bg = sum(bg_counts.values())
for (a, b), cnt in bg_counts.items():
    bigram_logp[a, b] = np.log(cnt / total_bg)

pt = "EPIIEWTFEGTAEETXLOEDMNCRTREAHYSAURZAEAETDSCAUTZVEIBAKAHHREPHSXETONNPDVRGITQIIWEAVTDEDETCWEEZWTCNESFERRNYPIHOJNFROEAGLEASPBHAFEAHZETEQEELOQEZMNTO"
grid = np.array([list(pt[r*12:(r+1)*12]) for r in range(12)])
grid_num = np.array([[ord(c) - ord('A') for c in row] for row in grid])

# Compute 12x12 pairwise transition weights: W[i, j] = sum_{r=0..11} bigram_logp[grid[r, i], grid[r, j]]
W = np.zeros((12, 12))
for i in range(12):
    for j in range(12):
        if i == j:
            W[i, j] = -1e9
        else:
            W[i, j] = sum(bigram_logp[grid_num[r, i], grid_num[r, j]] for r in range(12))

print("Pairwise weight matrix computed.")

# Branch-and-bound TSP solver to find top column permutations
best_paths = []

def dfs(current_path, current_score, visited_mask):
    if len(current_path) == 12:
        best_paths.append((current_score, current_path.copy()))
        return

    last = current_path[-1]
    # Sort remaining neighbors by weight descending
    candidates = []
    for next_node in range(12):
        if not (visited_mask & (1 << next_node)):
            candidates.append((W[last, next_node], next_node))
    candidates.sort(key=lambda x: -x[0])

    # Explore top 4 branches
    for w, next_node in candidates[:4]:
        current_path.append(next_node)
        dfs(current_path, current_score + w, visited_mask | (1 << next_node))
        current_path.pop()

print("Solving column order TSP...")
for start_node in range(12):
    dfs([start_node], 0.0, 1 << start_node)

best_paths.sort(key=lambda x: -x[0])
print(f"Top 5 Column Permutations of 12x12 grid:")
for score, path in best_paths[:5]:
    print(f"\nScore: {score:.2f} | Order: {path}")
    for r in range(12):
        row_str = "".join(grid[r, c] for c in path)
        print(f"  Row {r:2d}: {row_str}")
