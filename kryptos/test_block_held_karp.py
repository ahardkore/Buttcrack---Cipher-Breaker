import json, math, time
from collections import Counter
from buttcrack.ciphers.columnar import _decode_units
from buttcrack.scoring import get_scorer

with open('pk_all_ciphertexts.json') as f:
    ct = json.load(f)['PK9']

scorer = get_scorer()
ALPH = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
s13 = [0, 2, 9, 10, 10, 6, 7]
n = len(ct)

# Bigram log table
with open("words_alpha.txt") as f:
    dict_words = [w.strip().upper() for w in f if len(w.strip()) >= 3]

bg_counts = Counter()
for w in dict_words:
    for i in range(len(w) - 1):
        bg_counts[w[i:i+2]] += 1
total_bg = sum(bg_counts.values())
TBL = {bg: math.log10(c / total_bg) for bg, c in bg_counts.items()}
FLOOR = -7.5

def lp(x, y):
    return TBL.get(x + y, FLOOR)

def held_karp(T, W, w):
    full = (1 << w) - 1
    best_score, best_seq = None, None
    for start in range(w):
        NEG = float("-inf")
        dp = [[NEG] * w for _ in range(1 << w)]
        par = [[-1] * w for _ in range(1 << w)]
        dp[1 << start][start] = 0.0
        for S in range(1 << w):
            if not (S >> start) & 1:
                continue
            row = dp[S]
            for last in range(w):
                cur = row[last]
                if cur == NEG:
                    continue
                for nxt in range(w):
                    if (S >> nxt) & 1:
                        continue
                    S2 = S | (1 << nxt)
                    val = cur + T[last][nxt]
                    if val > dp[S2][nxt]:
                        dp[S2][nxt] = val
                        par[S2][nxt] = last
        for end in range(w):
            if dp[full][end] == NEG:
                continue
            total = dp[full][end] + W[end][start]
            if best_score is None or total > best_score:
                seq, S, cur = [], full, end
                while cur != -1:
                    seq.append(cur)
                    prev = par[S][cur]
                    S ^= (1 << cur)
                    cur = prev
                best_score, best_seq = total, seq[::-1]
    return best_score, best_seq

def solve_block_columnar(text, w, unit=3):
    num_blocks = len(text) // unit
    h = num_blocks // w
    # Each column has h blocks of length unit
    # In text, column k has blocks from k*h to (k+1)*h
    # block i is text[i*unit : (i+1)*unit]
    col_blocks = []
    for c in range(w):
        blks = [text[(c * h + r) * unit : (c * h + r + 1) * unit] for r in range(h)]
        col_blocks.append(blks)

    # Cost of placing col j after col i:
    # bigram from last letter of col_blocks[i][r] to first letter of col_blocks[j][r]
    T = [[sum(lp(col_blocks[i][r][-1], col_blocks[j][r][0]) for r in range(h)) if i != j else float("-inf")
          for j in range(w)] for i in range(w)]

    # Cost of wrap-around from end of row r in col i to start of row r+1 in col j:
    W = [[sum(lp(col_blocks[i][r][-1], col_blocks[j][r + 1][0]) for r in range(h - 1))
          for j in range(w)] for i in range(w)]

    score, seq = held_karp(T, W, w)
    plain = _decode_units(text, seq, unit=unit)
    return score, seq, plain

print("=== Running Block Held-Karp (unit=3) for widths [12, 16] across all 128 masks ===")
results = []
t0 = time.time()
for w in [12, 16]:
    for mask in range(128):
        shifts = [s13[i] + (13 if (mask & (1 << i)) else 0) for i in range(7)]
        z = ''.join(ALPH[(ALPH.index(c) - shifts[i % 7]) % 26] for i, c in enumerate(ct))
        bg_sc, order, plain = solve_block_columnar(z, w, unit=3)
        quad_sc = scorer.average(plain)
        results.append((quad_sc, bg_sc, w, mask, order, plain))

results.sort(key=lambda x: x[0], reverse=True)
print(f"Completed in {time.time()-t0:.2f}s")
print("\nTop 5 Block-Columnar candidates:")
for q_sc, bg_sc, w, mask, order, plain in results[:5]:
    print(f"Score: {q_sc:.4f} | Width {w} | Mask {mask} | Order: {order}")
    print(f"  PT: {plain[:70]}...")
