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

theophilus_cribs = [
    "TWOIRONSTHREEFINGERS", "THROUGHWICHHOLESTHE", "HOLESTHEWIRESAREDRAWN",
    "SMOOTHLYBEATENLONGANDROUND", "SMOOTHLYBEATENLONG", "DRAWINGTHEWIRETHROUGH",
    "PULLEDTHROUGHSMALLERAND", "GRADUALLYLENGTHENINGAND", "UNTILTHEDESIREDGAUGE",
    "AHARDENEDSTEELPLATEPIERCED", "STEELPLATEPIERCEDWITH", "SUCCESSIVELYSMALLER",
    "EACHPASSTHROUGHA", "REFINETHEWIREDIAMETER", "INCREASINGTENSILESTRENGTH",
    "ANNEALEDTOEXACTLYTHE", "EXACTLYTHERIGHTTEMPER", "TWISTEDANDCOILEDWIRE",
    "WITHASTEELPUNCHTOFORM", "WITHASTEELPUNCHTO", "INANIRONPLATETHEPLATE",
    "HARDENOUGHTODRAWGOLD", "HARDENOUGHTODRAW", "AFINGERINLENGTHRECTANGULAR",
    "AFINGERINLENGTH", "UNDERNEATHLENGTHWISE", "AGROOVEISTRACEDANDIS",
    "ONBOTHSIDESOFITSHARP", "STRONGHANDPLIERSHAVING", "STRONGHANDPLIERS",
    "LONGSLENDERTONGS", "LONGMETALCASTERSTONGS", "SLIGHTLYCURVEDATTHEFRONT",
    "HAVINGLARGEMETAL", "CURVEDUPWARDSBUT", "GOLDENANDSILVERWIRES",
    "THICKANDFINEAREFILED", "SOBEADSMAYAPPEARON", "BEADEDWIREWORK",
    "FINEENOUGHTOSPLIT", "PIERCEGLASSATLAST", "HEPOINTEDTOTHEGUTTER",
    "ONEOFMYOWNMAKING", "THERESIDUEOFHISPRACTICE", "EXQUISITENEEDLESTHE"
]

print(f"Testing {len(theophilus_cribs)} Theophilus craft cribs on PK9 under [4, 5, 7]...")

best_sc = -999.0
best_cand = None

for p in theophilus_cribs:
    L = len(p)
    if L < 14: continue
    for pos in range(n - L + 1):
        try:
            res = solve_additive_crib(ct9, [4, 5, 7], [(pos, p)], alphabet='KRYPTOS')
            if res['consistent'] and len(res['determined_positions']) == 144:
                pt = res['plaintext']
                sc = score_text(pt)
                if sc > best_sc:
                    best_sc = sc
                    best_cand = (sc, p, pos, pt)
                if sc > -5.5:
                    print(f"BINGO! score={sc:.3f} | {p} at {pos}")
                    print(f"PT: {pt}")
        except Exception:
            pass

print(f"\nDone. Best score under [4, 5, 7]: {best_sc:.3f}")
if best_cand:
    print(f"Cand: '{best_cand[1]}' at {best_cand[2]}")
    print(f"PT: {best_cand[3]}")
