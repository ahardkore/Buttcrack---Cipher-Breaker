import json
import math
from solve_pk8_with_cribs import solve_additive_crib, KRYPTOS_ALPHABET

with open("pk_all_ciphertexts.json") as f:
    cts = json.load(f)

ct8 = cts["PK8"]
N = len(ct8)

# Load quadgrams
quad_counts = {}
total = 0
with open("english_quadgrams.txt") as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) == 2:
            c = float(parts[1])
            quad_counts[parts[0]] = c
            total += c

log_quads = {k: math.log10(v / total) for k, v in quad_counts.items()}
floor = math.log10(0.01 / total)

def score_text(text):
    s = sum(log_quads.get(text[i:i+4], floor) for i in range(len(text)-3))
    return s / (len(text) - 3)

with open("pk8_needlemaking_cribs.txt") as f:
    cribs = [line.strip().upper() for line in f if len(line.strip()) >= 18]

print(f"Loaded {len(cribs)} 18-char needlemaking cribs. Dragging across PK8...")

best_score = -999.0
best_match = None

for c_idx, crib in enumerate(cribs):
    crib = crib[:18]
    for pos in range(N - 18 + 1):
        res = solve_additive_crib(ct8, [4, 5, 6, 7], [(pos, crib)])
        if res["consistent"] and res["determined_count"] == N:
            pt = res["plaintext"]
            sc = score_text(pt)
            if sc > -6.0:
                print(f"HIT! Score: {sc:.4f} | pos {pos:3d} | crib: {crib}")
                print(f"PT: {pt}")
            if sc > best_score:
                best_score = sc
                best_match = (sc, pos, crib, pt)

print(f"\nDrag complete. Best score: {best_score:.4f}")
if best_match:
    print(f"Best: pos {best_match[1]} | crib: {best_match[2]}")
    print(f"PT: {best_match[3]}")
