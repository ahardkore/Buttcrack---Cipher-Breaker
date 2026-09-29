from collections import Counter

ALPH_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def make_keyed_alphabet(kw):
    seen = set()
    res = []
    for c in kw.upper():
        if c in ALPH_STD and c not in seen:
            seen.add(c)
            res.append(c)
    for c in ALPH_STD:
        if c not in seen:
            seen.add(c)
            res.append(c)
    return "".join(res)

with open('pk_all_ciphertexts.json') as f:
    import json
    cts = json.load(f)
ct9 = cts['PK9']

# Load quadgrams
with open('english_quads.tsv') as f:
    lines = f.readlines()
log_probs = {}
for line in lines:
    q, sc = line.strip().split('\t')
    log_probs[q] = float(sc)

def score_text(txt):
    if len(txt) < 4: return -999.0
    return sum(log_probs.get(txt[i:i+4], -8.0) for i in range(len(txt)-3)) / (len(txt)-3)

keywords = [
    "KRYPTOS", "WHITESMITH", "WORKSHOP", "BERLINCLOCK", "WEBSTER", "WOMACKA",
    "SANBORN", "SCHEIDT", "LANGLEY", "PALIMPSEST", "ABSCISSA", "ORDINATE",
    "PENTIMENTO", "PROVENANCE", "PORTAL", "NEEDLE", "HEARTH", "COPPER",
    "BELLOWS", "CRUCIBLE", "FURNACE", "STANDARD"
]

print(f"Testing {len(keywords)} keyed alphabets on raw C under period 7...")

for kw in keywords:
    alph = make_keyed_alphabet(kw) if kw != "STANDARD" else ALPH_STD
    
    # We can do coordinate ascent or beam search on the 7 shifts
    # First: find best shift for each column independently by chi2
    shifts = [0] * 7
    # English monogram freqs
    efreq = {'E': 0.127, 'T': 0.091, 'A': 0.082, 'O': 0.075, 'I': 0.070, 'N': 0.067, 'S': 0.063, 'H': 0.061, 'R': 0.060, 'D': 0.043, 'L': 0.040, 'C': 0.028, 'U': 0.028, 'M': 0.024, 'W': 0.024, 'F': 0.022, 'G': 0.020, 'Y': 0.020, 'P': 0.019, 'B': 0.015, 'V': 0.010, 'K': 0.008, 'J': 0.002, 'X': 0.0015, 'Q': 0.001, 'Z': 0.0007}
    
    for r in range(7):
        col = ct9[r::7]
        L = len(col)
        best_chi2 = 1e9
        best_s = 0
        for s in range(26):
            # Quagmire III: P = alph[(alph.index(c) - s) % 26]
            dec = [alph[(alph.index(c) - s) % 26] for c in col]
            counts = Counter(dec)
            chi2 = sum(((counts.get(c, 0) - L * efreq[c])**2) / (L * efreq[c]) for c in ALPH_STD)
            if chi2 < best_chi2:
                best_chi2 = chi2
                best_s = s
        shifts[r] = best_s

    # Coordinate ascent to maximize quadgrams
    cur_pt = "".join(alph[(alph.index(ct9[i]) - shifts[i % 7]) % 26] for i in range(len(ct9)))
    cur_sc = score_text(cur_pt)
    improved = True
    while improved:
        improved = False
        for r in range(7):
            best_r_sc = cur_sc
            best_r_s = shifts[r]
            for s in range(26):
                shifts[r] = s
                pt = "".join(alph[(alph.index(ct9[i]) - shifts[i % 7]) % 26] for i in range(len(ct9)))
                sc = score_text(pt)
                if sc > best_r_sc:
                    best_r_sc = sc
                    best_r_s = s
            shifts[r] = best_r_s
            if best_r_sc > cur_sc:
                cur_sc = best_r_sc
                improved = True

    final_pt = "".join(alph[(alph.index(ct9[i]) - shifts[i % 7]) % 26] for i in range(len(ct9)))
    key_chars = "".join(alph[s] for s in shifts)
    print(f"Alphabet: {kw:12s} | sc={cur_sc:.3f} | key={key_chars} | PT: {final_pt[:50]}...")
