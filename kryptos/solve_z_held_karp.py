import math, time
from collections import Counter
Z = "EVIJSAOMWYTEESREOXDVFTIDNMZTOXAEELTGEWSUDEMOTNBSRHEITTFDLERTTOMASEJNAEWAARSENXHEPEEDTEYOLNAEEEHSESEVITEEECFRSDEELEOPPDSEIDINYSEDSAATOEOREWOEKSEN"
print("Loaded Z:", Z)
print("Length:", len(Z))

with open("all_words.txt") as f:
    dict_words = [w.strip().upper() for w in f if len(w.strip()) >= 3 and w.strip().isalpha()]

bg_counts = Counter()
for w in dict_words:
    for i in range(len(w) - 1):
        bg_counts[w[i:i+2]] += 1
total_bg = sum(bg_counts.values())
TBL = {bg: math.log10(c / total_bg) for bg, c in bg_counts.items()}
FLOOR = -7.5

def lp(x, y):
    return TBL.get(x + y, FLOOR)

def held_karp_cols(grid_cols, W, H):
    # Cost of placing col j after col i
    T = [[sum(lp(grid_cols[i][r], grid_cols[j][r]) for r in range(H)) if i != j else float("-inf")
          for j in range(W)] for i in range(W)]
    # Cost of wrap-around from end of row r in col i to start of row r+1 in col j
    W_cost = [[sum(lp(grid_cols[i][r], grid_cols[j][r+1]) for r in range(H-1))
               for j in range(W)] for i in range(W)]

    full = (1 << W) - 1
    best_score, best_seq = None, None
    for start in range(W):
        NEG = float("-inf")
        dp = [[NEG] * W for _ in range(1 << W)]
        par = [[-1] * W for _ in range(1 << W)]
        dp[1 << start][start] = 0.0
        for S in range(1 << W):
            if not (S >> start) & 1: continue
            row = dp[S]
            for last in range(W):
                cur = row[last]
                if cur == NEG: continue
                for nxt in range(W):
                    if (S >> nxt) & 1: continue
                    S2 = S | (1 << nxt)
                    val = cur + T[last][nxt]
                    if val > dp[S2][nxt]:
                        dp[S2][nxt] = val
                        par[S2][nxt] = last
        for end in range(W):
            if dp[full][end] == NEG: continue
            total = dp[full][end] + W_cost[end][start]
            if best_score is None or total > best_score:
                seq, S, cur = [], full, end
                while cur != -1:
                    seq.append(cur)
                    prev = par[S][cur]
                    S ^= (1 << cur)
                    cur = prev
                best_score, best_seq = total, seq[::-1]
    return best_score, best_seq

with open('english_quads.tsv') as f:
    quad_dict = {line.split('\t')[0]: float(line.split('\t')[1]) for line in f}

def score_quad(text):
    return sum(quad_dict.get(text[i:i+4], -9.5) for i in range(len(text)-3)) / (len(text)-3)

# Test width 12:
W = 12
H = 12
# Case A: Written by rows, read by cols (or permuted by cols)
cols = [[Z[r * W + c] for r in range(H)] for c in range(W)]
sc, order = held_karp_cols(cols, W, H)

# Decode
plain_rows = []
for r in range(H):
    plain_rows.append(''.join(cols[c][r] for c in order))
plain = ''.join(plain_rows)

print(f"\nWidth {W} (Written by rows, permuted cols):")
print(f"Held-Karp Score: {sc:.2f} | Order: {order}")
print(f"Quadgram Score: {score_quad(plain):.4f}")
print("Plaintext:")
for r in range(H):
    print(f"  Row {r:2d}: {plain_rows[r]}")

# Case B: Written by cols, permuted rows
cols_B = [[Z[c * H + r] for r in range(H)] for c in range(W)]
sc_B, order_B = held_karp_cols(cols_B, W, H)
plain_rows_B = []
for r in range(H):
    plain_rows_B.append(''.join(cols_B[c][r] for c in order_B))
plain_B = ''.join(plain_rows_B)

print(f"\nWidth {W} (Written by cols, permuted cols):")
print(f"Held-Karp Score: {sc_B:.2f} | Order: {order_B}")
print(f"Quadgram Score: {score_quad(plain_B):.4f}")
print("Plaintext:")
for r in range(H):
    print(f"  Row {r:2d}: {plain_rows_B[r]}")
