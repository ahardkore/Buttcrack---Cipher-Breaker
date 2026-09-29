perm = [3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10]

# Compute rank of perm:
# The alphabetical rank of word w: order = argsort(w)
# If perm is the readout order: order == perm
# If perm is the write-in order: inv_perm == argsort(w)

def argsort(w):
    return sorted(range(len(w)), key=lambda i: (w[i], i))

def invert_perm(p):
    inv = [0] * len(p)
    for i, x in enumerate(p):
        inv[x] = i
    return inv

inv_perm = invert_perm(perm)
print(f"Perm:     {perm}")
print(f"Inv Perm: {inv_perm}")

with open("words_12.txt") as f:
    words = [line.strip().upper() for line in f if len(line.strip()) == 12]

print(f"Loaded {len(words)} 12-letter words.")

matches_perm = []
matches_inv = []

for w in words:
    rk = argsort(w)
    if rk == perm:
        matches_perm.append(w)
    if rk == inv_perm:
        matches_inv.append(w)

print(f"Direct matches ({len(matches_perm)}): {matches_perm[:10]}")
print(f"Inverse matches ({len(matches_inv)}): {matches_inv[:10]}")
