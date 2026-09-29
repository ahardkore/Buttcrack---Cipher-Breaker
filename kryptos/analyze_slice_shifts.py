KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"

# English letter frequencies
freq = {
    'E': 12.0, 'T': 9.1, 'A': 8.1, 'O': 7.7, 'I': 7.3, 'N': 7.0, 'S': 6.3,
    'H': 5.9, 'R': 5.9, 'D': 4.3, 'L': 4.0, 'C': 2.7, 'U': 2.9, 'M': 2.6,
    'W': 2.1, 'F': 2.2, 'G': 2.0, 'Y': 2.1, 'P': 1.8, 'B': 1.5, 'V': 1.0,
    'K': 0.8, 'X': 0.2, 'J': 0.15, 'Q': 0.1, 'Z': 0.07
}

print("Top 3 candidate shifts for each slice by English monogram frequency log-likelihood:")
import math
for k in range(28):
    sl = PK9_REAL[k::28]
    scores = []
    for s in range(26):
        # decrypt slice with shift s
        dec = "".join(KRYPTOS[(KRYPTOS.index(c) - s + 26) % 26] for c in sl)
        sc = sum(math.log(freq[c]) for c in dec)
        scores.append((sc, s, dec))
    scores.sort(reverse=True)
    top_str = " | ".join(f"s={s:2d}: {dec} ({sc:.1f})" for sc, s, dec in scores[:3])
    print(f"Slice {k:2d} ({sl:6s}): {top_str}")
