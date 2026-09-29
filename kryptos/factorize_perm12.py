import numpy as np

target = [3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10]
w = 12

def word_to_order(word):
    return [i for i, _ in sorted(enumerate(word), key=lambda x: x[1])]

# Load 12-letter words
words = []
with open("words_12.txt") as f:
    for line in f:
        w_str = line.strip().upper()
        if len(w_str) == w and w_str.isalpha():
            words.append((w_str, word_to_order(w_str)))

print(f"Loaded {len(words)} 12-letter words.")

# Precompute order to word mapping (many words share the same permutation order)
order_to_word = {}
for w_str, ord1 in words:
    t_ord = tuple(ord1)
    if t_ord not in order_to_word:
        order_to_word[t_ord] = w_str

unique_orders = list(order_to_word.keys())
print(f"Unique permutation orders: {len(unique_orders)}")

# For each unique order o1:
# We want o1 o o2 = target  =>  o2 = o1^-1 o target
# Check if o2 is in unique_orders!
hits = []
for o1 in unique_orders:
    # Compute inverse of o1
    inv_o1 = [0] * w
    for i in range(w): inv_o1[o1[i]] = i
    
    # o2 = inv_o1 o target: o2[i] = inv_o1[target[i]]
    o2 = tuple(inv_o1[target[i]] for i in range(w))
    if o2 in order_to_word:
        hits.append((order_to_word[o1], order_to_word[o2]))

print(f"Found {len(hits)} exact factorizations into two 12-letter words:")
for w1, w2 in hits[:20]:
    print(f"  {w1} o {w2}")
