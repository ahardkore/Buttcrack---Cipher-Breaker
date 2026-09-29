KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

def word_to_shifts(w):
    return [KRYPTOS.index(c) for c in w]

def word_to_std_shifts(w):
    return [ord(c) - 65 for c in w]

# Our Q4 candidates:
# Q4 = [0, 18, 13, 9] (relative shifts: [0, 18, 13, 9])
# Q7 = [5, 5, 7, 7, 16, 13, 19]

with open("words_4.txt") as f:
    words4 = [line.strip().upper() for line in f if len(line.strip()) == 4]

with open("words_7.txt") as f:
    words7 = [line.strip().upper() for line in f if len(line.strip()) == 7]

print(f"Loaded {len(words4)} 4-letter words and {len(words7)} 7-letter words.")

# Check for Q4 matches up to a constant shift c
q4_cand = [0, 18, 13, 9]
q4_rel = [(q4_cand[i] - q4_cand[0]) % 26 for i in range(4)]

matching_w4 = []
for w in words4:
    sh = word_to_shifts(w)
    rel = [(sh[i] - sh[0]) % 26 for i in range(4)]
    if rel == q4_rel:
        matching_w4.append((w, "KRYPTOS"))
    sh_std = word_to_std_shifts(w)
    rel_std = [(sh_std[i] - sh_std[0]) % 26 for i in range(4)]
    if rel_std == q4_rel:
        matching_w4.append((w, "STANDARD"))

print(f"Matching 4-letter words for Q4 {q4_rel}: {matching_w4}")

# Check Q7 matches
q7_cand = [5, 5, 7, 7, 16, 13, 19]
q7_rel = [(q7_cand[i] - q7_cand[0]) % 26 for i in range(7)]
print(f"Q7 relative shifts: {q7_rel}")

matching_w7 = []
for w in words7:
    sh = word_to_shifts(w)
    rel = [(sh[i] - sh[0]) % 26 for i in range(7)]
    if rel == q7_rel:
        matching_w7.append((w, "KRYPTOS"))
    sh_std = word_to_std_shifts(w)
    rel_std = [(sh_std[i] - sh_std[0]) % 26 for i in range(7)]
    if rel_std == q7_rel:
        matching_w7.append((w, "STANDARD"))

print(f"Matching 7-letter words for Q7 {q7_rel}: {matching_w7}")
