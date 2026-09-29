import math

PK9 = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
N = len(PK9)
ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

english_freq = {
    'A': 0.08167, 'B': 0.01492, 'C': 0.02782, 'D': 0.04253, 'E': 0.12702,
    'F': 0.02228, 'G': 0.02015, 'H': 0.06094, 'I': 0.06966, 'J': 0.00153,
    'K': 0.00772, 'L': 0.04025, 'M': 0.02406, 'N': 0.06749, 'O': 0.07507,
    'P': 0.01929, 'Q': 0.00095, 'R': 0.05987, 'S': 0.06327, 'T': 0.09056,
    'U': 0.02758, 'V': 0.00978, 'W': 0.02360, 'X': 0.00150, 'Y': 0.01974,
    'Z': 0.00074
}

q7_base = [0, 2, 9, 23, 23, 6, 20]

# We will sweep:
# x in 0..25 (the free parameter in q4 = [0, x, 11, (x+3)%26])
# c_global in 0..25 (global Caesar shift)
# And 2 alphabets: Kryptos alphabet and Standard alphabet
# And 2 modes: Vigenere (C - K) and Beaufort (K - C)

results = []

for alph_name, alph in [("Kryptos", ALPH), ("Standard", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")]:
    C = [alph.index(ch) for ch in PK9]
    for mode in ["Vigenere", "Beaufort"]:
        for x in range(26):
            q4 = [0, x, 11, (x + 3) % 26]
            for c_glob in range(26):
                # 28 shifts
                shifts = [(q4[s % 4] + q7_base[s % 7] + c_glob) % 26 for s in range(28)]
                
                # Decrypt C to Z
                counts = {chr(ord('A') + i): 0 for i in range(26)}
                z_chars = []
                for t in range(N):
                    k = shifts[t % 28]
                    if mode == "Vigenere":
                        p_val = (C[t] - k + 26) % 26
                    else:
                        p_val = (k - C[t] + 26) % 26
                    ch = alph[p_val]
                    counts[ch] += 1
                    z_chars.append(ch)
                
                # Calculate IoC
                ioc = sum(v * (v - 1) for v in counts.values()) / (N * (N - 1))
                
                # Calculate Chi-squared against English
                chi2 = 0.0
                ll = 0.0
                for ch, exp_p in english_freq.items():
                    obs = counts[ch]
                    exp = N * exp_p
                    chi2 += (obs - exp)**2 / exp
                    ll += obs * math.log(exp_p)
                
                results.append((chi2, ll, ioc, alph_name, mode, x, c_glob, "".join(z_chars), counts))

results.sort(key=lambda r: r[0]) # sort by Chi2 (lower is better)

print("Top 15 Intermediate texts Z (sorted by Chi-squared against English):")
for chi2, ll, ioc, alph_name, mode, x, c_glob, z_text, counts in results[:15]:
    top_ltrs = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:6]
    top_str = " ".join(f"{k}:{v}" for k, v in top_ltrs)
    rare_str = f"Q:{counts['Q']} X:{counts['X']} Z:{counts['Z']} J:{counts['J']}"
    print(f"Chi2: {chi2:6.1f} | LL: {ll:6.1f} | IoC: {ioc:.5f} | {alph_name} {mode} | x={x:2d}, c={c_glob:2d}")
    print(f"   Top: {top_str} | Rare: {rare_str}")
    print(f"   Z: {z_text[:70]}...")
