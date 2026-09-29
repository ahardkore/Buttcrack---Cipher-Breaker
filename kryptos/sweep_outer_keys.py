import json

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
C = cts['PK9']
N = len(C)

ALPH_K = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
ALPH_S = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

def ioc(text):
    counts = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    total = len(text)
    return sum(v * (v - 1) for v in counts.values()) / (total * (total - 1))

# English letter frequencies
eng_freq = {
    'A': 0.08167, 'B': 0.01492, 'C': 0.02782, 'D': 0.04253, 'E': 0.12702,
    'F': 0.02228, 'G': 0.02015, 'H': 0.06094, 'I': 0.06966, 'J': 0.00153,
    'K': 0.00772, 'L': 0.04025, 'M': 0.02406, 'N': 0.06749, 'O': 0.07507,
    'P': 0.01929, 'Q': 0.00095, 'R': 0.05987, 'S': 0.06327, 'T': 0.09056,
    'U': 0.02758, 'V': 0.00978, 'W': 0.02360, 'X': 0.00150, 'Y': 0.01974,
    'Z': 0.00074
}

def chi2(text):
    counts = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    total = len(text)
    val = 0.0
    for ch, p in eng_freq.items():
        exp = total * p
        obs = counts.get(ch, 0)
        val += (obs - exp) ** 2 / exp
    return val

with open('/home/user/words_alpha.txt') as f:
    words = [line.strip().upper() for line in f if line.strip().isalpha()]

words_by_len = {}
for w in words:
    L = len(w)
    if L not in words_by_len: words_by_len[L] = []
    words_by_len[L].append(w)

print(f"Total words: {len(words)}")

for p in [7, 14, 6, 8, 9, 10, 12]:
    cands = words_by_len.get(p, [])
    print(f"\n--- Testing period {p}: {len(cands)} words ---")
    best_ic = 0.0
    best_chi = 9999.0
    best_w = None

    for w in cands:
        for alph_name, alph in [('KRYPTOS', ALPH_K), ('STANDARD', ALPH_S)]:
            # Vigenere / Quagmire
            pt = ''.join(alph[(alph.index(c) - alph.index(w[i % p])) % 26] for i, c in enumerate(C))
            ic = ioc(pt)
            if ic > best_ic:
                best_ic = ic
                best_w = (w, alph_name, 'Vig', ic)
                if ic > 0.058:
                    c2 = chi2(pt)
                    print(f"  [HIGH IOC] {w} ({alph_name} Vig): IoC={ic:.5f}, chi2={c2:.1f}")
            # Beaufort
            pt_b = ''.join(alph[(alph.index(w[i % p]) - alph.index(c)) % 26] for i, c in enumerate(C))
            ic_b = ioc(pt_b)
            if ic_b > best_ic:
                best_ic = ic_b
                best_w = (w, alph_name, 'Beau', ic_b)
                if ic_b > 0.058:
                    c2 = chi2(pt_b)
                    print(f"  [HIGH IOC] {w} ({alph_name} Beau): IoC={ic_b:.5f}, chi2={c2:.1f}")

    print(f"Period {p} best: {best_w}")
