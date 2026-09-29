import json

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
ct9 = cts['PK9']
n = len(ct9)
W, H = 12, 12

def coset_ioc(s, p):
    total = 0.0
    for r in range(p):
        col = s[r::p]
        L = len(col)
        if L < 2: continue
        counts = {c: col.count(c) for c in set(col)}
        total += sum(v * (v - 1) for v in counts.values()) / (L * (L - 1))
    return total / p

# Generate routes: map from (r, c) to index in original text
routes = {}

# 1. Identity (Row by row)
routes['row_by_row'] = list(range(144))

# 2. Transpose (Col by col)
routes['col_by_col'] = [c * H + r for r in range(H) for c in range(W)]

# 3. Boustrophedon horizontal (serpentine rows)
routes['boustro_horiz'] = []
for r in range(H):
    row = [r * W + c for c in range(W)]
    if r % 2 == 1: row.reverse()
    routes['boustro_horiz'].extend(row)

# 4. Boustrophedon vertical (serpentine cols)
b_vert_grid = [[0]*W for _ in range(H)]
idx = 0
for c in range(W):
    rows = list(range(H))
    if c % 2 == 1: rows.reverse()
    for r in rows:
        b_vert_grid[r][c] = idx
        idx += 1
routes['boustro_vert'] = [b_vert_grid[r][c] for r in range(H) for c in range(W)]

# 5. Spiral clockwise inward from top-left
spiral_cw = [[0]*W for _ in range(H)]
top, bot, left, right = 0, H-1, 0, W-1
idx = 0
while top <= bot and left <= right:
    for c in range(left, right+1): spiral_cw[top][c] = idx; idx += 1
    top += 1
    for r in range(top, bot+1): spiral_cw[r][right] = idx; idx += 1
    right -= 1
    if top <= bot:
        for c in range(right, left-1, -1): spiral_cw[bot][c] = idx; idx += 1
        bot -= 1
    if left <= right:
        for r in range(bot, top-1, -1): spiral_cw[r][left] = idx; idx += 1
        left += 1
routes['spiral_cw_in'] = [spiral_cw[r][c] for r in range(H) for c in range(W)]

# 6. Spiral counterclockwise inward from top-left
spiral_ccw = [[0]*W for _ in range(H)]
top, bot, left, right = 0, H-1, 0, W-1
idx = 0
while top <= bot and left <= right:
    for r in range(top, bot+1): spiral_ccw[r][left] = idx; idx += 1
    left += 1
    for c in range(left, right+1): spiral_ccw[bot][c] = idx; idx += 1
    bot -= 1
    if left <= right:
        for r in range(bot, top-1, -1): spiral_ccw[r][right] = idx; idx += 1
        right -= 1
    if top <= bot:
        for c in range(right, left-1, -1): spiral_ccw[top][c] = idx; idx += 1
        top += 1
routes['spiral_ccw_in'] = [spiral_ccw[r][c] for r in range(H) for c in range(W)]

# 7. Diagonal zig-zag (snake diagonals)
diag_grid = [[0]*W for _ in range(H)]
idx = 0
for d in range(W + H - 1):
    points = []
    for r in range(max(0, d - W + 1), min(H, d + 1)):
        c = d - r
        points.append((r, c))
    if d % 2 == 1: points.reverse()
    for r, c in points:
        diag_grid[r][c] = idx
        idx += 1
routes['diag_zigzag'] = [diag_grid[r][c] for r in range(H) for c in range(W)]

# 8. Rail fence (depths 2, 3, 4, 6, 8, 12)
for depth in [2, 3, 4, 6, 8, 12]:
    fence = [[] for _ in range(depth)]
    rail = 0
    dir_down = False
    for i in range(n):
        fence[rail].append(i)
        if rail == 0 or rail == depth - 1: dir_down = not dir_down
        rail += 1 if dir_down else -1
    routes[f'railfence_{depth}'] = [idx for rail_list in fence for idx in rail_list]

print(f"Testing {len(routes)} routes on PK9:")
for name, perm in routes.items():
    # Invert route: un-transposed text M
    # If CT[i] was at perm[i]:
    m1 = ''.join(ct9[perm[i]] for i in range(n))
    # If CT was written into perm:
    inv_perm = [0]*n
    for i, p in enumerate(perm): inv_perm[p] = i
    m2 = ''.join(ct9[inv_perm[i]] for i in range(n))
    
    ioc1_7 = coset_ioc(m1, 7)
    ioc1_28 = coset_ioc(m1, 28)
    ioc2_7 = coset_ioc(m2, 7)
    ioc2_28 = coset_ioc(m2, 28)
    
    max_ioc = max(ioc1_7, ioc1_28, ioc2_7, ioc2_28)
    if max_ioc > 0.060:
        print(f"ROUTE HIT: {name:20s} | max_ioc={max_ioc:.5f} (m1_p7={ioc1_7:.4f}, m1_p28={ioc1_28:.4f}, m2_p7={ioc2_7:.4f}, m2_p28={ioc2_28:.4f})")
