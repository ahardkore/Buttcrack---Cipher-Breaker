KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
perm = [3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10]

# Base shifts from simulated annealing / branch-and-bound
shifts = [5, 4, 9, 15, 16, 5, 6, 14, 5, 25, 20, 21, 10, 6, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3]

# Let us test variations on slices:
# Slice 1: try 2, 4, 15
# Slice 7: try 14, 16, 10, 17
# Slice 13: try 6, 7
# Slice 18: try 10, 3, 7, 8

import math
quad = {}
total = 0
with open("english_quadgrams.txt") as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) == 2:
            quad[parts[0]] = float(parts[1])
            total += float(parts[1])
for k in quad:
    quad[k] = math.log10(quad[k] / total)

def get_text(sh):
    z = []
    for i in range(144):
        c_idx = KRYPTOS.index(PK9_REAL[i])
        p_kr = (c_idx - sh[i % 28] + 26) % 26
        z.append(KRYPTOS[p_kr])
    W, H = 12, 12
    cols = [z[c*H : (c+1)*H] for c in range(W)]
    pt = []
    for r in range(H):
        for c in range(W):
            pt.append(cols[perm[c]][r])
    return "".join(pt)

def score_text(t):
    sc = 0.0
    for i in range(len(t)-3):
        sc += quad.get(t[i:i+4], -9.5)
    return sc / (len(t)-3)

best_sc = -999.0
best_sh = None

for s1 in [2, 4, 15]:
    for s7 in [10, 14, 16, 17]:
        for s13 in [6, 7]:
            for s18 in [3, 7, 8, 10]:
                cur_sh = list(shifts)
                cur_sh[1] = s1
                cur_sh[7] = s7
                cur_sh[13] = s13
                cur_sh[18] = s18
                t = get_text(cur_sh)
                sc = score_text(t)
                if sc > best_sc:
                    best_sc = sc
                    best_sh = list(cur_sh)
                    print(f"New Best: score={sc:.4f} | s1={s1}, s7={s7}, s13={s13}, s18={s18}")

print(f"\nFinal Best Score: {best_sc:.4f}")
print("Shifts:", best_sh)
t_final = get_text(best_sh)
for r in range(12):
    print(f"Row {r:2d}: {t_final[r*12:(r+1)*12]}")
