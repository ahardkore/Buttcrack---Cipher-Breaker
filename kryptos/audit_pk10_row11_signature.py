# Focused Closing Signature and Colophon Audit on PK10 Row 11
from collections import Counter

# Row 11 characters (36 chars in core):
row11 = "ERULYARRFWYIGJVGPGYIANHOUPIDADBUBYSU"
print("==========================================================================================")
print("             PK10 ROW 11 CLOSING SIGNATURE & DEDICATION AUDIT                             ")
print("==========================================================================================\n")
print(f"Row 11 Raw String (36 chars): {row11}\n")

# Load words
words = set()
with open("all_words.txt") as f:
    for line in f:
        w = line.strip().upper()
        if len(w) >= 3 and w.isalpha():
            words.add(w)

# Find all dictionary words embedded in Row 11 as contiguous substrings:
found_substrings = []
for L in range(3, 12):
    for i in range(len(row11) - L + 1):
        sub = row11[i : i + L]
        if sub in words:
            found_substrings.append((i, L, sub))

found_substrings.sort(key=lambda x: (x[0], -x[1]))
print("Contiguous English Words in Row 11:")
for pos, L, sub in found_substrings:
    surround = row11[max(0, pos-3):min(len(row11), pos+L+3)]
    print(f"  Pos {pos:2d} (len {L}): [{sub:8s}] in ...{surround}...")

# Check formable anagram words of length >= 5 from Row 11:
c_r11 = Counter(row11)
formable_anagrams = []
for w in words:
    if len(w) >= 6:
        cw = Counter(w)
        if all(cw[ch] <= c_r11[ch] for ch in cw):
            formable_anagrams.append(w)

formable_anagrams.sort(key=lambda x: (-len(x), x))
print(f"\nFormable Anagram Words from Row 11 (Length >= 6): {len(formable_anagrams)} found")
print("Top longest candidate words:")
for w in formable_anagrams[:25]:
    print(f"  {w}")

# Check Thematic Signatures:
# Does it contain: SURVIVE, BURIED, BROWSING, LANGLEY, SANBORN, SCHEIDT, PARADIGM?
print("\nChecking Thematic K1-K4 / Cryptosystem Colophon Cribs:")
colophon_cribs = [
    "SURVIVE", "SURVIVAL", "SURVIVOR", "BURIED", "BROWSING", "LAYERTWO",
    "UNKNOWN", "LOCATION", "MESSAGE", "ANYTHING", "NUANCE", "IQLUSION",
    "SUBTLE", "SHADING", "MAGNETIC", "TREMBLING", "SANBORN", "SCHEIDT",
    "ROBINSON", "PARADIGM", "KRYPTOS", "THEOPHILUS", "RELIEF", "AUTHOR"
]

for crib in colophon_cribs:
    cw = Counter(crib)
    if all(cw[ch] <= c_r11[ch] for ch in cw):
        print(f"  --> Row 11 can form exact anagram of \"{crib}\"!")
    else:
        # Check missing letters
        missing = cw - c_r11
        if sum(missing.values()) <= 2:
            miss_str = "".join(missing.elements())
            print(f"  Near match: \"{crib}\" (missing only {sum(missing.values())} letters: {miss_str})")
