import math

bigrams = {}
total = 0
with open("english_quadgrams.txt") as f:
    for line in f:
        p = line.strip().split()
        if len(p) == 2:
            q, cnt = p[0], float(p[1])
            for i in range(3):
                bi = q[i:i+2]
                bigrams[bi] = bigrams.get(bi, 0) + cnt
                total += cnt

log_bi = {k: math.log10(v / total) for k, v in bigrams.items()}
floor_bi = math.log10(0.01 / total)

def get_bi(c1, c2):
    return log_bi.get(c1 + c2, floor_bi)

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
undone = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF"
N = len(undone)
P = 7

# Slices
cols = [[ALPH.index(c) for c in undone[i::P]] for i in range(P)]

# Conventions:
# 1. Vigenere: P = (C - K) % 26
# 2. Beaufort: P = (K - C) % 26
# 3. VarBeaufort: P = (C + K) % 26

for conv_name, sign_c, sign_k in [("Vigenere (C - K)", 1, -1), ("Beaufort (K - C)", -1, 1), ("VarBeaufort (C + K)", 1, 1)]:
    # Find optimal pairwise transitions between columns
    # Viterbi DP
    # For c in 0..5: trans[c][s1][s2]
    # wrap: trans[6][s6][s0]
    
    # We want to maximize total bigram score across all 20 rows
    best_cycle_score = -1e9
    best_shifts = None
    
    # Precompute transition tables
    trans = []
    for c in range(P - 1):
        L = min(len(cols[c]), len(cols[c+1]))
        t_mat = []
        for s1 in range(26):
            row = []
            for s2 in range(26):
                sc = 0.0
                for r in range(L):
                    p1 = ALPH[(sign_c * cols[c][r] + sign_k * s1) % 26]
                    p2 = ALPH[(sign_c * cols[c+1][r] + sign_k * s2) % 26]
                    sc += get_bi(p1, p2)
                row.append(sc)
            t_mat.append(row)
        trans.append(t_mat)
        
    wrap = []
    L_wrap = min(len(cols[6]), len(cols[0]) - 1)
    for s6 in range(26):
        row = []
        for s0 in range(26):
            sc = 0.0
            for r in range(L_wrap):
                p6 = ALPH[(sign_c * cols[6][r] + sign_k * s6) % 26]
                p0 = ALPH[(sign_c * cols[0][r+1] + sign_k * s0) % 26]
                sc += get_bi(p6, p0)
            row.append(sc)
        wrap.append(row)
        
    for s0_start in range(26):
        dp = [-1e9] * 26
        dp[s0_start] = 0.0
        bps = []
        for step in range(P - 1):
            next_dp = [-1e9] * 26
            bp = [0] * 26
            for curr_s in range(26):
                if dp[curr_s] <= -1e8: continue
                for next_s in range(26):
                    v = dp[curr_s] + trans[step][curr_s][next_s]
                    if v > next_dp[next_s]:
                        next_dp[next_s] = v
                        bp[next_s] = curr_s
            dp = next_dp
            bps.append(bp)
            
        for s6 in range(26):
            if dp[s6] <= -1e8: continue
            tot = dp[s6] + wrap[s6][s0_start]
            if tot > best_cycle_score:
                best_cycle_score = tot
                curr = s6
                path = [curr]
                for bp in reversed(bps):
                    curr = bp[curr]
                    path.append(curr)
                path.reverse()
                best_shifts = path
                
    avg_bi = best_cycle_score / (20 * 7)
    key_str = "".join(ALPH[s] for s in best_shifts)
    pt = "".join(ALPH[(sign_c * ALPH.index(undone[i]) + sign_k * best_shifts[i % P]) % 26] for i in range(N))
    print(f"\n{conv_name}:")
    print(f"  Avg Bigram Score: {avg_bi:.3f} | Total: {best_cycle_score:.1f}")
    print(f"  Shifts: {best_shifts} -> Key: {key_str}")
    print(f"  PT (first 80): {pt[:80]}")

