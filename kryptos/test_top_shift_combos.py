import json, itertools
from buttcrack.engine import resolve_scorer
from buttcrack.ciphers.columnar import _decode_units

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
pk9 = cts['PK9']
M = _decode_units(pk9, [3, 5, 1, 4, 2, 0], unit=3)
scorer = resolve_scorer('quadgrams', 'english')

ALPH_K = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
ALPH_S = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# We can take the top 6 shifts per column for each configuration
from collections import Counter
eng_freq = {
    'A': 0.08167, 'B': 0.01492, 'C': 0.02782, 'D': 0.04253, 'E': 0.12702,
    'F': 0.02228, 'G': 0.02015, 'H': 0.06094, 'I': 0.06966, 'J': 0.00153,
    'K': 0.00772, 'L': 0.04025, 'M': 0.02406, 'N': 0.06749, 'O': 0.07507,
    'P': 0.01929, 'Q': 0.00095, 'R': 0.05987, 'S': 0.06327, 'T': 0.09056,
    'U': 0.02758, 'V': 0.00978, 'W': 0.02360, 'X': 0.00150, 'Y': 0.01974,
    'Z': 0.00074
}

def get_top_shifts(slice_text, alph, mode, top_k=6):
    scores = []
    for shift in range(26):
        pt = []
        for ch in slice_text:
            ci = alph.index(ch)
            if mode == 'vigenere': pi = (ci - shift) % 26
            elif mode == 'beaufort': pi = (shift - ci) % 26
            elif mode == 'variant': pi = (ci + shift) % 26
            pt.append(alph[pi])
        counts = Counter(pt)
        L = len(slice_text)
        chi = sum((counts.get(ch, 0) - L * p) ** 2 / (L * p) for ch, p in eng_freq.items())
        scores.append((chi, shift))
    scores.sort()
    return [s for chi, s in scores[:top_k]]

for a_name, alph in [('KRYPTOS', ALPH_K), ('STANDARD', ALPH_S)]:
    for mode in ['vigenere', 'beaufort', 'variant']:
        col_shifts = [get_top_shifts(M[c::7], alph, mode, top_k=5) for c in range(7)]
        total = 5**7
        print(f"Testing {a_name} | {mode} ({total} combos)...")
        best_sc = -999.0
        best_key = None
        best_pt = ""
        
        for shifts in itertools.product(*col_shifts):
            # decrypt M
            pt_chars = []
            for i, c in enumerate(M):
                ci = alph.index(c)
                sh = shifts[i % 7]
                if mode == 'vigenere': pi = (ci - sh) % 26
                elif mode == 'beaufort': pi = (sh - ci) % 26
                elif mode == 'variant': pi = (ci + sh) % 26
                pt_chars.append(alph[pi])
            pt = "".join(pt_chars)
            sc = scorer.average(pt)
            if sc > best_sc:
                best_sc = sc
                key_word = "".join(alph[s] for s in shifts)
                best_key = key_word
                best_pt = pt
                if sc > -5.8:
                    print(f"  [HIGH SCORE] {key_word} sc={sc:.3f} | {pt[:50]}...")
        
        print(f"  Best {a_name} | {mode}: key={best_key} sc={best_sc:.3f}\n  PT: {best_pt[:60]}...\n")
