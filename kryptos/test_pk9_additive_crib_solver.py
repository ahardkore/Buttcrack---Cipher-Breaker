import numpy as np
import json
import re

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
kpos = {c: i for i, c in enumerate(ALPH)}
k2std = [ord(c) - ord('A') for c in ALPH]
std2k = {chr(ord('A') + k2std[i]): i for i in range(26)}

with open("pk_all_ciphertexts.json") as f:
    cts = json.load(f)

ct9_raw = cts["PK9"]
ct9_undone = cts["PK9_UNDONE"]

# English quadgram scorer
print("Loading quadgrams...")
floor = -9.5
quad = {}
with open("english_quads.tsv") as f:
    for line in f:
        q, sc = line.strip().split("\t")
        if len(q) == 4:
            quad[q] = float(sc)

def score_text(text):
    if len(text) < 4: return -99.0
    s = sum(quad.get(text[i:i+4], floor) for i in range(len(text) - 3))
    return s / (len(text) - 3)

def solve_system_mod(A, b, mod):
    # Gaussian elimination mod p
    M = np.hstack([A % mod, (np.array(b) % mod).reshape(-1, 1)])
    rows, cols = M.shape
    r = 0
    pivots = []
    for c in range(cols - 1):
        piv = None
        for i in range(r, rows):
            if M[i, c] % mod != 0:
                piv = i; break
        if piv is None: continue
        M[[r, piv]] = M[[piv, r]]
        inv = pow(int(M[r, c]), -1, mod) if mod > 2 else 1
        M[r] = (M[r] * inv) % mod
        for i in range(rows):
            if i != r and M[i, c] % mod != 0:
                factor = M[i, c] % mod
                M[i] = (M[i] - factor * M[r]) % mod
        pivots.append(c)
        r += 1
    # Check consistency
    for i in range(r, rows):
        if M[i, -1] % mod != 0:
            return None, None
    return M[:r], pivots

def solve_clocks_from_keystream(t_start, ks_chunk, clocks=[4, 7]):
    # Variables: q4[0..3], q7[0..6] (total 11 variables)
    # Gauge fixing: q4[0] = 0 (10 free variables)
    m = len(ks_chunk)
    A = np.zeros((m, 11), dtype=int)
    for i in range(m):
        t = t_start + i
        A[i, t % 4] = 1
        A[i, 4 + (t % 7)] = 1

    # Solve mod 2 and mod 13
    # With q4[0] = 0, add equation q4[0] = 0
    A_full = np.vstack([A, np.zeros((1, 11), dtype=int)])
    A_full[-1, 0] = 1
    b2 = list(np.array(ks_chunk) % 2) + [0]
    b13 = list(np.array(ks_chunk) % 13) + [0]

    M2, piv2 = solve_system_mod(A_full, b2, 2)
    if M2 is None: return None
    M13, piv13 = solve_system_mod(A_full, b13, 13)
    if M13 is None: return None

    # If both consistent, reconstruct full solution if fully determined
    if len(piv2) < 11 or len(piv13) < 11:
        # Not fully determined, return None for strict determination
        return None

    # Solution vector
    x2 = np.zeros(11, dtype=int)
    for r in range(len(piv2)):
        c = piv2[r]
        x2[c] = M2[r, -1] % 2

    x13 = np.zeros(11, dtype=int)
    for r in range(len(piv13)):
        c = piv13[r]
        x13[c] = M13[r, -1] % 13

    # CRT combine: x = x13 + 13 * ((x2 - x13) * inv(13, 2) % 2)
    x = np.zeros(11, dtype=int)
    for i in range(11):
        x[i] = (x13[i] + 13 * ((x2[i] - x13[i]) % 2)) % 26

    q4 = x[:4]
    q7 = x[4:]
    return q4, q7

