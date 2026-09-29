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

clock_sets = [
    [2, 3, 5, 7],
    [3, 5, 7],
    [2, 5, 7],
    [5, 6, 7],
    [6, 7, 8],
    [7, 8, 9],
    [4, 7, 8],
    [4, 7, 9],
    [5, 7, 8],
    [5, 7, 9]
]

cribs = [
    "THEWHITESMITH", "WHITESMITHS", "INTHEWORKSHOP", "EXQUISITENEEDLE",
    "STUDYUNDERHIM", "FORTENYEARS", "OFMYOWNMAKING", "INVESTIGATION",
    "SEVENTHMONTH", "FIFTEENCORRESPONDENTS", "SPLITAHAIR", "PIERCEGLASS",
    "THEFIREWASLIT", "HAMMERANDANVIL", "DRAWINGTHEWIRE", "THROUGHTHEDRAWPLATE",
    "EACHHOLESMALLER", "FINEENOUGHTOSPLIT", "PIERCEGLASSATLAST", "HEPOINTEDTOTHE",
    "HEHEATEDTHESTEEL", "HEQUENCHEDITINOIL", "TOTEMPERTHESTEEL", "THEFIRSTNEEDLE"
]

print(f"Testing {len(clock_sets)} clock sets with {len(cribs)} cribs across PK9...")

for cset in clock_sets:
    best_cset_sc = -999.0
    best_hit = None
    for c in cribs:
        L = len(c)
        for pos in range(n - L + 1):
            try:
                res = solve_additive_crib(ct9, cset, [(pos, c)], alphabet='KRYPTOS')
                if res['consistent'] and len(res['determined_positions']) >= 80:
                    pt = res['plaintext']
                    sc = score_text(pt)
                    if sc > best_cset_sc:
                        best_cset_sc = sc
                        best_hit = (sc, c, pos, pt, len(res['determined_positions']))
                    if sc > -5.5:
                        print(f"BINGO! cset={cset} sc={sc:.3f} | {c}@{pos} (det {len(res['determined_positions'])}/144)")
                        print(f"PT: {pt}")
            except Exception:
                pass
    if best_hit:
        print(f"Clock set {cset}: best sc={best_cset_sc:.3f} | '{best_hit[1]}'@{best_hit[2]} (det {best_hit[4]}/144)")
    else:
        print(f"Clock set {cset}: no placement reached >= 80 determined letters.")

print("Search complete.")
