import re
from collections import Counter

dict_words = set()
for fn in ["words_4.txt", "words_7.txt", "words_12.txt"]:
    try:
        with open(fn) as f:
            for line in f:
                w = line.strip().upper()
                if 2 <= len(w) <= 12:
                    dict_words.add(w)
    except:
        pass

# Add Theophilus words
with open("theophilus_hendrie.txt") as f:
    for w in re.findall(r'[a-zA-Z]+', f.read()):
        if 2 <= len(w) <= 12:
            dict_words.add(w.upper())

rows = [
    "AEHHIIIKORTU", # Row 0
    "AADFHHLLMORY", # Row 1
    "AELMNOOPSSWW", # Row 2
    "AADEMNNNOTUU", # Row 3
    "AFHIIMMNORSS", # Row 4
    "AACFIILNRTTW", # Row 5
    "AAAABCEEHHMO", # Row 6
    "CDEEGIMNNOTT", # Row 7
    "DDEEEEFRSTTW", # Row 8
    "ADEFFFILLMST", # Row 9
    "FIILNOOOSTTU", # Row 10
    "DEEFGHHOSSSU"  # Row 11
]

def find_word_partitions(letters, min_len=4):
    c = Counter(letters)
    candidates = []
    for w in dict_words:
        if len(w) < min_len: continue
        cw = Counter(w)
        if all(cw[ch] <= c[ch] for ch in cw):
            candidates.append(w)
    
    results = []
    for w1 in candidates:
        c1 = c - Counter(w1)
        rem1 = "".join(sorted(c1.elements()))
        if len(rem1) == 0:
            results.append((w1,))
        elif len(rem1) <= 3:
            results.append((w1, rem1))
        for w2 in candidates:
            cw2 = Counter(w2)
            if all(cw2[ch] <= c1[ch] for ch in cw2):
                c2 = c1 - cw2
                rem2 = "".join(sorted(c2.elements()))
                if len(rem2) == 0:
                    results.append((w1, w2))
                elif len(rem2) <= 3:
                    results.append((w1, w2, rem2))
    return results

print("Testing Row 2 (AELMNOOPSSWW):")
res2 = find_word_partitions(rows[2], min_len=4)
for r in res2[:8]:
    print(" ", r)

print("\nTesting Row 8 (DDEEEEFRSTTW):")
res8 = find_word_partitions(rows[8], min_len=4)
for r in res8[:8]:
    print(" ", r)

print("\nTesting Row 9 (ADEFFFILLMST):")
res9 = find_word_partitions(rows[9], min_len=4)
for r in res9[:8]:
    print(" ", r)

print("\nTesting Row 10 (FIILNOOOSTTU):")
res10 = find_word_partitions(rows[10], min_len=4)
for r in res10[:8]:
    print(" ", r)