# Generate thematic candidate craft cribs
candidate_phrases = [
    "ATLASTTHEFIREWASLIT",
    "THEBELLOWSSANGAS",
    "THECOALSTURNEDWHITE",
    "WITHLONGTONGSHEHELD",
    "HEHELDTHESTEELINTO",
    "HEHELDTHESILVERINTO",
    "INTOTHEWHITECOALS",
    "ONEMOMENTOFTEMPERING",
    "CANDESTROYYEARSOF",
    "DESTROYYEARSOFLABOUR",
    "HEPOINTEDTOTHEHEARTH",
    "STRIKINGTHEANVIL",
    "STRIKINGTHESILVER",
    "THEMASTERTOOKTHE",
    "THEMASTERHELDTHE",
    "DRAWINGTHEWIRETHROUGH",
    "THROUGHTHEDRAWPLATE",
    "ANDQUENCHEDINIT",
    "ANDQUENCHEDINWATER",
    "QUENCHEDITINWATER",
    "QUENCHEDTHESTEEL",
    "QUENCHEDTHESILVER",
    "HEHEATEDTHESTEEL",
    "HEHEATEDTHESILVER",
    "TEMPEREDINWATER",
    "TEMPERINGTHESILVER",
    "TEMPERINGTHENEEDLE",
    "FORGINGTHENEEDLE",
    "MAKINGTHENEEDLE",
    "THEEYEOFTHENEEDLE",
    "THEPOINTOFTHENEEDLE",
    "THEPOINTOFTHESTEEL",
    "SLENDERANDSHARP",
    "FINEANDSLENDER",
    "SLENDERTOWARDSTHEPOINT",
    "TOWARDSTHEPOINT",
    "WITHACHARCOALFIRE",
    "UPONTHEANVILWITH",
    "WITHTHESMALLHAMMER",
    "WITHTHEIRONHAMMER",
    "UNDERTHEHAMMER",
    "THEMETALTURNEDWHITE",
    "UNTILITGLOWEDWHITE",
    "WHENITGLOWEDWHITE",
    "INTHEBELLOWSBLAST",
    "WITHHEAVYTONGS",
    "HEPLACEDITUPON",
    "HELAIDITUPONTHE",
    "HELAIDITONTHEANVIL",
    "ANDBEATITSLENDER",
    "BEATENSLENDERAND",
    "ANDFILETHESURFACE",
    "ANDFILETHESIDES",
    "ANDFILEDTHESIDES",
    "ANDFILEDTHEPOINT",
    "WITHTHESHARPFILE",
    "THEWORKCOULDONLYBEGIN",
    "WHENTHEFIREREACHED",
    "ITSPROPERHEATWITH",
    "ITSREQUIREDHEAT",
    "THECRAFTREQUIRES",
    "YEARSOFPRACTICE",
    "YEARSOFLABOURAND",
    "THEARCHIVEOFPELLEGRIN",
    "THEARCHIVEISOPENED",
    "THEFINALMASTERPIECE",
    "THEUNRAVELLINGOF",
    "ONCEUNRAVELEDIT",
    "UNRAVELEDITREVEALS",
    "THEREALOBJECTANEEDLE",
    "ANEEDLEFINEANDSHARP",
    "ANEEDLEOFPURESILVER",
    "OFPURESTEELANDSILVER",
    "APUNCHEONOFSTEEL",
    "ANDPIERCETHEEYE",
    "PIERCINGTHEEYEWITH",
    "PIERCEDWITHASMALL",
    "ASMALLHOLEFORTHE"
]

print(f"Loaded {len(candidate_phrases)} candidate craft cribs.")

for label, ct in [("PK9_UNDONE", ct9_undone), ("PK9_RAW", ct9_raw)]:
    print(f"\n{'='*70}\nTesting crib dragging on {label}...\n{'='*70}")
    best_overall = (-999.0, "", "", "", "")

    for phrase in candidate_phrases:
        clean_p = "".join(c for c in phrase.upper() if c in ALPH)
        L = len(clean_p)
        if L < 12: continue

        for pos in range(len(ct) - L + 1):
            ct_chunk = ct[pos : pos + L]

            # Quagmire III keystream: C_kr - P_kr mod 26
            ks_kr = [(kpos[ct_chunk[i]] - kpos[clean_p[i]]) % 26 for i in range(L)]
            res = solve_clocks_from_keystream(pos, ks_kr, [4, 7])
            if res is not None:
                q4, q7 = res
                # Decrypt full text
                full_pt = []
                for t in range(len(ct)):
                    ks = (q4[t % 4] + q7[t % 7]) % 26
                    p_kr = (kpos[ct[t]] - ks) % 26
                    full_pt.append(chr(ord('A') + k2std[p_kr]))
                pt_str = "".join(full_pt)
                sc = score_text(pt_str)
                if sc > best_overall[0]:
                    best_overall = (sc, clean_p, pos, pt_str, f"q4={list(q4)}, q7={list(q7)}")
                    if sc > -6.0:
                        print(f"*** HIT! Score={sc:.4f} | Crib='{clean_p}' at pos {pos} ***")
                        print(f"  PT: {pt_str}")
                        print(f"  Clocks: {best_overall[4]}")

    print(f"Best score on {label}: {best_overall[0]:.4f} with crib '{best_overall[1]}' at pos {best_overall[2]}")
    if best_overall[3]:
        print(f"  PT: {best_overall[3][:80]}...")
