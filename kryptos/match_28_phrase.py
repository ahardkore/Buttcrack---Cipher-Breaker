KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
shifts = [5, 4, 9, 15, 16, 5, 6, 14, 5, 25, 20, 21, 10, 6, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3]

# In Quagmire III:
# shift[i] = (key_kr[i] - pt_indicator_kr) % 26
# or shift[i] is the position of key character on KRYPTOS!
# Let us check:
k_key = "".join(KRYPTOS[s] for s in shifts)
std_key = "".join(chr(65 + s) for s in shifts)

print(f"Direct KRYPTOS key:  {k_key}")
print(f"Direct STANDARD key: {std_key}")

# What if key is shifted by a constant c (0..25)?
with open("theophilus_hendrie.txt") as f:
    raw = f.read().upper()

import re
clean = re.sub(r'[^A-Z]', '', raw)
print(f"Theophilus text clean length: {len(clean)}")

# Search for any 28-character window in clean text whose KRYPTOS or STANDARD shifts
# correlate strongly with our 28 shifts!
best_corr = 0
best_pos = -1
best_text = ""

for i in range(len(clean) - 28):
    win = clean[i:i+28]
    # Check KRYPTOS shifts
    win_k = [KRYPTOS.index(c) for c in win]
    # Check correlation: count how many match up to a constant shift c
    for c in range(26):
        matches = sum(1 for j in range(28) if (win_k[j] - c) % 26 == shifts[j])
        if matches > best_corr:
            best_corr = matches
            best_pos = i
            best_text = win
            print(f"Pos {i}: {matches}/28 matches (c={c}) | text: {win}")

    # Check STANDARD shifts
    win_std = [ord(ch) - 65 for ch in win]
    for c in range(26):
        matches = sum(1 for j in range(28) if (win_std[j] - c) % 26 == shifts[j])
        if matches > best_corr:
            best_corr = matches
            best_pos = i
            best_text = win
            print(f"Pos {i} (std): {matches}/28 matches (c={c}) | text: {win}")

print(f"\nBest match: {best_corr}/28")
