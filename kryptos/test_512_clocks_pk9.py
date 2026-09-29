import math
from collections import Counter

PK9 = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
N = len(PK9)

english_freq = {
    'A': 0.08167, 'B': 0.01492, 'C': 0.02782, 'D': 0.04253, 'E': 0.12702,
    'F': 0.02228, 'G': 0.02015, 'H': 0.06094, 'I': 0.06966, 'J': 0.00153,
    'K': 0.00772, 'L': 0.04025, 'M': 0.02406, 'N': 0.06749, 'O': 0.07507,
    'P': 0.01929, 'Q': 0.00095, 'R': 0.05987, 'S': 0.06327, 'T': 0.09056,
    'U': 0.02758, 'V': 0.00978, 'W': 0.02360, 'X': 0.00150, 'Y': 0.01974,
    'Z': 0.00074
}

# The confirmed mod-13 base vector
s13_base = [0, 2, 9, 10, 10, 6, 7]
C = [ALPH.index(c) for c in PK9]

# 8 choices for q4: [0, b1*13, b2*13, b3*13]
# 64 choices for q7: [0, 2 + m1*13, 9 + m2*13, 10 + m3*13, 10 + m4*13, 6 + m5*13, 7 + m6*13]
# Total = 8 * 64 = 512 clocks
# Plus global constant c in 0..25 (26 shifts)
# Plus 2 modes: Vigenere (C - K) and Beaufort (K - C)

results = []

for is_beau in [False, True]:
    for q4_idx in range(8):
        b1 = (q4_idx >> 2) & 1
        b2 = (q4_idx >> 1) & 1
        b3 = q4_idx & 1
        q4 = [0, b1 * 13, b2 * 13, b3 * 13]

        for q7_idx in range(64):
            m = [(q7_idx >> (5 - j)) & 1 for j in range(6)]
            q7 = [0] + [(s13_base[j+1] + m[j] * 13) % 26 for j in range(6)]

            # 28 shifts
            shifts = [(q4[s % 4] + q7[s % 7]) % 26 for s in range(28)]

            # Test global shift c in 0..25
            for c_glob in range(26):
                counts = {chr(ord('A') + i): 0 for i in range(26)}
                z_chars = []
                for t in range(N):
                    k = (shifts[t % 28] + c_glob) % 26
                    p = (k - C[t] + 26) % 26 if is_beau else (C[t] - k + 26) % 26
                    ch = ALPH[p]
                    counts[ch] += 1
                    z_chars.append(ch)

                rare = counts['Q'] + counts['X'] + counts['Z'] + counts['J']
                top9 = sum(counts[ch] for ch in "ETAOINSHR")

                chi2 = sum((counts[ch] - N * english_freq[ch])**2 / (N * english_freq[ch]) for ch in english_freq)
                ioc = sum(v * (v - 1) for v in counts.values()) / (N * (N - 1))

                results.append((chi2, rare, top9, ioc, is_beau, q4, q7, c_glob, "".join(z_chars)))

results.sort(key=lambda item: item[0])

print("Top 12 Clocks across all 512 * 26 * 2 = 26,624 states:")
for chi2, rare, top9, ioc, is_beau, q4, q7, c_glob, z_text in results[:12]:
    mode_str = "Beaufort" if is_beau else "Vigenere"
    print(f"Chi2={chi2:6.1f} | Rare={rare:2d} | Top9={top9:2d}/144 | IoC={ioc:.5f} | {mode_str} | c={c_glob:2d}")
    print(f"  q4={q4}")
    print(f"  q7={q7}")
    print(f"  Z: {z_text[:80]}...")
