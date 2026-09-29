import time

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
kpos = {c: i for i, c in enumerate(ALPH)}
k2std = [ord(c) - ord('A') for c in ALPH]

PK9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
N = 144

# Load Theophilus words
with open("theophilus_w4.txt") as f:
    words4 = [w.strip().upper() for w in f if len(w.strip()) == 4 and w.strip().isalpha()]

with open("theophilus_w7.txt") as f:
    words7 = [w.strip().upper() for w in f if len(w.strip()) == 7 and w.strip().isalpha()]

print(f"Loaded {len(words4)} 4-letter words and {len(words7)} 7-letter words.")

# Target unigram profile of Z:
# We know the unigram shifts that produce IoC = 0.08838:
target_shifts = [15, 10, 13, 17, 17, 5, 6, 10, 5, 3, 11, 21, 14, 7, 10, 10, 7, 10, 7, 6, 21, 0, 18, 5, 15, 10, 13, 3]

best_match = 0
best_pair = None
t0 = time.time()

for w4 in words4:
    q4 = [kpos[c] for c in w4]
    for w7 in words7:
        q7 = [kpos[c] for c in w7]
        matches = 0
        for t in range(28):
            s = (q4[t % 4] + q7[t % 7]) % 26
            if s == target_shifts[t]:
                matches += 1
        if matches > best_match:
            best_match = matches
            best_pair = (w4, w7)

elapsed = time.time() - t0
print(f"Evaluated {len(words4)*len(words7)} pairs in {elapsed:.2f}s.")
print(f"Best match to unigram shifts: {best_match}/28 matches | Pair: {best_pair}")
