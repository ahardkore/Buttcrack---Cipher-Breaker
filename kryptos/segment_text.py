# Load english dictionary
with open("theophilus_hendrie.txt") as f:
    theophilus_words = set(f.read().upper().split())

import re
clean_words = set()
for w in theophilus_words:
    cw = re.sub(r'[^A-Z]', '', w)
    if len(cw) >= 2:
        clean_words.add(cw)

# Also add common english words
for fname in ["words_4.txt", "words_7.txt", "words_12.txt"]:
    try:
        with open(fname) as f:
            for line in f:
                w = line.strip().upper()
                if len(w) >= 2:
                    clean_words.add(w)
    except:
        pass

print(f"Dictionary size: {len(clean_words)} words.")

pt = "EUARTOKIHHIIRYFMHOLADLAHWNPOOMEWLSASUMNTOANDEAUNHAMINSFORMISFARTWITCLNIAHOHEEAMACABATMIGENDTOENCTWEFDERETEDSTSELFFLADIFMOULTINOISOFTHEDGUSSHESOF"

# Word segmentation via dynamic programming
n = len(pt)
dp = [-99999.0] * (n + 1)
parent = [-1] * (n + 1)
dp[0] = 0.0

# Word cost: length^1.5 or dictionary match
for i in range(n):
    if dp[i] < -90000: continue
    # Try words of length 1 to 15
    for l in range(1, 16):
        if i + l <= n:
            w = pt[i:i+l]
            if w in clean_words or w in ["A", "I"]:
                score = l ** 1.3
            else:
                score = -2.0 * l # penalty for non-word
            if dp[i] + score > dp[i+l]:
                dp[i+l] = dp[i] + score
                parent[i+l] = i

# Reconstruct
idx = n
words = []
while idx > 0:
    p = parent[idx]
    words.append(pt[p:idx])
    idx = p
words.reverse()

print("\nWord segmentation:")
print(" ".join(words))
