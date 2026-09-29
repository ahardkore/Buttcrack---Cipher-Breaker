import json, math

with open("pk_all_ciphertexts.json") as f:
    ct9 = json.load(f)["PK9"]

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
kr_to_num = {c: i for i, c in enumerate(KRYPTOS)}
num_to_kr = {i: c for i, c in enumerate(KRYPTOS)}

# English monogram log frequencies
freq = {
    'E': 12.02, 'T': 9.10, 'A': 8.12, 'O': 7.68, 'I': 7.31, 'N': 6.95, 'S': 6.28,
    'H': 6.02, 'R': 5.92, 'D': 4.32, 'L': 3.98, 'C': 2.71, 'U': 2.88, 'M': 2.61,
    'W': 2.09, 'F': 2.30, 'G': 2.03, 'Y': 2.11, 'P': 1.82, 'B': 1.49, 'V': 1.11,
    'K': 0.69, 'X': 0.17, 'J': 0.10, 'Q': 0.11, 'Z': 0.07
}
log_freq = {c: math.log(f) for c, f in freq.items()}

# Precompute slice characters as kryptos indices and standard indices
slices_kr = []
slices_std = []
for s in range(28):
    chars = ct9[s::28]
    slices_kr.append([kr_to_num[c] for c in chars])
    slices_std.append([ord(c) - 65 for c in chars])

def solve_system(mode_name, use_kryptos, is_beaufort):
    # Precompute score table: score_table[s][shift] = sum of log_freq for slice s shifted by shift
    score_table = [[0.0]*26 for _ in range(28)]
    slices = slices_kr if use_kryptos else slices_std
    num_map = num_to_kr if use_kryptos else {i: chr(i+65) for i in range(26)}
    
    for s in range(28):
        for sh in range(26):
            tot = 0.0
            for c_idx in slices[s]:
                if is_beaufort:
                    p_idx = (sh - c_idx + 26) % 26
                else: # Vigenere
                    p_idx = (c_idx - sh + 26) % 26
                ch = num_map[p_idx]
                tot += log_freq[ch]
            score_table[s][sh] = tot

    # Now for each of the 26^3 values of q4 = (0, q4_1, q4_2, q4_3):
    # For each j in 0..6:
    #   q7_j optimizes score_table[j][q4[j%4] + q7_j] + score_table[j+7][q4[(j+7)%4] + q7_j] + ...
    best_score = -1e9
    best_q4 = None
    best_q7 = None

    q4 = [0, 0, 0, 0]
    for q4_1 in range(26):
        q4[1] = q4_1
        for q4_2 in range(26):
            q4[2] = q4_2
            for q4_3 in range(26):
                q4[3] = q4_3
                
                total_score = 0.0
                cur_q7 = [0]*7
                for j in range(7):
                    # Find best q7_j
                    s_indices = [j, j+7, j+14, j+21]
                    best_j_score = -1e9
                    best_v = 0
                    for v in range(26):
                        sc = (score_table[s_indices[0]][(q4[s_indices[0] % 4] + v) % 26] +
                              score_table[s_indices[1]][(q4[s_indices[1] % 4] + v) % 26] +
                              score_table[s_indices[2]][(q4[s_indices[2] % 4] + v) % 26] +
                              score_table[s_indices[3]][(q4[s_indices[3] % 4] + v) % 26])
                        if sc > best_j_score:
                            best_j_score = sc
                            best_v = v
                    cur_q7[j] = best_v
                    total_score += best_j_score
                
                if total_score > best_score:
                    best_score = total_score
                    best_q4 = list(q4)
                    best_q7 = list(cur_q7)

    print(f"\nMode: {mode_name}")
    print(f"Best Monogram Score: {best_score:.2f} (avg per char: {best_score/144:.3f})")
    print(f"q4: {best_q4}")
    print(f"q7: {best_q7}")

    # Compute key of length 28
    k28 = [(best_q4[s % 4] + best_q7[s % 7]) % 26 for s in range(28)]
    print(f"k28: {k28}")

    # Decrypt the full 144 characters
    dec = []
    for i, c in enumerate(ct9):
        s = i % 28
        k = k28[s]
        if use_kryptos:
            c_idx = kr_to_num[c]
            p_idx = (k - c_idx + 26) % 26 if is_beaufort else (c_idx - k + 26) % 26
            dec.append(num_to_kr[p_idx])
        else:
            c_idx = ord(c) - 65
            p_idx = (k - c_idx + 26) % 26 if is_beaufort else (c_idx - k + 26) % 26
            dec.append(chr(p_idx + 65))
    dec_str = "".join(dec)
    print(f"Decrypted text (first 100): {dec_str[:100]}")
    
    # Calculate IoC of dec_str
    counts = {}
    for c in dec_str: counts[c] = counts.get(c, 0) + 1
    ioc = sum(v*(v-1) for v in counts.values()) / (144 * 143)
    print(f"Decrypted IoC: {ioc:.4f}")
    return dec_str, best_q4, best_q7

print("Starting Exact Global Optimization of (Q4, Q7)...")
solve_system("Kryptos Vigenere", use_kryptos=True, is_beaufort=False)
solve_system("Kryptos Beaufort", use_kryptos=True, is_beaufort=True)
solve_system("Standard Vigenere", use_kryptos=False, is_beaufort=False)
solve_system("Standard Beaufort", use_kryptos=False, is_beaufort=True)
