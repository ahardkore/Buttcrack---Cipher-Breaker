import re

perm = [3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10]
def invert_perm(p):
    inv = [0] * len(p)
    for i, x in enumerate(p):
        inv[x] = i
    return inv
inv_perm = invert_perm(perm)

def argsort_stable(w):
    return sorted(range(len(w)), key=lambda i: (w[i], i))

all_words = set()
for fn in ["/usr/share/dict/words", "theophilus_hendrie.txt"]:
    try:
        with open(fn) as f:
            for line in f:
                for w in re.findall(r'[a-zA-Z]+', line):
                    if len(w) == 12:
                        all_words.add(w.upper())
    except:
        pass

print(f"Total 12-letter candidate words: {len(all_words)}")
matches_p = [w for w in all_words if argsort_stable(w) == perm]
matches_inv = [w for w in all_words if argsort_stable(w) == inv_perm]

print("Matches perm:", matches_p)
print("Matches inv_perm:", matches_inv)
