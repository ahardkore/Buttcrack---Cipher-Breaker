import json
import numpy as np
from collections import Counter

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)

ct10 = cts['PK10']
N = len(ct10)

def slice_ioc(s, p):
    slices = [s[i::p] for i in range(p)]
    iocs = []
    for sl in slices:
        m = len(sl)
        if m <= 1: continue
        c = Counter(sl)
        iocs.append(sum(v * (v - 1) for v in c.values()) / (m * (m - 1)))
    return sum(iocs) / len(iocs) if iocs else 0.0

def spiral_cw(matrix):
    res = []
    mat = [list(row) for row in matrix]
    while mat:
        res.extend(mat.pop(0))
        if mat and mat[0]:
            for row in mat: res.append(row.pop())
        if mat:
            res.extend(mat.pop()[::-1])
        if mat and mat[0]:
            for row in mat[::-1]: res.append(row.pop(0))
    return "".join(res)

for R, C in [(21, 24), (24, 21), (14, 36), (36, 14), (18, 28), (28, 18), (12, 42), (42, 12)]:
    grid = np.array(list(ct10)).reshape((R, C))
    routes = {}

    # 1. Standard rows
    routes['row_lr'] = "".join(grid.flatten())
    routes['row_rl'] = "".join(np.fliplr(grid).flatten())

    # 2. Boustrophedon rows
    boust_r = []
    for r in range(R):
        row = grid[r] if r % 2 == 0 else grid[r][::-1]
        boust_r.extend(row)
    routes['boust_rows'] = "".join(boust_r)

    # 3. Standard cols
    routes['col_tb'] = "".join(grid.T.flatten())
    routes['col_bt'] = "".join(np.flipud(grid.T).flatten())

    # 4. Boustrophedon cols
    boust_c = []
    for c in range(C):
        col = grid[:, c] if c % 2 == 0 else grid[:, c][::-1]
        boust_c.extend(col)
    routes['boust_cols'] = "".join(boust_c)

    # 5. Spiral CW
    routes['spiral_cw'] = spiral_cw(grid)

    for name, s in routes.items():
        for p in [7, 8, 9]:
            val = slice_ioc(s, p)
            if val > 0.046:
                print(f"Spike! Grid ({R}x{C}) Route {name:12s}: IoC({p}) = {val:.5f}")
