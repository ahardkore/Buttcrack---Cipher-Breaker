# Fast Exact Anagram Matching using Sorted Character Keys
from collections import defaultdict

with open("pk10_record_6943.txt") as f:
    lines = [l.strip() for l in f if l.startswith("# Row")]

rows = [l.split(":")[1].split("(")[0].strip() for l in lines]
core_rows = [r[2:38] for r in rows]

# Index words by their sorted character signature
anagram_map_6 = defaultdict(list)
anagram_map_8 = defaultdict(list)

with open("all_words.txt") as f:
    for line in f:
        w = line.strip().upper()
        if w.isalpha():
            if len(w) == 6:
                key = "".join(sorted(w))
                anagram_map_6[key].append(w)
            elif len(w) == 8:
                key = "".join(sorted(w))
                anagram_map_8[key].append(w)

print("==========================================================================================")
print("             PK10 PANEL B DEFECT SECTOR FAST ANAGRAM SCAN (COLS 18..23)                  ")
print("==========================================================================================\n")

print("--- 1. Exact 6-Letter Anagram Matches on Columns 18..23 ---")
for r in range(12):
    s6 = core_rows[r][18:24]
    key6 = "".join(sorted(s6))
    matches = anagram_map_6.get(key6, [])
    print(f"Row {r:2d} (Raw: {s6} | sorted: {key6}): {len(matches)} exact anagrams -> {matches}")

print("\n--- 2. Exact 8-Letter Anagram Matches on Extended Window (Cols 17..24) ---")
for r in range(12):
    s8 = core_rows[r][17:25]
    key8 = "".join(sorted(s8))
    matches8 = anagram_map_8.get(key8, [])
    print(f"Row {r:2d} (Raw: {s8} | sorted: {key8}): {len(matches8)} exact anagrams -> {matches8}")
