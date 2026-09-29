import numpy as np

PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
k2i = {c: i for i, c in enumerate(ALPH)}
q7 = [0, 2, 9, 23, 23, 6, 20]
C = [k2i[c] for c in PK9_CT]

# Load quadgrams
quads = {}
total_q = 5348433.0
with open("english_quadgrams.txt") as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) == 2:
            quads[parts[0]] = np.log10(float(parts[1]) / total_q)
floor_val = -8.728227

def score_text(txt):
    sc = 0.0
    for i in range(len(txt) - 3):
        g = txt[i:i+4]
        sc += quads.get(g, floor_val)
    return sc / (len(txt) - 3)

# Test all 16 parities
best_global_score = -10.0
best_info = ""

factors = [(12, 12), (9, 16), (16, 9), (8, 18), (18, 8), (6, 24), (24, 6)]

for parity in range(16):
    q4_bits = [((parity >> b) & 1) * 13 for b in range(4)]
    Z = []
    for i in range(144):
        shift = (q7[i % 7] + q4_bits[i % 4]) % 26
        z_kr = (C[i] - shift) % 26
        Z.append(ALPH[z_kr])
    Z = np.array(Z)

    for R, C_cols in factors:
        grid = Z.reshape(R, C_cols)

        # 1. Read by columns (down)
        txt = "".join(grid.T.flatten())
        sc = score_text(txt)
        if sc > best_global_score:
            best_global_score = sc
            best_info = f"Parity {parity}, {R}x{C_cols} Col-down: {txt[:40]}... (score: {sc:.4f})"

        # 2. Read by columns (up)
        txt = "".join(grid[::-1, :].T.flatten())
        sc = score_text(txt)
        if sc > best_global_score:
            best_global_score = sc
            best_info = f"Parity {parity}, {R}x{C_cols} Col-up: {txt[:40]}... (score: {sc:.4f})"

        # 3. Read alternating columns (snake down-up)
        grid_snake = grid.copy()
        for col in range(1, C_cols, 2):
            grid_snake[:, col] = grid_snake[::-1, col]
        txt = "".join(grid_snake.T.flatten())
        sc = score_text(txt)
        if sc > best_global_score:
            best_global_score = sc
            best_info = f"Parity {parity}, {R}x{C_cols} Col-snake: {txt[:40]}... (score: {sc:.4f})"

        # 4. Alternating rows (boustrophedon)
        grid_bous = grid.copy()
        for r in range(1, R, 2):
            grid_bous[r, :] = grid_bous[r, ::-1]
        txt = "".join(grid_bous.flatten())
        sc = score_text(txt)
        if sc > best_global_score:
            best_global_score = sc
            best_info = f"Parity {parity}, {R}x{C_cols} Row-snake: {txt[:40]}... (score: {sc:.4f})"

        # 5. Diagonals
        diags = []
        for d in range(R + C_cols - 1):
            for r in range(max(0, d - C_cols + 1), min(R, d + 1)):
                c = d - r
                diags.append(grid[r, c])
        txt = "".join(diags)
        sc = score_text(txt)
        if sc > best_global_score:
            best_global_score = sc
            best_info = f"Parity {parity}, {R}x{C_cols} Diag-down: {txt[:40]}... (score: {sc:.4f})"

print("Best simple route score:")
print(best_info)
