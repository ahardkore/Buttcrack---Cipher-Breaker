import math
from collections import Counter

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

for alph_name, alph in [("Kryptos", ALPH), ("Standard", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")]:
    C = [alph.index(c) for c in PK9]
    for mode in ["Vigenere", "Beaufort"]:
        best_shifts = []
        for s in range(28):
            slice_chars = [C[i] for i in range(s, N, 28)]
            best_sh = 0
            best_ll = -1e9
            for sh in range(26):
                ll = 0
                for c_val in slice_chars:
                    if mode == "Vigenere":
                        p_val = (c_val - sh + 26) % 26
                    else:
                        p_val = (sh - c_val + 26) % 26
                    ch = alph[p_val]
                    ll += math.log(english_freq[ch])
                if ll > best_ll:
                    best_ll = ll
                    best_sh = sh
            best_shifts.append(best_sh)
        
        # Now decrypt with best_shifts
        dec = []
        for i in range(N):
            sh = best_shifts[i % 28]
            if mode == "Vigenere":
                p_val = (C[i] - sh + 26) % 26
            else:
                p_val = (sh - C[i] + 26) % 26
            dec.append(alph[p_val])
        dec_str = "".join(dec)
        
        # Check IoC of dec_str
        cnts = Counter(dec_str)
        ioc = sum(v * (v - 1) for v in cnts.values()) / (N * (N - 1))
        
        print(f"=== {alph_name} {mode} ===")
        print(f"Optimal 28 shifts: {best_shifts}")
        print(f"IoC of decrypted Z: {ioc:.5f}")
        
        # Test if best_shifts decomposes into p4 + p7
        # We can check factorise_sumclock!
        # Let us see if best_shifts satisfies sumclock conditions!
