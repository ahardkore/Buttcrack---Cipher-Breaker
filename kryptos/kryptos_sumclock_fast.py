#!/usr/bin/env python3
"""Ultra-fast Simulated Annealing and Coordinate Descent for Multi-Clock Quagmire III.
"""

import math, json, random, time
import numpy as np

# Load quadgrams
print("Loading quadgram table...")
floor = -8.0
ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
idx = {c: i for i, c in enumerate(ALPH)}

quad_table = np.full(26 * 26 * 26 * 26, floor, dtype=np.float32)
with open("english_quads.tsv") as f:
    for line in f:
        q, sc = line.strip().split("\t")
        if all(c in idx for c in q):
            code = idx[q[0]] * 17576 + idx[q[1]] * 676 + idx[q[2]] * 26 + idx[q[3]]
            quad_table[code] = float(sc)

print("Quad table precomputed successfully.")

with open("pk_all_ciphertexts.json") as f:
    ciphers = json.load(f)

def run_solver(cipher_name, clocks, num_restarts=100, sa_steps=3000):
    ct = ciphers[cipher_name]
    n = len(ct)
    c_idx = np.array([idx[c] for c in ct], dtype=np.int32)
    m = n - 3

    print(f"\n{'='*70}\nRunning solver for {cipher_name} (N={n}) with clocks {clocks}\n{'='*70}")

    best_overall_score = -999.0
    best_overall_pt = ""
    best_overall_shifts = None

    t0 = time.time()

    for restart in range(num_restarts):
        # Initialize random shifts for each clock
        shifts = [np.random.randint(0, 26, size=p, dtype=np.int32) for p in clocks]

        # Compute full keystream and plaintext
        ks = np.zeros(n, dtype=np.int32)
        for c_i, p in enumerate(clocks):
            for i in range(n):
                ks[i] += shifts[c_i][i % p]
        ks %= 26
        pt_idx = (c_idx - ks) % 26

        # Compute initial score
        total_score = 0.0
        for i in range(m):
            code = pt_idx[i] * 17576 + pt_idx[i+1] * 676 + pt_idx[i+2] * 26 + pt_idx[i+3]
            total_score += quad_table[code]

        # Simulated Annealing phase
        temp = 1.0
        cooling = 0.998

        for step in range(sa_steps):
            # Pick a random clock and a random position
            clock_id = random.randrange(len(clocks))
            p = clocks[clock_id]
            pos = random.randrange(p)
            old_val = shifts[clock_id][pos]
            new_val = (old_val + random.randint(1, 25)) % 26
            diff = (new_val - old_val) % 26

            # Affected positions in text: i = pos + k * p
            affected = [i for i in range(pos, n, p)]
            # Find all unique quadgram start indices affected: i-3, i-2, i-1, i
            quad_indices = set()
            for i in affected:
                for q_start in (i - 3, i - 2, i - 1, i):
                    if 0 <= q_start < m:
                        quad_indices.add(q_start)

            # Compute delta score
            delta = 0.0
            # Old quad contribution
            for q_start in quad_indices:
                code_old = pt_idx[q_start] * 17576 + pt_idx[q_start+1] * 676 + pt_idx[q_start+2] * 26 + pt_idx[q_start+3]
                delta -= quad_table[code_old]

            # Apply change temporarily
            shifts[clock_id][pos] = new_val
            for i in affected:
                pt_idx[i] = (pt_idx[i] - diff) % 26

            # New quad contribution
            for q_start in quad_indices:
                code_new = pt_idx[q_start] * 17576 + pt_idx[q_start+1] * 676 + pt_idx[q_start+2] * 26 + pt_idx[q_start+3]
                delta += quad_table[code_new]

            # Accept or reject
            if delta > 0 or math.exp(delta / (temp * 10.0)) > random.random():
                total_score += delta
            else:
                # Revert
                shifts[clock_id][pos] = old_val
                for i in affected:
                    pt_idx[i] = (pt_idx[i] + diff) % 26

            temp *= cooling

        # Greedy coordinate descent polishing
        improved = True
        while improved:
            improved = False
            for clock_id, p in enumerate(clocks):
                for pos in range(p):
                    old_val = shifts[clock_id][pos]
                    best_val = old_val
                    best_delta = 0.0

                    affected = [i for i in range(pos, n, p)]
                    quad_indices = set()
                    for i in affected:
                        for q_start in (i - 3, i - 2, i - 1, i):
                            if 0 <= q_start < m:
                                quad_indices.add(q_start)

                    old_contrib = sum(quad_table[pt_idx[q_s] * 17576 + pt_idx[q_s+1] * 676 + pt_idx[q_s+2] * 26 + pt_idx[q_s+3]] for q_s in quad_indices)

                    for test_val in range(26):
                        if test_val == old_val:
                            continue
                        test_diff = (test_val - old_val) % 26
                        for i in affected:
                            pt_idx[i] = (pt_idx[i] - test_diff) % 26
                        new_contrib = sum(quad_table[pt_idx[q_s] * 17576 + pt_idx[q_s+1] * 676 + pt_idx[q_s+2] * 26 + pt_idx[q_s+3]] for q_s in quad_indices)
                        cur_delta = new_contrib - old_contrib
                        if cur_delta > best_delta:
                            best_delta = cur_delta
                            best_val = test_val
                        for i in affected:
                            pt_idx[i] = (pt_idx[i] + test_diff) % 26

                    if best_delta > 1e-4:
                        apply_diff = (best_val - old_val) % 26
                        shifts[clock_id][pos] = best_val
                        for i in affected:
                            pt_idx[i] = (pt_idx[i] - apply_diff) % 26
                        total_score += best_delta
                        improved = True

        avg_score = total_score / m
        if avg_score > best_overall_score:
            best_overall_score = avg_score
            best_overall_pt = "".join(ALPH[pt_idx[i]] for i in range(n))
            best_overall_shifts = [s.copy() for s in shifts]
            print(f"Restart {restart:3d} ({(time.time()-t0):.1f}s): Score = {best_overall_score:.4f}")
            print(f"   PT: {best_overall_pt[:80]}...")
            if best_overall_score > -5.0:
                print("   *** STRONG ENGLISH CANDIDATE FOUND! ***")

    print(f"\nFinal Best Score for {cipher_name} with {clocks}: {best_overall_score:.4f}")
    print(f"Full Text:\n{best_overall_pt}\n")
    return best_overall_score, best_overall_pt, best_overall_shifts

if __name__ == "__main__":
    import sys
    c_name = sys.argv[1] if len(sys.argv) > 1 else "PK8"
    clks = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [4, 5, 6, 7]
    restarts = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    run_solver(c_name, clks, restarts)
