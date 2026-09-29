import time, math
from collections import Counter

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
kpos = {c: i for i, c in enumerate(ALPH)}
k2std = [ord(c) - ord('A') for c in ALPH]

PK9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
N = 144
ct_kr = [kpos[c] for c in PK9_RAW]

# Load English unigrams
# English letter probabilities:
eng_freq = {
    'E': 0.12702, 'T': 0.09056, 'A': 0.08167, 'O': 0.07507, 'I': 0.06966, 'N': 0.06749,
    'S': 0.06327, 'H': 0.06094, 'R': 0.05987, 'D': 0.04253, 'L': 0.04025, 'C': 0.02782,
    'U': 0.02758, 'M': 0.02406, 'W': 0.02360, 'F': 0.02228, 'G': 0.02015, 'Y': 0.01974,
    'P': 0.01929, 'B': 0.01492, 'V': 0.00978, 'K': 0.00772, 'J': 0.00153, 'X': 0.00150,
    'Q': 0.00095, 'Z': 0.00074
}
log_eng = [math.log(eng_freq[chr(65+i)]) for i in range(26)]

with open("theophilus_w4.txt") as f:
    words4 = [w.strip().upper() for w in f if len(w.strip()) == 4 and w.strip().isalpha()]

with open("theophilus_w7.txt") as f:
    words7 = [w.strip().upper() for w in f if len(w.strip()) == 7 and w.strip().isalpha()]

print(f"Loaded {len(words4)} 4-letter words and {len(words7)} 7-letter words.")

best_ll = -999999.0
best_pair = None
best_ioc = 0.0

t0 = time.time()
tested = 0

for w4 in words4:
    q4 = [kpos[c] for c in w4]
    for w7 in words7:
        q7 = [kpos[c] for c in w7]
        ll = 0.0
        counts = [0] * 26
        for t in range(N):
            s = (q4[t % 4] + q7[t % 7]) % 26
            p_kr = (ct_kr[t] - s + 26) % 26
            p_std = k2std[p_kr]
            counts[p_std] += 1
            ll += log_eng[p_std]
        
        tested += 1
        if ll > best_ll:
            best_ll = ll
            best_pair = (w4, w7)
            # Compute IoC
            best_ioc = sum(c * (c - 1) for c in counts) / (N * (N - 1))

elapsed = time.time() - t0
print(f"Tested {tested} pairs in {elapsed:.2f}s ({tested/elapsed:.0f} pairs/sec).")
print(f"Best LL: {best_ll:.2f} | IoC: {best_ioc:.5f} | Words: {best_pair}")

# Print letter distribution of best pair
q4 = [kpos[c] for c in best_pair[0]]
q7 = [kpos[c] for c in best_pair[1]]
z = []
for t in range(N):
    s = (q4[t % 4] + q7[t % 7]) % 26
    p_kr = (ct_kr[t] - s + 26) % 26
    z.append(chr(65 + k2std[p_kr]))
z = "".join(z)
print("Decrypted Z:")
print(z)
counts = Counter(z)
print("Top letters:", counts.most_common(8))
