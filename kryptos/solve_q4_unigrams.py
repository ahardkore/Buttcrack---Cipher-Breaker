# Exact 104-Test Unigram Solver for Q4 on Decoupled Stream Y
import math
from collections import Counter

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY"
N = len(PK8_CT)
ct = [KRYPTOS.index(c) for c in PK8_CT]

q5 = [0, 25, 12, 5, 18]       # from Stride 84
q6 = [0, 0, 8, 17, 10, 18]    # from Stride 140
q7 = [0, 19, 5, 9, 12, 4, 4]  # from Stride 60

# Decoupled stream Y:
Y = [(ct[t] - (q5[t % 5] + q6[t % 6] + q7[t % 7]) + 52) % 26 for t in range(N)]

eng_freq = {
    "A": 0.08167, "B": 0.01492, "C": 0.02782, "D": 0.04253, "E": 0.12702,
    "F": 0.02228, "G": 0.02015, "H": 0.06094, "I": 0.06966, "J": 0.00153,
    "K": 0.00772, "L": 0.04025, "M": 0.02406, "N": 0.06749, "O": 0.07507,
    "P": 0.01929, "Q": 0.00095, "R": 0.05987, "S": 0.06327, "T": 0.09056,
    "U": 0.02758, "V": 0.00978, "W": 0.02360, "X": 0.00150, "Y": 0.01974,
    "Z": 0.00074
}

log_freq_kr = [math.log(eng_freq[KRYPTOS[i]]) for i in range(26)]

print("==========================================================================================")
print("             SOLVING Q4 VIA INDEPENDENT UNIGRAM SLICE PROJECTION                          ")
print("==========================================================================================\n")

best_q4 = []
for p in range(4):
    slice_Y = [Y[t] for t in range(p, N, 4)]
    best_s = 0
    best_ll = -1e9
    for s in range(26):
        # pt = (y - s) mod 26
        ll = sum(log_freq_kr[(y - s + 26) % 26] for y in slice_Y)
        if ll > best_ll:
            best_ll = ll
            best_s = s
    best_q4.append(best_s)
    # compute IoC with best_s
    pt_slice = [KRYPTOS[(y - best_s + 26) % 26] for y in slice_Y]
    c = Counter(pt_slice)
    ioc = sum(v*(v-1) for v in c.values()) / (len(pt_slice)*(len(pt_slice)-1))
    print(f"Slice {p}: Optimal shift = {best_s:2d} (Kryptos '{KRYPTOS[best_s]}') | Slice IoC = {ioc:.5f} | LL = {best_ll:.2f}")

print(f"\nOptimal Q4 Vector: {best_q4}")
print(f"Q4 Letters in Kryptos: {''.join(KRYPTOS[s] for s in best_q4)}")

# Decrypt full plaintext
pt_full = []
for t in range(N):
    pt_idx = (Y[t] - best_q4[t % 4] + 26) % 26
    pt_full.append(KRYPTOS[pt_idx])

pt_str = "".join(pt_full)
print(f"\nFull Decrypted PK8 Plaintext (N = {N}):\n{pt_str}\n")

# Compute metrics
c_full = Counter(pt_str)
ioc_full = sum(v*(v-1) for v in c_full.values()) / (N * (N - 1))
rare = sum(c_full[ch] for ch in "JQXZ")
print(f"Overall Monogram IoC: {ioc_full:.5f}")
print(f"Rare Letters (J,Q,X,Z): {rare} / {N} ({rare/N*100:.2f}%)")

# Quadgram score:
qtable = {}
with open("english_quads.tsv") as f:
    for line in f:
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 4:
            qtable[parts[0]] = float(parts[1])

sc = sum(qtable.get(pt_str[i:i+4], -9.5) for i in range(N-3)) / (N-3)
defs = sum(1 for i in range(N-3) if pt_str[i:i+4] not in qtable)
print(f"Quadgram Score: {sc:.4f} | Valid Quadgrams: {N-3-defs} / {N-3} ({(N-3-defs)/(N-3)*100:.1f}%)")

# Word search
words = set()
with open("all_words.txt") as f:
    for line in f:
        w = line.strip().upper()
        if len(w) >= 3 and w.isalpha(): words.add(w)

found = []
for L in range(3, 10):
    for i in range(N - L + 1):
        sub = pt_str[i:i+L]
        if sub in words: found.append((i, L, sub))

found.sort(key=lambda x: (x[0], -x[1]))
print(f"\nEnglish Words Found in Plaintext ({len(found)} words):")
for pos, L, sub in found[:25]:
    surround = pt_str[max(0, pos-3):min(N, pos+L+3)]
    print(f"  Pos {pos:3d}: [{sub:8s}] in ...{surround}...")
