import json
import random
import math

ALPH = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
k2std = [ord(c) - ord('A') for c in ALPH]
hpos = {c: i for i, c in enumerate(ALPH)}

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)

undone = cts['PK9_UNDONE']
N = len(undone)

# Load dictionary words for fast word coverage checking
print("Loading dictionary words...")
with open("all_words.txt") as f:
    dict_words = set(w.strip().upper() for w in f if len(w.strip()) >= 3)

# Load quadgrams
floor = -9.5
quad = {}
with open('english_quads.tsv') as f:
    for line in f:
        q, sc = line.strip().split('\t')
        if len(q) == 4: quad[q] = float(sc)

def score_candidate(shifts):
    pt = []
    for i, ch in enumerate(undone):
        s = shifts[i % 14]
        p_kr = (hpos[ch] - s) % 26
        pt.append(chr(ord('A') + k2std[p_kr]))
    pt_str = "".join(pt)

    # 1. Quadgram score
    q_score = sum(quad.get(pt_str[i:i+4], floor) for i in range(N - 3)) / (N - 3)

    # 2. Word count / coverage
    # Find all words of length 3..8 in pt_str
    words_found = []
    for l in [3, 4, 5, 6, 7]:
        for i in range(N - l + 1):
            sub = pt_str[i:i+l]
            if sub in dict_words:
                words_found.append(sub)

    # Weight score
    total_score = q_score + 0.05 * len(words_found)
    return total_score, q_score, len(words_found), pt_str

# Initialize with the best known seed key
init_key_str = "BYAACYUOHGODBU"
shifts = [hpos[c] for c in init_key_str]

best_score, q_sc, n_w, best_pt = score_candidate(shifts)
print(f"Seed Key: {init_key_str} | Score: {best_score:.4f} (Quad: {q_sc:.4f}, Words: {n_w})")
print(f"PT: {best_pt[:70]}...\n")

# Run 200 random-restart coordinate descents
for restart in range(100):
    cur_shifts = [random.randint(0, 25) for _ in range(14)] if restart > 0 else shifts.copy()
    cur_score, _, _, _ = score_candidate(cur_shifts)

    # Coordinate descent
    improved = True
    while improved:
        improved = False
        for pos in range(14):
            best_val = cur_shifts[pos]
            best_delta = 0.0
            old_val = cur_shifts[pos]

            for diff in range(1, 26):
                cur_shifts[pos] = (old_val + diff) % 26
                sc, _, _, _ = score_candidate(cur_shifts)
                if sc - cur_score > best_delta:
                    best_delta = sc - cur_score
                    best_val = cur_shifts[pos]

            if best_delta > 1e-4:
                cur_shifts[pos] = best_val
                cur_score += best_delta
                improved = True
            else:
                cur_shifts[pos] = old_val

    if cur_score > best_score:
        best_score = cur_score
        shifts = cur_shifts.copy()
        _, q_sc, n_w, best_pt = score_candidate(shifts)
        key_str = "".join(ALPH[s] for s in shifts)
        print(f"Restart {restart:2d}: New Best Score = {best_score:.4f} (Quad: {q_sc:.4f}, Words: {n_w}) | Key: {key_str}")
        print(f"  PT: {best_pt}\n")

key_str = "".join(ALPH[s] for s in shifts)
print(f"\nFinal Best Key (Period 14): {key_str}")
print(f"Plaintext:\n{best_pt}")
