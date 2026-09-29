import json, math

quad = {}
total = 0
with open("english_quadgrams.txt") as f:
    for line in f:
        p = line.strip().split()
        if len(p) == 2:
            quad[p[0]] = float(p[1])
            total += float(p[1])
for k in quad:
    quad[k] = math.log10(quad[k] / total)

def get_quad(s):
    return quad.get(s, -9.5)

# Rows of our Kryptos Vigenere candidate
rows = [
    "UFMMSASNNNUE",
    "OSWBEFLTEHID",
    "WKCAIHDGELOH",
    "AHWUTEHYDAIH",
    "KXEIBFVGRRTS",
    "TONBYYANRENT",
    "GIGNMBHEANUG",
    "HROALNBFAYOS",
    "OSANUMMNDNFR",
    "DMUHRRBOPDAF",
    "ERSNVSAAFUHF",
    "TUORIOIHDVHU"
]

# Can we reorder the 12 columns [0..11] to maximize the quadgram score across all 12 rows?
# Let's run a fast simulated annealing over 12! permutations:
import random

def score_perm(perm):
    tot = 0.0
    for r in range(12):
        row_str = "".join(rows[r][perm[c]] for c in range(12))
        for i in range(9):
            tot += get_quad(row_str[i:i+4])
    return tot / (12 * 9)

best_p = list(range(12))
best_sc = score_perm(best_p)

cur_p = list(best_p)
cur_sc = best_sc

for step in range(50000):
    i, j = random.sample(range(12), 2)
    new_p = list(cur_p)
    new_p[i], new_p[j] = new_p[j], new_p[i]
    new_sc = score_perm(new_p)
    if new_sc > cur_sc or random.random() < math.exp((new_sc - cur_sc) / 0.1):
        cur_p = new_p
        cur_sc = new_sc
        if cur_sc > best_sc:
            best_sc = cur_sc
            best_p = list(new_p)

print(f"Best column permutation score: {best_sc:.4f}")
print(f"Permutation: {best_p}")
for r in range(12):
    row_str = "".join(rows[r][best_p[c]] for c in range(12))
    print(f"Row {r:2d}: {row_str}")

# Also test transposing the grid (if columns were rows)
cols = ["".join(rows[r][c] for r in range(12)) for c in range(12)]
def score_col_perm(perm):
    tot = 0.0
    for r in range(12):
        row_str = "".join(cols[r][perm[c]] for c in range(12))
        for i in range(9):
            tot += get_quad(row_str[i:i+4])
    return tot / (12 * 9)

best_cp = list(range(12))
best_csc = score_col_perm(best_cp)
cur_cp = list(best_cp)
cur_csc = best_csc

for step in range(50000):
    i, j = random.sample(range(12), 2)
    new_cp = list(cur_cp)
    new_cp[i], new_cp[j] = new_cp[j], new_cp[i]
    new_sc = score_col_perm(new_cp)
    if new_sc > cur_csc or random.random() < math.exp((new_sc - cur_csc) / 0.1):
        cur_cp = new_cp
        cur_csc = new_sc
        if cur_csc > best_csc:
            best_csc = cur_csc
            best_cp = list(new_cp)

print(f"\nBest transposed column permutation score: {best_csc:.4f}")
print(f"Permutation: {best_cp}")
for r in range(12):
    row_str = "".join(cols[r][best_cp[c]] for c in range(12))
    print(f"Row {r:2d}: {row_str}")
