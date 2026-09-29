import sys, json
sys.path.insert(0, '/home/user/buttcrack/src')
from buttcrack.additive_crib import solve_additive_crib

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
ct8 = cts['PK8']
n = len(ct8)

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

candidates = [
    # Bellows / Fire / Coals
    "IPUMPEDTHEBELLOWS", "WEPUMPEDTHEBELLOWS", "HEPUMPEDTHEBELLOWS",
    "THEBELLOWSSANGAS", "THEBELLOWSROARED", "THEBELLOWSBLEWAS",
    "THECOALSTURNEDWHITE", "THECOALSBEGANTOGLOW", "THECOALSGLOWEDWHITE",
    "WHITEHOTHEATINTHE", "WHENTHEFIREWASREADY", "WHENTHEFIREWASHOT",
    "WHENTHEHEARTHEEACHED", "WHENTHECOALSWEREWHITE", "UNTILTHECOALSTURNED",
    "UNTILTHEFIREWASREADY", "UNTILTHEFIREWASHOT", "ATLASTTHEFIREWASREADY",
    "ATLASTTHEFIREWASHOT", "ATLASTTHEFIREWASLIT", "THEFIREWASLITANDTHE",
    "THEHEATINTHEHEARTH", "THEHEARTHWASNOWREADY", "THEFORGEWASNOWREADY",
    "HEPLACEDTHECRUCIBLE", "HETURNEDTOTHEHEARTH", "HETURNEDTOTHEFORGE",
    "HETOOKUPTHETONGSAND", "HETOKETHETONGSAND", "HETOOKTHETONGSFROM",
    "INTOTHEWHITEHOTCOALS", "INTOTHEGLOWINGCOALS", "WITHTHETONGSHEPLACED",
    "HESHOVELEDCOALINTO", "HETOSSVALCOALINTO", "THEFLAMESLEAPEDUP",
    "THESMOKEROSEINTOTHE", "THESPARKSFLEWFROM", "HEHEATEDTHESTEELUNTIL",
    "HEHEATEDTHEIRONUNTIL", "HEHEATEDTHEMETALUNTIL", "HESATBYTHEHEARTHAND",
    "NOWTHEWORKCOULDBEGIN", "NOWTHEWORKBEGANIN", "ANDTHEWORKCOULDBEGIN",
    "METHEWORKCOULDBEGIN", "TOLDMETHEWORKCOULD", "SAIDTHATTHEWORKCOULD",
    "FORHOURSIWATCHEDHIM", "FORHOURSWESTOODBY", "DAYAFTERDAYINTHE",
    "THEFIRSTLESSONWAS", "MYFIRSTLESSONWAS", "HEEXPLAINEDTHATTHE",
    "HESHOWEDMETHATTHE", "HEWARNEDMETHATTHE", "WITHOUTPROPERHEAT",
    "IFTHEHEATISTOOLOW", "IFTHEHEARTHISTOO", "THESTEELWILLBEBRITTLE",
    "THEIRONWILLBEBRITTLE", "THEWIREWILLBREAKIF", "TOODRAWTHEWIREFINE"
]

print(f"Testing {len(candidates)} candidate phrases on PK8 under [4, 5, 6, 7]...")

best_sc = -999.0
best_hit = None

for p in candidates:
    L = len(p)
    for pos in range(n - L + 1):
        try:
            res = solve_additive_crib(ct8, [4, 5, 6, 7], [(pos, p)], alphabet='KRYPTOS')
            if res['consistent'] and len(res['determined_positions']) >= 80:
                pt = res['plaintext']
                sc = score_text(pt)
                if sc > best_sc:
                    best_sc = sc
                    best_hit = (sc, p, pos, pt, len(res['determined_positions']))
                if sc > -5.5:
                    print(f"BINGO! sc={sc:.3f} | {p} at {pos} (det {len(res['determined_positions'])}/153)")
                    print(f"PT: {pt}")
        except Exception:
            pass

print(f"\nDone. Best score: {best_sc:.3f}")
if best_hit:
    print(f"Hit: '{best_hit[1]}' at pos {best_hit[2]} (det {best_hit[4]}/153)")
    print(f"PT: {best_hit[3]}")
