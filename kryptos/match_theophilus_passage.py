with open("theophilus_hendrie.txt") as f:
    text = f.read()

import re
clean = re.sub(r'[^A-Z]', '', text.upper())

# Let's count letter frequencies in our PK9 rows 0..11
target = "EUARTOKIHHIIRYFMHOLADLAHWNPOOMEWLSASUMNTOPNDEAUNHAMINSFORMISFARTWITCLNIAHOHEEAMACABATHIGENDTOANCTWEFDERETEDSTSELFFLADIFMOULTINOISOFTHEDCUSSHASOF"

from collections import Counter
target_c = Counter(target)

print("Target length:", len(target))
print("Target letter counts:", sorted(target_c.items()))

# Now scan clean text with window 144 to find if there's an exact or near-exact match
best_diff = 999
best_pos = -1

for i in range(0, len(clean) - 144, 1):
    win = clean[i:i+144]
    win_c = Counter(win)
    diff = sum(abs(target_c[ch] - win_c[ch]) for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    if diff < best_diff:
        best_diff = diff
        best_pos = i
        print(f"Pos {i}: diff = {diff} | {win[:40]}...")

print(f"\nBest match diff: {best_diff}")
if best_pos >= 0:
    print("Passage:", clean[best_pos:best_pos+144])
