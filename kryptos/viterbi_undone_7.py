import math
from collections import Counter

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
undone = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF"
N = len(undone)
P = 7

# Load bigrams
bigrams = {}
total = 0
with open("english_quadgrams.txt") as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) == 2:
            q, cnt = parts[0], float(parts[1])
            for i in range(3):
                bi = q[i:i+2]
                bigrams[bi] = bigrams.get(bi, 0) + cnt
                total += cnt

log_bi = {k: math.log10(v / total) for k, v in bigrams.items()}
floor_bi = math.log10(0.01 / total)

def get_bi_score(c1, c2):
    return log_bi.get(c1 + c2, floor_bi)

# Columns of undone
cols = [undone[c::P] for c in range(P)]
for c in range(P):
    print(f"Col {c} len: {len(cols[c])}")

# Let's test both KRYPTOS and STANDARD alphabet
for alph_name, alph in [("KRYPTOS", ALPH), ("STANDARD", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")]:
    print(f"\n=================== Alphabet: {alph_name} ===================")
    
    # Precompute transition scores:
    # trans_score[c][s_curr][s_next] for c = 0..5:
    # bigram (Col_c[r], Col_{c+1}[r]) for r = 0..19
    trans_scores = []
    for c in range(P - 1):
        t_mat = [[0.0 for _ in range(26)] for _ in range(26)]
        for s1 in range(26):
            for s2 in range(26):
                sc = 0.0
                for r in range(20):
                    p1 = alph[(alph.index(cols[c][r]) - s1) % 26]
                    p2 = alph[(alph.index(cols[c+1][r]) - s2) % 26]
                    sc += get_bi_score(p1, p2)
                t_mat[s1][s2] = sc
        trans_scores.append(t_mat)
        
    # Wrap-around transition: from Col 6[r] to Col 0[r+1] for r = 0..19
    wrap_mat = [[0.0 for _ in range(26)] for _ in range(26)]
    for s6 in range(26):
        for s0 in range(26):
            sc = 0.0
            for r in range(20):
                p6 = alph[(alph.index(cols[6][r]) - s6) % 26]
                p0 = alph[(alph.index(cols[0][r+1]) - s0) % 26]
                sc += get_bi_score(p6, p0)
            wrap_mat[s6][s0] = sc
            
    # For each possible initial shift s0 in range(26):
    # Run dynamic programming to find optimal s1..s6 and return to s0
    best_cycle_score = -1e9
    best_shifts = None
    
    for s0_start in range(26):
        # dp[step][state]
        dp = [-1e9] * 26
        dp[s0_start] = 0.0
        backpointers = []
        
        for step in range(P - 1):
            next_dp = [-1e9] * 26
            bp = [0] * 26
            for curr_s in range(26):
                if dp[curr_s] <= -1e8: continue
                for next_s in range(26):
                    val = dp[curr_s] + trans_scores[step][curr_s][next_s]
                    if val > next_dp[next_s]:
                        next_dp[next_s] = val
                        bp[next_s] = curr_s
            dp = next_dp
            backpointers.append(bp)
            
        # Add wrap-around to s0_start
        for s6 in range(26):
            if dp[s6] <= -1e8: continue
            total_val = dp[s6] + wrap_mat[s6][s0_start]
            if total_val > best_cycle_score:
                best_cycle_score = total_val
                # Reconstruct path
                curr = s6
                path = [curr]
                for bp in reversed(backpointers):
                    curr = bp[curr]
                    path.append(curr)
                path.reverse()
                best_shifts = path
                
    print(f"Optimal Viterbi Bigram Score: {best_cycle_score:.2f} (avg per bigram: {best_cycle_score / 140:.3f})")
    print(f"Optimal Shifts: {best_shifts}")
    key_chars = "".join(alph[s] for s in best_shifts)
    print(f"Key in {alph_name}: {key_chars}")
    
    # Decrypt text
    pt = "".join(alph[(alph.index(undone[i]) - best_shifts[i % P]) % 26] for i in range(N))
    print(f"Decrypted text:\n{pt}\n")
