import numpy as np
import json

text = "FTNKGOBHKVBVMDWNPRAUTJOSRMOTSSEUMIACHLDSLIHGYVOONKREFTMDMNOHEPUPCOQTHINIOTPDEDTAEELDONSIXLDAHOMLMDATGABDPUYWHDLEMNCGDBCAMTNTCDAMTDTPWWUWNWEERHIP"
N = len(text)

# Load bigrams
with open("english_bigrams.json") as f:
    bg_dict = json.load(f)

# Convert to log matrix
bigram_log = np.full((26, 26), -9.0)
for k, v in bg_dict.items():
    if len(k) == 2:
        a = ord(k[0]) - ord('A')
        b = ord(k[1]) - ord('A')
        if 0 <= a < 26 and 0 <= b < 26:
            bigram_log[a, b] = float(v)

def solve_width(w):
    h = N // w
    # Column j has characters text[j*h : (j+1)*h]
    cols = [text[j*h : (j+1)*h] for j in range(w)]
    
    # Cost of placing col_a before col_b: sum of log bigrams across all rows
    cost = np.zeros((w, w))
    for a in range(w):
        for b in range(w):
            if a == b: continue
            s = 0.0
            for r in range(h):
                ca = ord(cols[a][r]) - ord('A')
                cb = ord(cols[b][r]) - ord('A')
                s += bigram_log[ca, cb]
            cost[a, b] = s
            
    # Held-Karp TSP: find permutation that maximizes sum of bigrams
    # dp[mask][last_col] = max_score
    memo = {}
    
    def get_best(mask, last):
        if mask == (1 << w) - 1:
            return 0.0, []
        state = (mask, last)
        if state in memo:
            return memo[state]
        
        best_val = -1e9
        best_path = []
        for nxt in range(w):
            if not (mask & (1 << nxt)):
                val, path = get_best(mask | (1 << nxt), nxt)
                total = val + cost[last, nxt]
                if total > best_val:
                    best_val = total
                    best_path = [nxt] + path
                    
        memo[state] = (best_val, best_path)
        return memo[state]
        
    global_best_val = -1e9
    global_best_perm = []
    for start in range(w):
        val, path = get_best(1 << start, start)
        if val > global_best_val:
            global_best_val = val
            global_best_perm = [start] + path
            
    # Reconstruct text
    ordered_cols = [cols[c] for c in global_best_perm]
    res_rows = []
    for r in range(h):
        for c in range(w):
            res_rows.append(ordered_cols[c][r])
    res_text = "".join(res_rows)
    return global_best_val / ((w - 1) * h), global_best_perm, res_text

for w in [6, 8, 9, 12, 16]:
    if N % w == 0:
        avg_bg, perm, pt = solve_width(w)
        print(f"Width {w:2d} (rows {N//w:2d}): Avg Bigram = {avg_bg:.3f} | Perm = {perm}")
        print(f"  Sample: {pt[:72]}...")
