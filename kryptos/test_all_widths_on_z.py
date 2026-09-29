import json
import numpy as np

with open("english_bigrams.json") as f:
    data = json.load(f)
bg_dict = data["tbl"]

z_str = "UCBLAAOHWSUAFYNAOCHSHAIZRQFOIEKFFLTCERWLEADRTTFJPLETFSZERXQOOOMPSIAIBAIPAFDUURHKEGXEHXUSMNAAEIOYFYPMIIIUGFFJHFXFRXXTTDSAIHSIPYPSSMEHAHOJNZMFDNTQ"
N = len(z_str)

bigram_log = np.full((26, 26), -7.0)
for k, v in bg_dict.items():
    if len(k) == 2:
        a = ord(k[0]) - ord("A")
        b = ord(k[1]) - ord("A")
        if 0 <= a < 26 and 0 <= b < 26:
            bigram_log[a, b] = float(v)

def solve_width(w):
    h = N // w
    cols = [z_str[j*h : (j+1)*h] for j in range(w)]
    cost = np.zeros((w, w))
    for a in range(w):
        for b in range(w):
            if a == b: continue
            s = 0.0
            for r in range(h):
                ca = ord(cols[a][r]) - ord("A")
                cb = ord(cols[b][r]) - ord("A")
                s += bigram_log[ca, cb]
            cost[a, b] = s
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
    ordered_cols = [cols[c] for c in global_best_perm]
    res_rows = []
    for r in range(h):
        for c in range(w):
            res_rows.append(ordered_cols[c][r])
    return "".join(res_rows), global_best_perm, global_best_val / ((w - 1) * h)

for w in [6, 8, 9, 12, 16]:
    if N % w == 0:
        pt, perm, avg_bg = solve_width(w)
        print(f"Width {w:2d}: Avg Bigram = {avg_bg:.3f} | Perm = {perm}")
        print(f"  PT: {pt[:72]}...")
