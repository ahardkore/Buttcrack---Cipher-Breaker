import math
from collections import Counter

PK9 = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
N = len(PK9)

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
std_to_kr = {c: i for i, c in enumerate(ALPH)}
kr_to_std = {i: c for i, c in enumerate(ALPH)}

english_freq = {
    'A': 0.08167, 'B': 0.01492, 'C': 0.02782, 'D': 0.04253, 'E': 0.12702,
    'F': 0.02228, 'G': 0.02015, 'H': 0.06094, 'I': 0.06966, 'J': 0.00153,
    'K': 0.00772, 'L': 0.04025, 'M': 0.02406, 'N': 0.06749, 'O': 0.07507,
    'P': 0.01929, 'Q': 0.00095, 'R': 0.05987, 'S': 0.06327, 'T': 0.09056,
    'U': 0.02758, 'V': 0.00978, 'W': 0.02360, 'X': 0.00150, 'Y': 0.01974,
    'Z': 0.00074
}

q7 = [0, 2, 9, 23, 23, 6, 20]
print(f"Fixed q7: {q7}")

results = []

for x in range(26):
    q4 = [0, x, 11, (x + 3) % 26]
    
    # 28 shifts
    shifts = [(q4[s % 4] + q7[s % 7]) % 26 for s in range(28)]
    
    # Test all 4 modes
    for mode in range(4):
        counts = Counter()
        dec_chars = []
        for i, ch in enumerate(PK9):
            sh = shifts[i % 28]
            if mode == 0: # Vigenere Std
                p_val = (ord(ch) - ord('A') - sh) % 26
                p_chr = chr(ord('A') + p_val)
            elif mode == 1: # Beaufort Std
                p_val = (sh - (ord(ch) - ord('A'))) % 26
                p_chr = chr(ord('A') + p_val)
            elif mode == 2: # Vigenere Kr
                p_val = (std_to_kr[ch] - sh) % 26
                p_chr = ALPH[p_val]
            else: # Beaufort Kr
                p_val = (sh - std_to_kr[ch]) % 26
                p_chr = ALPH[p_val]
            dec_chars.append(p_chr)
            counts[p_chr] += 1
        
        chi2 = 0.0
        for ltr, exp_p in english_freq.items():
            obs = counts[ltr]
            exp = N * exp_p
            chi2 += (obs - exp)**2 / exp
        
        ll = sum(counts[ltr] * math.log(english_freq[ltr]) for ltr in english_freq)
        results.append((ll, chi2, mode, x, q4, "".join(dec_chars)))

results.sort(key=lambda item: item[0], reverse=True)

print("Top 10 Candidates (sorted by Log-Likelihood):")
m_names = ["Vig Std", "Bft Std", "Vig Kr", "Bft Kr"]
for ll, chi2, mode, x, q4, dec in results[:10]:
    print(f"LL: {ll:6.2f} | Chi2: {chi2:5.2f} | Mode: {m_names[mode]} | x={x:2d} | q4={q4}")
    print(f"  Z: {dec[:80]}...")
