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

phrases = [
    "MYFIRSTLESSONWASTO", "HEHANDEDMEAPIECEOF", "HEHANDEDMEARODOF", "HEHANDEDMETHETONGS",
    "HEHANDEDMETHEHAMMER", "HETOOKAPIECEOFSILVER", "HETOOKAPIECOFSTEEL", "HEPLACEDTHESILVERIN",
    "HEPLACEDTHEMETALIN", "WEBEGANBYDRAWING", "HETAUGHTMETODRAW", "FIRSTHETAUGHTMETO",
    "FIRSTWEHADTODRAW", "FIRSTIHADTODRAW", "FIRSTHETOOKTHE", "IWATCHEDASHETOOK",
    "IWATCHEDASHEDREW", "HEDREWTHEWIRETHROUGH", "HEDREWTHESILVERTHROUGH", "WEDREWTHEWIRETHROUGH",
    "THROUGHTHEDRAWPLATE", "THROUGHTHEHOLESOFTHE", "THROUGHEACHHOLEINTURN", "EACHHOLESMALLERTHANTHELAST",
    "HOLEBYHOLESMALLERTHAN", "FROMTHELARGESTTOTHESMALLEST", "UNTILTHEWIREWASASFINEAS",
    "UNTILITWASASFINEASAHAIR", "FINEENOUGHTOSPLITAHAIR", "FINEENOUGHTOPIERCEGLASS",
    "ORPIERCEGLASSATLAST", "THENWITHASMALLCHISEL", "THENWITHAFINEPUNCH", "HEPIERCEDTHEEYEOFTHE",
    "TOPIERCETHEEYEOFTHE", "HEPIERCEDTHEEYEWITHA", "THEEYEWASSOSMALLTHAT", "HEGROUNDTHEPOINTONTHE",
    "ONTHEGRINDSTONEHESHAPED", "HESHAPEDTHEPOINTUNTIL", "HEQUENCHEDITINOIL", "WEQUENCHEDITINOIL",
    "QUENCHEDINAFLASKOF", "TOTEMPERTHESTEELHE", "UNTILATLASTTHENEEDLE", "THEFIRSTNEEDLEOFMYOWN",
    "ANEEDLEOFMYOWNMAKING", "ONEOFMYOWNMAKINGATLAST", "ITWASSOSFINETHATITCOULD", "THERESIDUEOFHISPRACTICE",
    "THESILVERWASTHEN", "HETOOKTHEHAMMERAND", "HESTRUCKTHEANVILAND", "HETURNEDTOTHEANVIL",
    "WITHASMALLHAMMERHE", "HEHEATEDTHEWIREIN", "INTHEWHITEHOTCOALS", "HEPOUREDTHEMOLTEN",
    "DRAWINGTHEWIRETHROUGH", "EACHPASSMAKINGIT", "PASSINGITTHROUGH", "DRAWINGITTHROUGH",
    "TILLITWASASFINEAS", "THINASASPIDERSWEB", "FINEASASPIDERSWEB", "ASFINEASATHREAD",
    "TOTRAINMETOBEOME", "IFISTUDYUNDERHIM", "TENYEARSOFPRACTICE", "DAYAFTERDAYWESTOOD",
    "EACHMORNINGWEBEGAN", "ATDAWNWEBEGANBY", "THEFIREWASREADYAND", "WHENTHEFIREWASREADY"
]

print(f"Testing {len(phrases)} deep narrative phrases on PK9 across all positions under (4, 5, 7)...")

best_score = -999.0
best_candidate = None
found = 0

for p in phrases:
    L = len(p)
    if L < 14: continue
    for pos in range(n - L + 1):
        try:
            res = solve_additive_crib(ct9, [4, 5, 7], [(pos, p)], alphabet='KRYPTOS')
            if res['consistent'] and len(res['determined_positions']) == 144:
                pt = res['plaintext']
                sc = score_text(pt)
                if sc > best_score:
                    best_score = sc
                    best_candidate = (sc, p, pos, pt)
                if sc > -5.5:
                    print(f"BINGO! score={sc:.3f} | {p} at {pos}")
                    print(f"PT: {pt}")
                    found += 1
        except Exception:
            pass

print(f"\nCompleted search. Found {found} high-confidence decryptions.")
print(f"Best score overall: {best_score:.3f}")
if best_candidate:
    print(f"Phrase: '{best_candidate[1]}' at position {best_candidate[2]}")
    print(f"Decrypted text: {best_candidate[3]}")
