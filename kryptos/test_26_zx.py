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

q7 = [0, 2, 9, 23, 23, 6, 20]
C = [ALPH.index(c) for c in PK9]

# Peel q7
Y = [(C[t] - q7[t % 7] + 26) % 26 for t in range(N)]

print("Sweeping x in 0..25 for q4 = [0, x, 11, (x+3)%26]:")
results = []
for x in range(26):
    q4 = [0, x, 11, (x + 3) % 26]
    Z = [(Y[t] - q4[t % 4] + 26) % 26 for t in range(N)]
    z_chars = [ALPH[v] for v in Z]
    
    # Monogram stats
    counts = {chr(ord('A') + i): 0 for i in range(26)}
    for ch in z_chars:
        counts[ch] += 1
        
    rare = counts['Q'] + counts['X'] + counts['Z'] + counts['J']
    top_ltrs = counts['E'] + counts['T'] + counts['A'] + counts['O'] + counts['I'] + counts['N'] + counts['S'] + counts['H'] + counts['R']
    
    chi2 = sum((counts[ch] - N * english_freq[ch])**2 / (N * english_freq[ch]) for ch in english_freq)
    ioc = sum(v * (v - 1) for v in counts.values()) / (N * (N - 1))
    
    results.append((chi2, rare, top_ltrs, ioc, x, "".join(z_chars)))

results.sort(key=lambda item: item[0])

for chi2, rare, top_ltrs, ioc, x, z_text in results[:10]:
    print(f"x={x:2d} | Chi2={chi2:6.1f} | Rare={rare:2d} | Top9={top_ltrs:2d}/144 | IoC={ioc:.5f}")
    print(f"  Z: {z_text[:80]}...")
