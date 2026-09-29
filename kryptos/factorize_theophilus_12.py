import re

perm = [3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10]

def argsort_stable(w):
    return sorted(range(len(w)), key=lambda i: (w[i], i))

# Load all words from theophilus_hendrie.txt and curated list
with open("theophilus_hendrie.txt") as f:
    text = f.read().upper()

words = set(w for w in re.findall(r'[A-Z]+', text) if len(w) == 12)
print(f"Loaded {len(words)} 12-letter words from Theophilus.")

# Add curated 12-letter words from Kryptos lore
kryptos_12 = [
    "TRANSPOSITION", "POLYALPHABET", "CRYPTOGRAPHY", "DECIPHERMENT",
    "INVESTIGATOR", "ARCHAEOLOGIST", "CENTRALINTEL", "INTELLIGENCE",
    "WHITESMITHS", "BLACKSMITHS", "NEEDLEMAKERS", "MEDIEVALARTS",
    "DEDIVERSISAR", "THEOPHILUSPR"
]
for w in kryptos_12:
    if len(w) == 12:
        words.add(w)

word_list = sorted(words)
orders = [argsort_stable(w) for w in word_list]

print(f"Total candidate words: {len(word_list)}")

# Test composition: P = P1 o P2 (meaning P[i] = P1[P2[i]] or P[i] = P2[P1[i]])
found = []
for i, w1 in enumerate(word_list):
    p1 = orders[i]
    for j, w2 in enumerate(word_list):
        p2 = orders[j]
        # Check comp 1
        comp1 = [p1[p2[k]] for k in range(12)]
        if comp1 == perm:
            found.append((w1, w2, "p1 o p2"))
            print(f"Match: {w1} o {w2} = perm")
        # Check comp 2
        comp2 = [p2[p1[k]] for k in range(12)]
        if comp2 == perm:
            found.append((w2, w1, "p2 o p1"))
            print(f"Match: {w2} o {w1} = perm")

print(f"Total matching pairs: {len(found)}")
