import json
from collections import Counter
from buttcrack.ciphers.columnar import _decode_units

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
pk9 = cts['PK9']
M = _decode_units(pk9, [3, 5, 1, 4, 2, 0], unit=3)

ALPH_K = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
ALPH_S = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# English letter frequencies
eng_freq = {
    'A': 0.08167, 'B': 0.01492, 'C': 0.02782, 'D': 0.04253, 'E': 0.12702,
    'F': 0.02228, 'G': 0.02015, 'H': 0.06094, 'I': 0.06966, 'J': 0.00153,
    'K': 0.00772, 'L': 0.04025, 'M': 0.02406, 'N': 0.06749, 'O': 0.07507,
    'P': 0.01929, 'Q': 0.00095, 'R': 0.05987, 'S': 0.06327, 'T': 0.09056,
    'U': 0.02758, 'V': 0.00978, 'W': 0.02360, 'X': 0.00150, 'Y': 0.01974,
    'Z': 0.00074
}

def score_slice(slice_text, shift, alph, mode):
    # decrypt
    pt = []
    for ch in slice_text:
        ci = alph.index(ch)
        if mode == 'vigenere':
            pi = (ci - shift) % 26
        elif mode == 'beaufort':
            pi = (shift - ci) % 26
        elif mode == 'variant':
            pi = (ci + shift) % 26
        pt.append(alph[pi])
    
    # compute chi2 against English
    counts = Counter(pt)
    L = len(slice_text)
    chi = 0.0
    for ch, p in eng_freq.items():
        exp = L * p
        obs = counts.get(ch, 0)
        chi += (obs - exp) ** 2 / exp
    return chi, ''.join(pt)

for name, alph in [('KRYPTOS', ALPH_K), ('STANDARD', ALPH_S)]:
    for mode in ['vigenere', 'beaufort', 'variant']:
        print(f"\n==================== {name} | {mode} ====================")
        top_shifts = []
        for c in range(7):
            s = M[c::7]
            scores = []
            for shift in range(26):
                chi, pt = score_slice(s, shift, alph, mode)
                key_char = alph[shift]
                scores.append((chi, shift, key_char, pt))
            scores.sort()
            top_shifts.append([x[2] for x in scores[:4]])
            print(f"Col {c} top 4: " + ", ".join(f"{ch}(s={sh}, chi={chi:.1f})" for chi, sh, ch, pt in scores[:4]))
