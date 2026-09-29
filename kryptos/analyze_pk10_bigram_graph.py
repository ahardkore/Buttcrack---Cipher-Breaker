# Exhaustive Bigram-Graph Analysis on PK10 36 Core Columns
import math
from collections import Counter

# Standard English bigram frequencies / log-probabilities
# We can load bigrams from english_quads or build from unigrams/bigrams
with open("pk10_record_6943.txt") as f:
    lines = [l.strip() for l in f if l.startswith("# Row")]

rows = [l.split(":")[1].split("(")[0].strip() for l in lines]
core_rows = [r[2:38] for r in rows] # 12 rows x 36 cols

# Baseline core column IDs in raw PK10:
base_core_cols = [
    34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17,
    23, 25, 26, 16, 20, 37, 39, 7, 31, 33, 32, 36,
    22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6
]

# Extract each of the 36 columns as a 12-char string:
cols = []
for c_idx in range(36):
    col_str = "".join(core_rows[r][c_idx] for r in range(12))
    cols.append(col_str)

print("==========================================================================================")
print("             PK10 36-COLUMN DIRECTED BIGRAM TRANSITION GRAPH AUDIT                        ")
print("==========================================================================================\n")
print(f"Total columns: {len(cols)}, Height: 12 rows per column.")

# Load bigram log-likelihoods:
# We can derive empirical bigram weights from english_quads.tsv
# Summing quadgrams matching (a, b, *, *) or (*, a, b, *)
bigram_counts = {}
with open("english_quads.tsv") as f:
    for line in f:
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 4:
            q = parts[0]
            # add bigrams
            for k in range(3):
                bg = q[k:k+2]
                bigram_counts[bg] = bigram_counts.get(bg, 0.0) + 10.0 ** float(parts[1])

tot_bg = sum(bigram_counts.values())
bg_logp = {}
for bg, cnt in bigram_counts.items():
    bg_logp[bg] = math.log(cnt / tot_bg)

floor_bg = math.log(1e-7 / tot_bg)

def eval_pair(c1, c2):
    sc = 0.0
    for r in range(12):
        bg = c1[r] + c2[r]
        sc += bg_logp.get(bg, floor_bg)
    return sc

# 1. Compute 36x36 directed edge weights
adj = {}
all_edges = []
for i in range(36):
    for j in range(36):
        if i != j:
            w = eval_pair(cols[i], cols[j])
            adj[(i, j)] = w
            all_edges.append((w, i, j))

all_edges.sort(reverse=True)
print(f"Total directed edges computed: {len(all_edges)}")
print(f"Average edge weight: {sum(e[0] for e in all_edges)/len(all_edges):.4f}")
print(f"Max edge weight:     {all_edges[0][0]:.4f} (Col {all_edges[0][1]} -> Col {all_edges[0][2]})")
print(f"Min edge weight:     {all_edges[-1][0]:.4f}\n")

# 2. Check the weights of the 35 consecutive baseline edges (k -> k+1)
print("--- Baseline Column Sequence Edge Weights (k -> k+1) ---")
base_weights = []
for k in range(35):
    w = adj[(k, k+1)]
    base_weights.append(w)
    # Find rank of this edge among all outgoing edges from k
    out_edges = sorted([(adj[(k, j)], j) for j in range(36) if j != k], reverse=True)
    rank = [x[1] for x in out_edges].index(k+1) + 1
    top_dest = out_edges[0][1]
    top_w = out_edges[0][0]
    print(f"  Edge ({k:2d} -> {k+1:2d}) [Cols {base_core_cols[k]:2d} -> {base_core_cols[k+1]:2d}]: Weight = {w:7.2f} (Rank #{rank:2d} / 35 out of Col {k:2d}, Best={top_dest:2d} [{top_w:7.2f}])")

avg_base_w = sum(base_weights) / len(base_weights)
print(f"\nAverage Baseline Transition Weight: {avg_base_w:.2f}")

# How many baseline edges are the #1 or #2 choice for their column?
top1_count = sum(1 for k in range(35) if [x[1] for x in sorted([(adj[(k, j)], j) for j in range(36) if j != k], reverse=True)].index(k+1) == 0)
top3_count = sum(1 for k in range(35) if [x[1] for x in sorted([(adj[(k, j)], j) for j in range(36) if j != k], reverse=True)].index(k+1) < 3)
print(f"Baseline edges that are #1 outgoing choice: {top1_count} / 35 ({top1_count/35*100:.1f}%)")
print(f"Baseline edges in Top 3 outgoing choices:  {top3_count} / 35 ({top3_count/35*100:.1f}%)")

# 3. Top 15 Highest-Affinity Column Pairs Across the Entire Graph:
print("\n--- Top 15 Strongest Bigram Column Connections in PK10 ---")
for rank, (w, i, j) in enumerate(all_edges[:15], 1):
    is_base = (j == i + 1)
    marker = ">>> IN BASELINE <<<" if is_base else ""
    print(f"  #{rank:2d}: Pos {i:2d} (Col {base_core_cols[i]:2d}) -> Pos {j:2d} (Col {base_core_cols[j]:2d}) | Weight = {w:7.2f} {marker}")
