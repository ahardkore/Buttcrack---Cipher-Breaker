import json

with open("pk_all_ciphertexts.json") as f:
    ct10 = json.load(f)["PK10"]

ct_nums = [ord(c) - 65 for c in ct10]
N = 504

def ioc(nums):
    counts = {}
    for c in nums: counts[c] = counts.get(c, 0) + 1
    n = len(nums)
    if n <= 1: return 0.0
    return sum(v * (v - 1) for v in counts.values()) / (n * (n - 1))

def period_ioc(nums, p):
    slices = [nums[i::p] for i in range(p)]
    return sum(ioc(s) for s in slices if len(s) > 1) / p

factors = [
    (7, 72), (8, 63), (9, 56), (12, 42), (14, 36), (18, 28), (21, 24),
    (24, 21), (28, 18), (36, 14), (42, 12), (56, 9), (63, 8), (72, 7)
]

print("Testing route transpositions on PK10 across all factorizations...")

for H, W in factors:
    # 1. Boustrophedon rows: even rows L->R, odd rows R->L
    grid_boust_row = []
    idx = 0
    for r in range(H):
        row = ct_nums[r*W:(r+1)*W]
        if r % 2 == 1:
            row = row[::-1]
        grid_boust_row.append(row)
    
    # Read col-by-col
    text_boust_col = []
    for c in range(W):
        for r in range(H):
            text_boust_col.append(grid_boust_row[r][c])
            
    for p in [7, 8, 9, 56, 63, 72]:
        val = period_ioc(text_boust_col, p)
        if val > 0.052:
            print(f"Boust Row->Col {H}x{W}: IoC={val:.4f} at period {p}")

    # 2. Boustrophedon cols: even cols T->B, odd cols B->T
    grid_boust_col = [[0]*W for _ in range(H)]
    idx = 0
    for c in range(W):
        col = ct_nums[c*H:(c+1)*H]
        if c % 2 == 1:
            col = col[::-1]
        for r in range(H):
            grid_boust_col[r][c] = col[r]
            
    # Read row-by-row
    text_boust_row = []
    for r in range(H):
        for c in range(W):
            text_boust_row.append(grid_boust_col[r][c])
            
    for p in [7, 8, 9, 56, 63, 72]:
        val = period_ioc(text_boust_row, p)
        if val > 0.052:
            print(f"Boust Col->Row {H}x{W}: IoC={val:.4f} at period {p}")

    # 3. Diagonal readout (top-left to bottom-right diagonals)
    diags = {}
    for r in range(H):
        for c in range(W):
            d = r + c
            if d not in diags: diags[d] = []
            diags[d].append(ct_nums[r*W + c])
    text_diag = []
    for d in sorted(diags):
        text_diag.extend(diags[d])
    for p in [7, 8, 9, 56, 63, 72]:
        val = period_ioc(text_diag, p)
        if val > 0.052:
            print(f"Diagonal {H}x{W}: IoC={val:.4f} at period {p}")

print("Route sweep complete.")
