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

for mode_name, is_kryptos, is_beaufort in [
    ("Standard Vigenere", False, False),
    ("Standard Beaufort", False, True),
    ("Kryptos Vigenere", True, False),
    ("Kryptos Beaufort", True, True)
]:
    print(f"\n==========================================")
    print(f"--- Mode: {mode_name} ---")
    print(f"==========================================")
    
    best_key = []
    total_chi2 = 0.0
    
    for s in range(7):
        slice_chars = [PK9[i] for i in range(s, N, 7)]
        best_sh = 0
        best_chi2 = 1e9
        
        for sh in range(26):
            dec_chars = []
            for ch in slice_chars:
                if not is_kryptos:
                    c_val = ord(ch) - ord('A')
                    if not is_beaufort:
                        p_val = (c_val - sh) % 26
                    else:
                        p_val = (sh - c_val) % 26
                    dec_chars.append(chr(ord('A') + p_val))
                else:
                    c_val = std_to_kr[ch]
                    if not is_beaufort:
                        p_val = (c_val - sh) % 26
                    else:
                        p_val = (sh - c_val) % 26
                    dec_chars.append(ALPH[p_val])
            
            # Compute chi2 vs English
            counts = Counter(dec_chars)
            chi2 = 0.0
            n_s = len(slice_chars)
            for ltr, exp_p in english_freq.items():
                obs = counts[ltr]
                exp = n_s * exp_p
                chi2 += (obs - exp)**2 / exp
            
            if chi2 < best_chi2:
                best_chi2 = chi2
                best_sh = sh
        
        best_key.append(best_sh)
        total_chi2 += best_chi2
        
        key_char = chr(ord('A') + best_sh) if not is_kryptos else ALPH[best_sh]
        print(f"Slice {s} (len {len(slice_chars)}): Best shift = {best_sh:2d} ('{key_char}') with Chi2 = {best_chi2:.2f}")
    
    key_str = "".join(chr(ord('A') + k) if not is_kryptos else ALPH[k] for k in best_key)
    print(f"Full 7-key: {best_key} -> '{key_str}' | Total Chi2 = {total_chi2:.2f}")
    
    # Decrypt with this 7-key
    full_dec = []
    for i, ch in enumerate(PK9):
        sh = best_key[i % 7]
        if not is_kryptos:
            c_val = ord(ch) - ord('A')
            p_val = (c_val - sh) % 26 if not is_beaufort else (sh - c_val) % 26
            full_dec.append(chr(ord('A') + p_val))
        else:
            c_val = std_to_kr[ch]
            p_val = (c_val - sh) % 26 if not is_beaufort else (sh - c_val) % 26
            full_dec.append(ALPH[p_val])
    
    dec_text = "".join(full_dec)
    print(f"Decrypted text Z (len {len(dec_text)}):")
    print(dec_text)
