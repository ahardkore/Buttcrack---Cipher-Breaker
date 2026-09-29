import sys, json
sys.path.insert(0, '/home/user/buttcrack/src')
from buttcrack.columnar_exact import solve_columnar
from buttcrack.ciphers.quagmire3 import keyed_alphabet
from buttcrack.scoring import NgramScorer

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
ct9 = cts['PK9']
n = len(ct9)

ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
scorer = NgramScorer()

thematic_keys = [
    "KRYPTOS", "WEBSTER", "WOMACKA", "WILLIAM", "SANBORN", "SCHEIDT", "LANGLEY",
    "BERLINS", "GERMANY", "AMERICA", "HEARTHS", "NEEDLES", "WHITESM", "WORKSHO",
    "ANVILSS", "BELLOWS", "HAMMERS", "METALLS", "IRONBAR", "COPPERT", "DRAWPLT",
    "PELLEGR", "VIENNAS", "AUSTRIA", "LEIPZIG", "EASTNNE", "PALIMPS", "ABSCISS",
    "PORTALS", "SEVENTH", "FIFTEEN", "FOURTEE", "SIXTEEN", "TWENTYF", "NIMBLES",
    "WIMBLES", "WINDLES", "TROWELS", "TONGSSS", "CHISELS", "PLIERSN", "SPINDLE",
    "THIMBLE", "SHUTTLE", "BOBBINS", "LOOMSSS", "WEAVERS", "SPINNER", "TAILORS",
    "QUENCHS", "TEMPERS", "ANNEALS", "FORGING", "CRUCIBL", "FURNACE", "CASTING"
]

print(f"Testing {len(thematic_keys)} thematic keys with exact Held-Karp columnar solver...")

for kw in thematic_keys:
    shifts = [ALPH_K.index(c) for c in kw]
    # Decrypt under Quagmire III
    p_prime = "".join(ALPH_K[(ALPH_K.index(ct9[i]) - shifts[i % 7]) % 26] for i in range(n))
    
    for w in [6, 8, 9, 12, 16]:
        sol = solve_columnar(p_prime, w, scorer=scorer)
        # Check quadgram score of decrypt
        # Un-transpose p_prime with sol.order:
        # Col length H = 144 / w
        H = n // w
        # The columns of p_prime are read in sol.order
        grid = ["" for _ in range(H)]
        # sol.order gives the permutation of columns
        # Let's decode letters:
        cols = [p_prime[i*H : (i+1)*H] for i in range(w)]
        ordered_cols = [cols[c] for c in sol.order]
        pt = "".join("".join(ordered_cols[c][r] for c in range(w)) for r in range(H))
        
        qsc = scorer.average(pt)
        if qsc > -6.5:
            print(f"HIT! kw={kw}, w={w:2d}, qsc={qsc:.3f} | order={sol.order}")
            print(f"PT: {pt[:70]}...")

print("Test complete.")
