import json
from collections import Counter

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
pk9 = cts['PK9']
N = len(pk9)

ALPH = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
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
    # compute log likelihood or dot product with English monogram frequencies
    n = len(text)
    c = Counter(text)
    dot = sum((c.get(ch, 0) / n) * eng_freq[ch] for ch in eng_freq)
    return dot

print(f"PK9 raw C: len={N}, IoC={ioc(pk9):.5f}, eng_dot={eng_fitness(pk9):.5f}")

# For a periodic key of period P, each coset can be shifted independently!
# To maximize the monogram IoC and English fitness of the ENTIRE decrypted text Z:
# If each coset j is decrypted with shift k_j:
# Can we choose (k_0, ..., k_{P-1}) to maximize the monogram IoC of the combined text Z?
