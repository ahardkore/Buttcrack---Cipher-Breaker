#!/usr/bin/env python3
"""SIMULATED ANNEALING SOLVER FOR PK9
Jointly optimizes column permutation and polyalphabetic key schedule.
"""

import json
import math
import random
from collections import Counter

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK9"]

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
n = len(ct)

# Load dictionary & build n-gram scoring
with open("words_alpha.txt") as f:
    words = [w.strip().upper() for w in f if len(w.strip()) >= 3]

tri_counts = Counter()
for w in words:
    for i in range(len(w) - 2):
        tri_counts[w[i:i+3]] += 1

total_tri = sum(tri_counts.values())
log_tri = {t: math.log10(c / total_tri) for t, c in tri_counts.items()}
floor_tri = -7.0

def score(txt):
    return sum(log_tri.get(txt[i:i+3], floor_tri) for i in range(len(txt) - 2))

with open("words_alpha.txt") as f:
    dict_set = set(w.strip().upper() for w in f if len(w.strip()) >= 4)

def count_words(txt):
    return sum(1 for i in range(len(txt) - 3) if txt[i:i+4] in dict_set)

# Base mod-13 schedule
s13 = [0, 2, 9, 10, 10, 6, 7]

def run_annealing(width, iterations=15000):
    rows = n // width
    print(f"\n--- Running Simulated Annealing for Width {width} ({rows} rows x {width} cols) ---")
    
    # Initialize
    best_overall_score = -1e9
    best_overall_text = ""
    best_overall_state = None
    
    for restart in range(10):
        # State: perm of width, parity mask of 7 bits
        perm = list(range(width))
        random.shuffle(perm)
        mask = random.randint(0, 127)
        shifts = [(s13[i] + (13 if (mask & (1 << i)) else 0)) % 26 for i in range(7)]
        
        # Initial score
        # Decrypt outer Quagmire
        z = "".join(ALPH[(ALPH.index(ch) - shifts[i % 7]) % 26] for i, ch in enumerate(ct))
        # Columnar transpose
        cols = [z[c*rows:(c+1)*rows] for c in range(width)]
        cur_text = "".join("".join(cols[perm[c]][r] for c in range(width)) for r in range(rows))
        cur_score = score(cur_text)
        
        T = 5.0
        T_min = 0.05
        decay = (T_min / T) ** (1.0 / iterations)
        
        for it in range(iterations):
            # Propose move:
            # 70% chance swap columns, 30% chance flip parity bit or shift
            move_type = random.random()
            new_perm = list(perm)
            new_shifts = list(shifts)
            
            if move_type < 0.6:
                # swap 2 columns
                i, j = random.sample(range(width), 2)
                new_perm[i], new_perm[j] = new_perm[j], new_perm[i]
            elif move_type < 0.85:
                # flip a parity bit
                bit = random.randint(0, 6)
                new_shifts[bit] = (new_shifts[bit] + 13) % 26
            else:
                # nudge a shift by +-1 (in case mod-13 had a slight neighbor offset)
                idx = random.randint(0, 6)
                new_shifts[idx] = (new_shifts[idx] + random.choice([-1, 1])) % 26
                
            # Evaluate
            z_cand = "".join(ALPH[(ALPH.index(ch) - new_shifts[i % 7]) % 26] for i, ch in enumerate(ct))
            cols_cand = [z_cand[c*rows:(c+1)*rows] for c in range(width)]
            cand_text = "".join("".join(cols_cand[new_perm[c]][r] for c in range(width)) for r in range(rows))
            cand_score = score(cand_text)
            
            delta = cand_score - cur_score
            if delta > 0 or math.exp(delta / T) > random.random():
                perm = new_perm
                shifts = new_shifts
                cur_score = cand_score
                cur_text = cand_text
                
                if cur_score > best_overall_score:
                    best_overall_score = cur_score
                    best_overall_text = cur_text
                    best_overall_state = (list(perm), list(shifts))
                    
            T *= decay
            
        w_cnt = count_words(cur_text)
        print(f"  Restart {restart:2d}: Score = {cur_score:.1f} (avg {cur_score/142:.3f}) | Words: {w_cnt:2d} | Perm: {perm[:6]}...")
        
    print(f"\nBest Overall Score for Width {width}: {best_overall_score:.1f}")
    print(f"Key: {''.join(ALPH[s] for s in best_overall_state[1])}")
    print(f"Perm: {best_overall_state[0]}")
    print(f"Words: {count_words(best_overall_text)}")
    print(f"Text:\n{best_overall_text}\n")
    return best_overall_text

for w in [12, 9, 8]:
    run_annealing(w, iterations=8000)
