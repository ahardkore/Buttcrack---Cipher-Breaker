import json
from collections import Counter
from buttcrack.scoring import NgramScorer
scorer = NgramScorer()

col_pairs = [
    ('E', 'W', 0),
    ('H', 'F', 1),
    ('A', 'E', 2),
    ('H', 'T', 3),
    ('S', 'R', 4),
    ('S', 'E', 5),
    ('D', 'E', 6),
    ('S', 'E', 7),
    ('O', 'E', 8),
    ('O', 'P', 9),
    ('F', 'S', 10),
    ('U', 'D', 11),
]

# We want to find a permutation p_col of (0..11) such that:
# Row 11 string: ''.join(col_pairs[c][0] for c in p_col)
# Row 8 string:  ''.join(col_pairs[c][1] for c in p_col)
# Both have high English quadgram scores!

# Let's do simulated annealing directly on p_col to maximize (Score(Row 11) + Score(Row 8))!
import random
import math

best_p = list(range(12))
best_sc = -1e9

for restart in range(200):
    p = list(range(12))
    random.shuffle(p)
    
    def eval_p(perm):
        s11 = "".join(col_pairs[c][0] for c in perm)
        s8  = "".join(col_pairs[c][1] for c in perm)
        return (scorer.score(s11) + scorer.score(s8)) / 18.0
        
    cur_sc = eval_p(p)
    temp = 1.0
    cooling = 0.9995
    
    for step in range(5000):
        i, j = random.sample(range(12), 2)
        p[i], p[j] = p[j], p[i]
        new_sc = eval_p(p)
        delta = new_sc - cur_sc
        if delta > 0 or random.random() < math.exp(delta / temp):
            cur_sc = new_sc
            if cur_sc > best_sc:
                best_sc = cur_sc
                best_p = list(p)
        else:
            p[i], p[j] = p[j], p[i]
        temp *= cooling

s11 = "".join(col_pairs[c][0] for c in best_p)
s8  = "".join(col_pairs[c][1] for c in best_p)
print(f"Global Best Joint Score: {best_sc:.4f}")
print(f"Optimal p_col: {best_p}")
print(f"Row 11: {s11} (score: {scorer.score(s11)/9.0:.2f})")
print(f"Row  8: {s8}  (score: {scorer.score(s8)/9.0:.2f})")

