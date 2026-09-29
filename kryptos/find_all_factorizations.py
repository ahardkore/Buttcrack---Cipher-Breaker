perm = [3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10]

def invert_perm(p):
    inv = [0] * len(p)
    for i, x in enumerate(p):
        inv[x] = i
    return inv

def argsort_stable(w):
    return sorted(range(len(w)), key=lambda i: (w[i], i))

with open("words_12.txt") as f:
    words = [line.strip().upper() for line in f if len(line.strip()) == 12]

# Map tuple(order) -> list of words
order_to_words = {}
for w in words:
    ord_w = tuple(argsort_stable(w))
    order_to_words.setdefault(ord_w, []).append(w)

print(f"Total words: {len(words)}, unique permutations: {len(order_to_words)}")

# Now for each W1 with order P1:
# If P = P1 o P2 (meaning P[i] = P1[P2[i]]):
# Then P2[i] = P1_inv[P[i]].
matches = []
for p1_tuple, w1_list in order_to_words.items():
    p1 = list(p1_tuple)
    p1_inv = invert_perm(p1)
    p2 = tuple(p1_inv[perm[i]] for i in range(12))
    if p2 in order_to_words:
        w2_list = order_to_words[p2]
        matches.append((w1_list[0], w2_list[0]))

print(f"\nFound {len(matches)} exact dictionary word-pair factorizations of perm:")
for w1, w2 in matches[:25]:
    print(f"  {w1}  o  {w2}")
