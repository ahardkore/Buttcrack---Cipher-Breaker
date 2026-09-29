import sys, json
sys.path.insert(0, '/home/user/buttcrack/src')
from buttcrack.additive_crib import solve_additive_crib

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
ct9 = cts['PK9']
n = len(ct9)

# Load quadgrams
with open('english_quads.tsv') as f:
    lines = f.readlines()
log_probs = {}
for line in lines:
    q, sc = line.strip().split('\t')
    log_probs[q] = float(sc)

def score_text(txt):
    if len(txt) < 4: return -999.0
    valid = [txt[i:i+4] for i in range(len(txt)-3) if '?' not in txt[i:i+4]]
    if not valid: return -999.0
    return sum(log_probs.get(q, -8.0) for q in valid) / len(valid)

anchors1 = ["DRAWPLATE", "DRAWING", "WHITESMITH", "EXQUISITE", "WORKSHOP"]
anchors2 = ["NEEDLE", "POINT", "THREAD", "PIERCE", "TEMPER", "HAMMER", "ANVIL", "TONGS", "COALS", "HOLES"]

print("Testing pairs of thematic anchor words on PK9 under [4, 5, 7]...")

best_sc = -999.0
best_hit = None
tested = 0

for w1 in anchors1:
    l1 = len(w1)
    for p1 in range(0, n - l1 + 1, 2):
        for w2 in anchors2:
            l2 = len(w2)
            for p2 in range(0, n - l2 + 1, 2):
                if p1 <= p2 < p1 + l1 or p2 <= p1 < p2 + l2:
                    continue # overlap
                
                tested += 1
                try:
                    res = solve_additive_crib(ct9, [4, 5, 7], [(p1, w1), (p2, w2)], alphabet='KRYPTOS')
                    if res['consistent'] and len(res['determined_positions']) >= 80:
                        pt = res['plaintext']
                        sc = score_text(pt)
                        if sc > best_sc:
                            best_sc = sc
                            best_hit = (sc, w1, p1, w2, p2, pt, len(res['determined_positions']))
                        if sc > -5.5:
                            print(f"BINGO! sc={sc:.3f} | {w1}@{p1} + {w2}@{p2} (det {len(res['determined_positions'])}/144)")
                            print(f"PT: {pt}")
                except Exception:
                    pass

print(f"\nTested {tested} anchor pairs. Best score: {best_sc:.3f}")
if best_hit:
    print(f"Hit: {best_hit[1]}@{best_hit[2]} + {best_hit[3]}@{best_hit[4]} (det {best_hit[6]}/144)")
    print(f"PT: {best_hit[5]}")
