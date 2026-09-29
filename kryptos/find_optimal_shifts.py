import json
from collections import Counter

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
pk9 = cts['PK9']
N = len(pk9)

ALPH_K = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
ALPH_STD = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

eng_freq = {
    'E': 0.1202, 'T': 0.0910, 'A': 0.0812, 'O': 0.0768, 'I': 0.0731, 'N': 0.0695,
    'S': 0.0628, 'R': 0.0602, 'H': 0.0592, 'D': 0.0432, 'L': 0.0398, 'U': 0.0288,
    'C': 0.0271, 'M': 0.0261, 'F': 0.0230, 'Y': 0.0211, 'W': 0.0209, 'G': 0.0203,
    'P': 0.0182, 'B': 0.0149, 'V': 0.0111, 'K': 0.0069, 'X': 0.0017, 'Q': 0.0011,
    'J': 0.0010, 'Z': 0.0007
}

def ioc(text):
    n = len(text)
    if n <= 1: return 0.0
    c = Counter(text)
    return sum(v*(v-1) for v in c.values()) / (n*(n-1))

def eng_fitness(text):
    n = len(text)
    c = Counter(text)
    return sum((c.get(ch, 0) / n) * eng_freq[ch] for ch in eng_freq)

def decrypt_periodic(ct, key_indices, alph):
    P = len(key_indices)
    return ''.join(alph[(alph.index(c) - key_indices[i % P]) % 26] for i, c in enumerate(ct))

for alph_name, alph in [('KRYPTOS', ALPH_K), ('STANDARD', ALPH_STD)]:
    for P in [7, 14, 28]:
        # For each column, find the best shift that correlates with English monograms
        best_shifts = []
        for j in range(P):
            col_chars = [pk9[i] for i in range(j, N, P)]
            best_k = 0
            best_dot = -1.0
            for k in range(26):
                dec_col = [alph[(alph.index(c) - k) % 26] for c in col_chars]
                c_cnt = Counter(dec_col)
                dot = sum(c_cnt.get(ch, 0) * eng_freq[ch] for ch in eng_freq)
                if dot > best_dot:
                    best_dot = dot
                    best_k = k
            best_shifts.append(best_k)
        
        Z = decrypt_periodic(pk9, best_shifts, alph)
        key_str = ''.join(alph[k] for k in best_shifts)
        print(f"[{alph_name}] Period {P:2d}: IoC={ioc(Z):.5f}, eng_dot={eng_fitness(Z):.5f}, key={key_str}")
        print(f"  Z: {Z[:60]}...")
