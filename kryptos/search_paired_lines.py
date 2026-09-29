import json
from collections import Counter
from buttcrack.scoring import NgramScorer
scorer = NgramScorer()

# Pairs: (Row 11 char, Row 8 char) -> list of col indices in G
col_pairs = [
    ('E', 'W', 0),
    ('H', 'F', 1),
    ('A', 'E', 2),
    ('H', 'T', 3),
    ('S', 'R', 4),
    ('S', 'E', 5),
    ('D', 'E', 6),
    ('S', 'E', 7),
    ('O', 'E', 8),
    ('O', 'P', 9),
    ('F', 'S', 10),
    ('U', 'D', 11),
]

# Multiset of available pairs: (c11, c8)
available_pairs = Counter((p[0], p[1]) for p in col_pairs)
print("Available letter pairs between Row 11 and Row 8:")
for pair, count in sorted(available_pairs.items()):
    print(f"  Row 11: {pair[0]} <---> Row 8: {pair[1]} (count: {count})")

# Let's load English words of lengths 2..12
import os
words_by_len = {}
all_words = set()
for l in range(2, 13):
    fname = f"words_{l}.txt"
    if os.path.exists(fname):
        with open(fname) as f:
            w_list = [line.strip().upper() for line in f if len(line.strip()) == l]
            words_by_len[l] = set(w_list)
            all_words.update(w_list)

print(f"Loaded {len(all_words)} total dictionary words")

# Also load common words from a clean corpus if available
# Let's test candidate sequences for Row 11:
# Known high-confidence phrases for Row 11:
# 'SHADES OF HOUS', 'SHADE OF HOUSE', 'SHADES OF HOME' ...
# Let's test all anagrams of Row 11 that form valid English words!
row11_letters = "EHAHSSDSOOFU"
row8_letters  = "WFETREEEEPSD"

# Let's find all 2-word, 3-word partitions of row11_letters
def get_word_partitions(letters, max_words=3):
    c_target = Counter(letters)
    valid_words = [w for w in all_words if len(w) >= 2 and all(c_target[ch] >= cnt for ch, cnt in Counter(w).items())]
    
    results = []
    def backtrack(rem_c, current_words):
        if not rem_c:
            results.append("".join(current_words))
            return
        if len(current_words) >= max_words:
            return
        rem_len = sum(rem_c.values())
        for w in valid_words:
            if len(w) <= rem_len and all(rem_c[ch] >= cnt for ch, cnt in Counter(w).items()):
                backtrack(rem_c - Counter(w), current_words + [w])
                
    backtrack(c_target, [])
    return list(set(results))

print("Finding valid English word partitions of Row 11...")
row11_phrases = get_word_partitions(row11_letters, max_words=3)
print(f"Found {len(row11_phrases)} candidate partitions for Row 11")

print("Finding valid English word partitions of Row 8...")
row8_phrases = get_word_partitions(row8_letters, max_words=3)
print(f"Found {len(row8_phrases)} candidate partitions for Row 8")

# Now check compatibility:
# Can a phrase for Row 11 and a phrase for Row 8 be formed simultaneously by permuting the pairs?
compatible_pairs = []

for p11 in row11_phrases:
    for p8 in row8_phrases:
        # Check if Counter of zip(p11, p8) matches available_pairs
        cand_pairs = Counter(zip(p11, p8))
        if cand_pairs == available_pairs:
            sc11 = scorer.score(p11) / 9.0
            sc8  = scorer.score(p8) / 9.0
            compatible_pairs.append((sc11 + sc8, sc11, sc8, p11, p8))

compatible_pairs.sort(reverse=True)
print(f"\nTotal compatible (Row 11, Row 8) alignments: {len(compatible_pairs)}")
for tot_sc, sc11, sc8, p11, p8 in compatible_pairs[:20]:
    print(f"Score {tot_sc:6.2f} (R11: {sc11:5.2f}, R8: {sc8:5.2f}) | R11: {p11:12s} | R8: {p8:12s}")

